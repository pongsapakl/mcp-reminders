import sys
from datetime import datetime
from functools import lru_cache
from textwrap import dedent

from loguru import logger
from mcp.server.fastmcp import FastMCP

from .models import CreateReminderRequest, UpdateReminderRequest
from .reminders import RemindersManager

mcp = FastMCP("Reminders")

logger.remove()
logger.add(
    sys.stderr,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
)


# Initialize the RemindersManager on demand to only request reminders permission
# when a reminder tool is invoked instead of on the launch of the Claude Desktop app.
@lru_cache(maxsize=None)
def get_reminders_manager() -> RemindersManager:
    """Get or initialize the reminders manager with proper error handling."""
    try:
        return RemindersManager()
    except ValueError as e:
        error_msg = dedent("""\
        Reminders access is not granted. Please follow these steps:

        1. Open System Preferences/Settings
        2. Go to Privacy & Security > Reminders
        3. Check the box next to your terminal application or Claude Desktop
        4. Restart Claude Desktop

        Once you've granted access, try your reminder operation again.
        """)
        raise ValueError(error_msg) from e


@mcp.resource("reminders://lists")
def get_reminder_lists() -> str:
    """List all available reminder lists that can be used with reminder operations."""
    try:
        manager = get_reminders_manager()
        lists = manager.list_reminder_list_names()
        if not lists:
            return "No reminder lists found"
        return "Available reminder lists:\n" + "\n".join(f"- {list_name}" for list_name in lists)
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Error listing reminder lists: {str(e)}"


@mcp.tool()
async def list_reminder_lists() -> str:
    """List all available reminder lists."""
    try:
        manager = get_reminders_manager()
        lists = manager.list_reminder_list_names()
        if not lists:
            return "No reminder lists found"

        return "Available reminder lists:\n" + "\n".join(f"- {list_name}" for list_name in lists)

    except Exception as e:
        return f"Error listing reminder lists: {str(e)}"


@mcp.tool()
async def list_reminders(
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    list_name: str | None = None,
    include_completed: bool = False,
) -> str:
    """List reminders with optional filters.

    Args:
        start_date: Filter reminders with due dates on or after this date (ISO format)
        end_date: Filter reminders with due dates on or before this date (ISO format)
        list_name: Optional reminder list name to filter by (check reminders://lists)
        include_completed: Whether to include completed reminders (default: False)
    """
    try:
        manager = get_reminders_manager()
        reminders = manager.list_reminders(start_date, end_date, list_name, include_completed)
        if not reminders:
            return "No reminders found matching the criteria"

        return "".join([str(reminder) for reminder in reminders])

    except Exception as e:
        return f"Error listing reminders: {str(e)}"


@mcp.tool()
async def create_reminder(create_reminder_request: CreateReminderRequest) -> str:
    """Create a new reminder.

    Before using this tool:
    1. Ask the user which reminder list they want to use if not specified (check reminders://lists)
    2. Confirm the title and due date with the user
    3. Ask if they want to set priority, notes, or alarms

    Args:
        title: Reminder title (required)
        due_date: Optional due date in ISO format (YYYY-MM-DDTHH:MM:SS)
        notes: Optional notes/description
        priority: Priority level (0=none, 1-4=high, 5=medium, 6-9=low, default: 0)
        list_name: Optional reminder list name. Ask user which list to use, referencing reminders://lists
        alarms_minutes_offsets: List of minutes before the due date to trigger alarms
            e.g. [60, 1440] means two alarms: 1 hour before and 24 hours before
        url: Optional URL associated with the reminder
    """
    logger.info(f"Incoming Create Reminder Request: {create_reminder_request}")
    try:
        manager = get_reminders_manager()

        reminder = manager.create_reminder(create_reminder_request)
        if not reminder:
            return "Failed to create reminder. Please check reminders permissions and try again."

        return f"Successfully created reminder: {reminder.title} (ID: {reminder.identifier})"

    except Exception as e:
        return f"Error creating reminder: {str(e)}"


@mcp.tool()
async def update_reminder(reminder_id: str, update_reminder_request: UpdateReminderRequest) -> str:
    """Update an existing reminder.

    Before using this tool:
    1. Ask the user which fields they want to update
    2. If moving to a different list, verify the list exists using reminders://lists
    3. Confirm the changes with the user

    Args:
        reminder_id: Unique identifier of the reminder to update
        title: Optional new title
        due_date: Optional new due date in ISO format
        notes: Optional new notes/description
        priority: Optional new priority (0-9)
        list_name: Optional new reminder list. Ask user which list to use, referencing reminders://lists
        alarms_minutes_offsets: List of minutes before the due date to trigger alarms
        url: Optional URL
        completed: Optional completion status (True/False)
    """
    try:
        manager = get_reminders_manager()
        reminder = manager.update_reminder(reminder_id, update_reminder_request)
        if not reminder:
            return f"Failed to update reminder. Reminder with ID {reminder_id} not found or update failed."

        return f"Successfully updated reminder: {reminder.title}"

    except Exception as e:
        return f"Error updating reminder: {str(e)}"


@mcp.tool()
async def complete_reminder(reminder_id: str) -> str:
    """Mark a reminder as completed.

    Args:
        reminder_id: Unique identifier of the reminder to complete
    """
    try:
        manager = get_reminders_manager()
        reminder = manager.complete_reminder(reminder_id)
        if not reminder:
            return f"Failed to complete reminder. Reminder with ID {reminder_id} not found."

        return f"Successfully completed reminder: {reminder.title}"

    except Exception as e:
        return f"Error completing reminder: {str(e)}"


@mcp.tool()
async def delete_reminder(reminder_id: str) -> str:
    """Delete a reminder permanently.

    Args:
        reminder_id: Unique identifier of the reminder to delete
    """
    try:
        manager = get_reminders_manager()
        success = manager.delete_reminder(reminder_id)
        if not success:
            return f"Failed to delete reminder. Reminder with ID {reminder_id} not found."

        return f"Successfully deleted reminder"

    except Exception as e:
        return f"Error deleting reminder: {str(e)}"


def main():
    logger.info("Running mcp-reminders server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
