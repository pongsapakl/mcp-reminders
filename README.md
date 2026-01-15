# mcp-reminders

![Python](https://img.shields.io/badge/python-3.12+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that enables Claude and other LLMs to manage Apple Reminders.

## About

This MCP server gives Claude full CRUD capabilities for Apple Reminders - create, read, update, delete, and complete tasks. Perfect for using Claude as your personal task manager, allowing you to manage reminders through natural conversation.

## Features

- Create, read, update, and delete reminders
- List all reminder lists
- Mark reminders as complete
- Set due dates, priorities, and notes
- Query reminders by date range and completion status
- Full integration with Apple's native Reminders app

## Prerequisites

- **macOS 10.14+** - Uses EventKit framework to interact with Reminders
- **Python 3.12+**
- **Apple Reminders app**
- **Claude Desktop** or another MCP-compatible client
- Basic familiarity with [MCP servers](https://modelcontextprotocol.io/)

## Installation

```bash
git clone https://github.com/pongsapakl/mcp-reminders.git
cd mcp-reminders
uv sync
```

## Configuration

Add to your MCP settings file. For Claude Desktop, edit:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Alternative: `~/.mcp.json`

```json
{
  "mcpServers": {
    "mcp-reminders": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/mcp-reminders",
        "run",
        "python",
        "main.py"
      ]
    }
  }
}
```

**Important**: Replace `/absolute/path/to/mcp-reminders` with the actual path where you cloned this repository.

## Permissions

The first time you use this server, macOS will request permission to access your Reminders. Grant permission in:

**System Settings → Privacy & Security → Reminders**

Make sure your MCP client (e.g., Claude Desktop) is authorized to access Reminders.

## Available Tools

- `list_reminder_lists()` - List all reminder lists
- `list_reminders(start_date?, end_date?, list_name?, include_completed?)` - Query reminders with optional filters
- `create_reminder(CreateReminderRequest)` - Create a new reminder with title, notes, due date, priority, and list
- `update_reminder(reminder_id, UpdateReminderRequest)` - Update an existing reminder
- `complete_reminder(reminder_id)` - Mark a reminder as completed
- `delete_reminder(reminder_id)` - Delete a reminder

## Usage Examples

Here's how Claude can use these tools in practice:

**Creating a reminder:**
```
User: "Remind me to call mom tomorrow at 2pm"
Claude: [Uses create_reminder with title="Call mom", due_date="2026-01-16 14:00", list="Reminders"]
```

**Listing today's tasks:**
```
User: "What do I need to do today?"
Claude: [Uses list_reminders with start_date=today, end_date=today, include_completed=false]
```

**Completing a task:**
```
User: "I finished calling mom"
Claude: [Uses list_reminders to find the reminder, then complete_reminder(reminder_id)]
```

**Managing priorities:**
```
User: "Make the dentist appointment high priority"
Claude: [Finds reminder, uses update_reminder to set priority=1]
```

## Limitations

- **Early reminders/alarms**: Setting notification times before the due date (like "remind me 1 hour before") is not yet supported. The EventKit API for early reminders doesn't fully align with how the macOS Reminders UI handles them.
- **Creating reminder lists**: You cannot create new reminder lists (calendars) programmatically yet. You'll need to create lists manually in the Reminders app first.

## Troubleshooting

**"Permission denied" error**
- Make sure you've granted Reminders access in System Settings → Privacy & Security → Reminders
- Restart Claude Desktop after granting permissions
- Check that your MCP client is in the authorized apps list

**Server not connecting**
- Verify the absolute path in your MCP config file is correct
- Try running `uv sync` again to ensure dependencies are installed
- Check Claude Desktop logs: `~/Library/Logs/Claude/`

**Reminders not appearing**
- Make sure the reminder list name exists in your Reminders app
- Try refreshing the Reminders app
- Check that you're querying the correct date range

**"Invalid reminder ID" error**
- Reminder IDs are x-apple-reminder:// URLs that can change
- Use list_reminders to get current IDs before updating/completing/deleting

## Contributing

Contributions are welcome! Feel free to:
- Report issues on [GitHub](https://github.com/pongsapakl/mcp-reminders/issues)
- Submit pull requests for bug fixes or improvements
- Suggest new features (especially for early reminders and list creation)

## License

MIT

---

Built with [MCP SDK](https://modelcontextprotocol.io/) | Learn more about [Model Context Protocol](https://modelcontextprotocol.io/)
