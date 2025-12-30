# mcp-reminders

A Model Context Protocol (MCP) server for managing Apple Reminders.

## Features

- Create, read, update, and delete reminders
- List reminder lists
- Mark reminders as complete
- Set due dates, priorities, and notes
- Query reminders by date range and completion status

## Installation

```bash
uv sync
```

## Usage

This server is designed to be used with Claude Desktop or other MCP clients.

### Configuration

Add to your MCP settings:

```json
{
  "mcp-reminders": {
    "type": "stdio",
    "command": "uv",
    "args": [
      "--directory",
      "/path/to/mcp-reminders",
      "run",
      "python",
      "main.py"
    ]
  }
}
```

### Permissions

The first time you use this server, macOS will request permission to access your Reminders. Grant permission in:

System Settings > Privacy & Security > Reminders

## Available Tools

- `list_reminder_lists()` - List all reminder lists
- `list_reminders(start_date?, end_date?, list_name?, include_completed?)` - Query reminders
- `create_reminder(CreateReminderRequest)` - Create a new reminder
- `update_reminder(reminder_id, UpdateReminderRequest)` - Update an existing reminder
- `complete_reminder(reminder_id)` - Mark a reminder as completed
- `delete_reminder(reminder_id)` - Delete a reminder

## Requirements

- macOS 10.14+
- Python 3.12+
- Access to Apple Reminders

## TODO

### Add Early Reminder Feature
Support for early reminders (notifications before due time) similar to macOS Reminders app UI.

**What we've found:**
- macOS Reminders UI has two separate fields: "Alarm" (due time) and "Early reminder" (notification before due time)
- EventKit's EKAlarm class supports both `relativeOffset` (relative to due date) and `absoluteDate` (specific time) alarms
- There's a `isDefaultAlarm` property that may distinguish between main alarm and early reminders
- Early reminders set via macOS Reminders UI are not consistently readable via EventKit API - they may be stored differently than programmatically created alarms
- Current implementation creates reminders without alarms; users set `due_date` to their desired reminder time
- Further investigation needed to properly read/write early reminders that match macOS Reminders app behavior

### Add Reminder List Creation
Add ability to create new reminder lists (calendars) programmatically via `create_reminder_list(name)` function.
