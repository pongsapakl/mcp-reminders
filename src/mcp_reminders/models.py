from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Annotated, Self

from EventKit import EKReminder  # type: ignore[import-untyped]
from pydantic import BaseModel, BeforeValidator, Field


def convert_datetime(v):
    """Convert various datetime formats to Python datetime."""
    if hasattr(v, "timeIntervalSince1970"):
        return datetime.fromtimestamp(v.timeIntervalSince1970())

    if isinstance(v, str):
        return datetime.fromisoformat(v)

    if isinstance(v, datetime):
        return v

    # If we don't recognize the type, let Pydantic handle it
    return v


FlexibleDateTime = Annotated[datetime, BeforeValidator(convert_datetime)]


class Priority(IntEnum):
    """Reminder priority levels (EventKit uses 0-9)."""
    NONE = 0
    HIGH = 1
    MEDIUM = 5
    LOW = 9


@dataclass
class Reminder:
    """Represents a reminder from Apple Reminders."""
    title: str
    identifier: str
    list_name: str | None = None
    due_date: FlexibleDateTime | None = None
    notes: str | None = None
    priority: int = 0  # 0-9, where 0=none, 1-4=high, 5=medium, 6-9=low
    completed: bool = False
    completion_date: FlexibleDateTime | None = None
    url: str | None = None
    _raw_reminder: EKReminder | None = None  # Store the original EKReminder object

    @classmethod
    def from_ekreminder(cls, ekreminder: EKReminder) -> "Reminder":
        """Create a Reminder instance from an EKReminder."""
        # Convert dueDateComponents to datetime if available
        due_date = None
        if ekreminder.dueDateComponents():
            components = ekreminder.dueDateComponents()
            # Reconstruct datetime from components
            due_date = datetime(
                year=components.year() if components.year() != 0x7FFFFFFFFFFFFFFF else 1,
                month=components.month() if components.month() != 0x7FFFFFFFFFFFFFFF else 1,
                day=components.day() if components.day() != 0x7FFFFFFFFFFFFFFF else 1,
                hour=components.hour() if components.hour() != 0x7FFFFFFFFFFFFFFF else 0,
                minute=components.minute() if components.minute() != 0x7FFFFFFFFFFFFFFF else 0,
            )

        return cls(
            title=ekreminder.title() or "",
            identifier=ekreminder.calendarItemIdentifier(),
            list_name=ekreminder.calendar().title() if ekreminder.calendar() else None,
            due_date=due_date,
            notes=ekreminder.notes(),
            priority=ekreminder.priority() if ekreminder.priority() else 0,
            completed=ekreminder.isCompleted(),
            completion_date=ekreminder.completionDate(),
            url=str(ekreminder.URL()) if ekreminder.URL() else None,
            _raw_reminder=ekreminder,
        )

    def __str__(self) -> str:
        """Return a human-readable string representation of the Reminder."""
        status = "Completed" if self.completed else "Pending"

        return (
            f"Reminder: {self.title},\n"
            f" - Identifier: {self.identifier},\n"
            f" - List: {self.list_name or 'N/A'},\n"
            f" - Due Date: {self.due_date or 'N/A'},\n"
            f" - Priority: {self.priority},\n"
            f" - Status: {status},\n"
            f" - Completion Date: {self.completion_date or 'N/A'},\n"
            f" - Notes: {self.notes or 'N/A'},\n"
            f" - URL: {self.url or 'N/A'}\n"
        )


class CreateReminderRequest(BaseModel):
    """Request model for creating a new reminder."""
    title: str
    due_date: datetime | None = None
    notes: str | None = None
    priority: int = Field(default=0, ge=0, le=9)
    list_name: str | None = None
    url: str | None = None


class UpdateReminderRequest(BaseModel):
    """Request model for updating an existing reminder."""
    title: str | None = None
    due_date: datetime | None = None
    notes: str | None = None
    priority: int | None = Field(default=None, ge=0, le=9)
    list_name: str | None = None
    url: str | None = None
    completed: bool | None = None
