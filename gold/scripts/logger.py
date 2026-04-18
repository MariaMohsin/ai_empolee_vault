"""
Logger - Simple logging system for AI Employee
"""

from pathlib import Path
from datetime import datetime


class Logger:
    """Simple file-based logger"""

    def __init__(self, log_file=None):
        if log_file is None:
            root = Path(__file__).parent.parent
            log_file = root / "Logs" / "ai_employee.log"

        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, level, message):
        """
        Write log entry

        Args:
            level (str): Log level (INFO, ERROR, STEP, etc.)
            message (str): Log message
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{timestamp}] [{level}] {message}\n"

        # Write to file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(entry)

        # Also print to console
        print(entry.strip())
