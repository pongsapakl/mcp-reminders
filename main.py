"""Entry point for mcp-reminders server."""
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from mcp_reminders.server import main

if __name__ == "__main__":
    main()
