import sys
from datetime import datetime
from threading import Semaphore
from typing import Any

from EventKit import (
    EKAlarm,  # type: ignore
    EKCalendar,  # type: ignore
    EKEntityTypeReminder,  # type: ignore
    EKEventStore,  # type: ignore
    EKReminder,  # type: ignore
)
from Foundation import NSCalendar, NSCalendarUnitDay, NSCalendarUnitHour, NSCalendarUnitMinute, NSCalendarUnitMonth, NSCalendarUnitYear, NSDate, NSDateComponents  # type: ignore
from loguru import logger

from .models import (
    CreateReminderRequest,
    Reminder,
    UpdateReminderRequest,
)

logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
)


class RemindersManager:
    def __init__(self):
        self.event_store = EKEventStore.alloc().init()

        # Force a fresh permission check for reminders
        auth_status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeReminder)
        logger.debug(f"Initial Reminders authorization status: {auth_status}")

        # Always request access regardless of current status
        if not self._request_access():
            logger.error("Reminders access request failed")
            raise ValueError(
                "Reminders access not granted. Please check System Settings > Privacy & Security > Reminders."
            )
        logger.info("Reminders access granted successfully")

    def list_reminders(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        list_name: str | None = None,
        include_completed: bool = False,
    ) -> list[Reminder]:
        """List reminders with optional filters.

        Args:
            start_date: Filter reminders with due dates on or after this date
            end_date: Filter reminders with due dates on or before this date
            list_name: The name of the reminder list to filter by
            include_completed: Whether to include completed reminders

        Returns:
            list[Reminder]: A list of reminders matching the criteria
        """
        # Get reminder list(s) to search
        reminder_list = self._find_list_by_name(list_name) if list_name else None
        if list_name and not reminder_list:
            raise NoSuchReminderListException(list_name)

        reminder_lists = [reminder_list] if reminder_list else None

        logger.info(
            f"Listing reminders in: {list_name if list_name else 'all lists'}, "
            f"include_completed: {include_completed}"
        )

        # Use predicate to fetch reminders
        predicate = self.event_store.predicateForRemindersInCalendars_(reminder_lists)

        # Fetch reminders using completion handler
        semaphore = Semaphore(0)
        fetched_reminders = []

        def completion_handler(reminders):
            nonlocal fetched_reminders
            if reminders:
                fetched_reminders = list(reminders)
            semaphore.release()

        self.event_store.fetchRemindersMatchingPredicate_completion_(predicate, completion_handler)
        semaphore.acquire()

        # Filter results based on criteria
        results = []
        for ekreminder in fetched_reminders:
            # Filter by completion status
            if not include_completed and ekreminder.isCompleted():
                continue

            # Filter by date range if specified
            if start_date or end_date:
                due_components = ekreminder.dueDateComponents()
                if not due_components:
                    continue  # Skip reminders without due dates when filtering by date

                # Convert due date components to datetime for comparison
                due_date = self._components_to_datetime(due_components)
                if start_date and due_date < start_date:
                    continue
                if end_date and due_date > end_date:
                    continue

            results.append(Reminder.from_ekreminder(ekreminder))

        return results

    def create_reminder(self, new_reminder: CreateReminderRequest) -> Reminder:
        """Create a new reminder.

        Args:
            new_reminder: The reminder to create

        Returns:
            Reminder: The created reminder with identifier if successful
        """
        ekreminder = EKReminder.reminderWithEventStore_(self.event_store)

        ekreminder.setTitle_(new_reminder.title)

        if new_reminder.notes:
            ekreminder.setNotes_(new_reminder.notes)

        if new_reminder.url:
            ekreminder.setURL_(new_reminder.url)

        if new_reminder.priority is not None:
            ekreminder.setPriority_(new_reminder.priority)

        # Set due date using NSDateComponents
        if new_reminder.due_date:
            components = self._datetime_to_components(new_reminder.due_date)
            ekreminder.setDueDateComponents_(components)


        # Set reminder list (calendar)
        if new_reminder.list_name:
            reminder_list = self._find_list_by_name(new_reminder.list_name)
            if not reminder_list:
                logger.error(
                    f"Failed to create reminder: The specified list '{new_reminder.list_name}' does not exist."
                )
                raise NoSuchReminderListException(new_reminder.list_name)
        else:
            reminder_list = self.event_store.defaultCalendarForNewReminders()
            logger.debug(f"Using default reminder list: {reminder_list.title()}")

        ekreminder.setCalendar_(reminder_list)

        try:
            success, error = self.event_store.saveReminder_commit_error_(ekreminder, True, None)

            if not success:
                logger.error(f"Failed to save reminder: {error}")
                raise Exception(error)

            logger.info(f"Successfully created reminder: {new_reminder.title}")
            return Reminder.from_ekreminder(ekreminder)

        except Exception as e:
            logger.exception(e)
            raise

    def update_reminder(self, reminder_id: str, request: UpdateReminderRequest) -> Reminder:
        """Update an existing reminder by its identifier.

        Args:
            reminder_id: The unique identifier of the reminder to update
            request: The update request containing the fields to modify

        Returns:
            Reminder: The updated reminder if successful
        """
        existing_reminder = self.find_reminder_by_id(reminder_id)
        if not existing_reminder:
            raise NoSuchReminderException(reminder_id)

        existing_ek_reminder = existing_reminder._raw_reminder
        if not existing_ek_reminder:
            raise NoSuchReminderException(reminder_id)

        if request.title is not None:
            existing_ek_reminder.setTitle_(request.title)
        if request.notes is not None:
            existing_ek_reminder.setNotes_(request.notes)
        if request.url is not None:
            existing_ek_reminder.setURL_(request.url)
        if request.priority is not None:
            existing_ek_reminder.setPriority_(request.priority)
        if request.completed is not None:
            existing_ek_reminder.setCompleted_(request.completed)

        # Update due date
        if request.due_date is not None:
            components = self._datetime_to_components(request.due_date)
            existing_ek_reminder.setDueDateComponents_(components)

        # Update reminder list if specified
        if request.list_name:
            reminder_list = self._find_list_by_name(request.list_name)
            if reminder_list:
                existing_ek_reminder.setCalendar_(reminder_list)
            else:
                raise NoSuchReminderListException(request.list_name)


        try:
            success, error = self.event_store.saveReminder_commit_error_(existing_ek_reminder, True, None)

            if not success:
                logger.error(f"Failed to update reminder: {error}")
                raise Exception(error)

            logger.info(f"Successfully updated reminder: {request.title or existing_reminder.title}")
            return Reminder.from_ekreminder(existing_ek_reminder)

        except Exception as e:
            logger.error(f"Failed to update reminder: {e}")
            raise

    def complete_reminder(self, reminder_id: str) -> Reminder:
        """Mark a reminder as completed.

        Args:
            reminder_id: The unique identifier of the reminder to complete

        Returns:
            Reminder: The updated reminder
        """
        existing_reminder = self.find_reminder_by_id(reminder_id)
        if not existing_reminder:
            raise NoSuchReminderException(reminder_id)

        existing_ek_reminder = existing_reminder._raw_reminder
        if not existing_ek_reminder:
            raise NoSuchReminderException(reminder_id)

        existing_ek_reminder.setCompleted_(True)

        try:
            success, error = self.event_store.saveReminder_commit_error_(existing_ek_reminder, True, None)

            if not success:
                logger.error(f"Failed to complete reminder: {error}")
                raise Exception(error)

            logger.info(f"Successfully completed reminder: {existing_reminder.title}")
            return Reminder.from_ekreminder(existing_ek_reminder)

        except Exception as e:
            logger.error(f"Failed to complete reminder: {e}")
            raise

    def delete_reminder(self, reminder_id: str) -> bool:
        """Delete a reminder by its identifier.

        Args:
            reminder_id: The unique identifier of the reminder to delete

        Returns:
            bool: True if deletion was successful

        Raises:
            NoSuchReminderException: If the reminder with the given ID doesn't exist
            Exception: If there was an error deleting the reminder
        """
        existing_reminder = self.find_reminder_by_id(reminder_id)
        if not existing_reminder:
            raise NoSuchReminderException(reminder_id)

        existing_ek_reminder = existing_reminder._raw_reminder
        if not existing_ek_reminder:
            raise NoSuchReminderException(reminder_id)

        try:
            success, error = self.event_store.removeReminder_commit_error_(existing_ek_reminder, True, None)

            if not success:
                logger.error(f"Failed to delete reminder: {error}")
                raise Exception(error)

            logger.info(f"Successfully deleted reminder: {existing_reminder.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete reminder: {e}")
            raise

    def find_reminder_by_id(self, identifier: str) -> Reminder | None:
        """Find a reminder by its identifier.

        Args:
            identifier: The unique identifier of the reminder

        Returns:
            Reminder | None: The reminder if found, None otherwise
        """
        ekreminder = self.event_store.calendarItemWithIdentifier_(identifier)
        if not ekreminder:
            logger.info(f"No reminder found with ID: {identifier}")
            return None

        return Reminder.from_ekreminder(ekreminder)

    def list_reminder_list_names(self) -> list[str]:
        """List all available reminder list names.

        Returns:
            list[str]: A list of reminder list names
        """
        reminder_lists = self.event_store.calendarsForEntityType_(EKEntityTypeReminder)
        return [reminder_list.title() for reminder_list in reminder_lists]

    def list_reminder_lists(self) -> list[Any]:
        """List all available reminder lists.

        Returns:
            list[Any]: A list of EKCalendar objects for reminders
        """
        return self.event_store.calendarsForEntityType_(EKEntityTypeReminder)

    def _request_access(self) -> bool:
        """Request access to interact with the macOS Reminders app."""
        semaphore = Semaphore(0)
        access_granted = False

        def completion(granted: bool, error) -> None:
            nonlocal access_granted
            access_granted = granted
            semaphore.release()

        self.event_store.requestAccessToEntityType_completion_(EKEntityTypeReminder, completion)
        semaphore.acquire()
        return access_granted

    def _find_list_by_name(self, list_name: str) -> Any | None:
        """Find a reminder list by name. Returns None if not found.

        Args:
            list_name: The name of the reminder list to find

        Returns:
            Any | None: The reminder list (EKCalendar) if found, None otherwise
        """
        for reminder_list in self.event_store.calendarsForEntityType_(EKEntityTypeReminder):
            if reminder_list.title() == list_name:
                return reminder_list

        logger.info(f"Reminder list '{list_name}' not found")
        return None

    def _datetime_to_components(self, dt: datetime) -> NSDateComponents:
        """Convert a Python datetime to NSDateComponents.

        Args:
            dt: Python datetime object

        Returns:
            NSDateComponents: The corresponding NSDateComponents
        """
        components = NSDateComponents.alloc().init()
        components.setYear_(dt.year)
        components.setMonth_(dt.month)
        components.setDay_(dt.day)
        components.setHour_(dt.hour)
        components.setMinute_(dt.minute)
        return components

    def _components_to_datetime(self, components: NSDateComponents) -> datetime:
        """Convert NSDateComponents to Python datetime.

        Args:
            components: NSDateComponents object

        Returns:
            datetime: The corresponding Python datetime
        """
        # Note: NSDateComponents uses NSIntegerMax (0x7FFFFFFFFFFFFFFF) for undefined values
        return datetime(
            year=components.year() if components.year() != 0x7FFFFFFFFFFFFFFF else 1,
            month=components.month() if components.month() != 0x7FFFFFFFFFFFFFFF else 1,
            day=components.day() if components.day() != 0x7FFFFFFFFFFFFFFF else 1,
            hour=components.hour() if components.hour() != 0x7FFFFFFFFFFFFFFF else 0,
            minute=components.minute() if components.minute() != 0x7FFFFFFFFFFFFFFF else 0,
        )


class NoSuchReminderListException(Exception):
    def __init__(self, list_name: str):
        super().__init__(f"Reminder list: {list_name} does not exist")


class NoSuchReminderException(Exception):
    def __init__(self, reminder_id: str):
        super().__init__(f"Reminder with id: {reminder_id} does not exist")
