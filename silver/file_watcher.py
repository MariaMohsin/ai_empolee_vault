from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
from datetime import datetime
import time
import shutil

# ========================================
# CONFIGURATION
# ========================================
VAULT = Path(__file__).parent
INBOX = VAULT / "Inbox"
NEEDS = VAULT / "Needs_Action"
LOGS = VAULT / "Logs"
ERROR_LOG = LOGS / "watcher_error.log"
INBOX_ARCHIVE = VAULT / "Inbox_Archive"  # Store original files


# ========================================
# ERROR LOGGING FUNCTION
# ========================================
def log_error(error_message):
    """
    Writes error messages to the error log file with timestamp.
    This helps track problems when the watcher encounters issues.
    """
    try:
        # Ensure Logs folder exists
        LOGS.mkdir(exist_ok=True)

        # Get current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Write error to log file (append mode)
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {error_message}\n")

        print(f"[ERROR] {error_message}")
    except Exception as e:
        # If logging fails, at least print to console
        print(f"[CRITICAL] Failed to log error: {e}")


# ========================================
# FOLDER SETUP
# ========================================
def ensure_folders_exist():
    """
    Creates required folders if they don't exist.
    This prevents the watcher from crashing if folders are missing.
    """
    try:
        # Create Inbox folder if missing
        if not INBOX.exists():
            INBOX.mkdir(parents=True)
            print(f"[SETUP] Created missing folder: {INBOX}")

        # Create Needs_Action folder if missing
        if not NEEDS.exists():
            NEEDS.mkdir(parents=True)
            print(f"[SETUP] Created missing folder: {NEEDS}")

        # Create Logs folder if missing
        if not LOGS.exists():
            LOGS.mkdir(parents=True)
            print(f"[SETUP] Created missing folder: {LOGS}")

        # Create Inbox_Archive folder if missing
        if not INBOX_ARCHIVE.exists():
            INBOX_ARCHIVE.mkdir(parents=True)
            print(f"[SETUP] Created missing folder: {INBOX_ARCHIVE}")

        return True
    except Exception as e:
        log_error(f"Failed to create folders: {e}")
        return False


def create_structured_task(original_file_path, archived_file_path):
    """
    Creates a structured task file in Needs_Action based on template.

    Args:
        original_file_path (Path): Path to the original file in Inbox
        archived_file_path (Path): Path where the file was archived

    Returns:
        Path: Path to the created task file, or None if failed
    """
    try:
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Create task filename: task_<original_filename>
        task_filename = f"task_{original_file_path.name}"
        task_path = NEEDS / task_filename

        # Read original file content (first 500 chars for preview)
        try:
            with open(original_file_path, 'r', encoding='utf-8') as f:
                content_preview = f.read(500)
                if len(content_preview) == 500:
                    content_preview += "..."
        except:
            content_preview = "[Binary file or unreadable content]"

        # Create structured task content
        task_content = f"""# Task: Review New File

```yaml
type: file_review
status: pending
priority: medium
created_at: {timestamp}
assigned_to: bronze_employee
related_files:
  - {archived_file_path.relative_to(VAULT)}
```

## Task Description

A new file has been detected in the Inbox and requires review and processing.

**File Details:**
- **Original Name:** {original_file_path.name}
- **Archived Location:** {archived_file_path.relative_to(VAULT)}
- **Detected:** {timestamp}
- **File Type:** {original_file_path.suffix}

**Content Preview:**
```
{content_preview}
```

## Action Items

- [ ] Review the file content and understand its purpose
- [ ] Determine what action is required (if any)
- [ ] Process the file according to requirements
- [ ] Document the outcome in this task file
- [ ] Move this task to /Done when complete

## Notes

This file was automatically detected by the file watcher system and archived for processing.
The AI Employee should review the content and take appropriate action based on the file type and contents.

**Processing Guidelines:**
- If the file contains a task, execute it according to Company Handbook rules
- If the file is informational, acknowledge and file appropriately
- If the file is unclear, note questions in this task for clarification

---

## Task History

- **Created:** {timestamp}
- **Started:** [Pending]
- **Completed:** [Pending]

---

**Task Status:** Pending Review
"""

        # Write task file
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(task_content)

        return task_path

    except Exception as e:
        log_error(f"Failed to create structured task for {original_file_path}: {e}")
        return None


# ========================================
# FILE HANDLER CLASS
# ========================================
class InboxHandler(FileSystemEventHandler):
    """
    Watches the Inbox folder and automatically moves new files
    to the Needs_Action folder for AI processing.
    """

    def __init__(self):
        # Track processed files to avoid duplicates
        self.processed = set()

    def process_file(self, file_path):
        """
        Processes a single file: creates structured task and archives original.
        Includes error handling to prevent crashes.
        """
        try:
            src = Path(file_path)

            # FILTER 1: Ignore temporary files (created during file writes)
            if src.suffix == '.tmp' or '.tmp.' in src.name:
                return

            # FILTER 2: Ignore if already processed (prevent duplicates)
            if src.name in self.processed:
                return

            # WAIT: Give time for file to finish writing
            time.sleep(0.5)

            # CHECK: Ensure file still exists (might have been temp file)
            if not src.exists():
                return

            # MARK: Add to processed set to avoid re-processing
            self.processed.add(src.name)

            print(f"[NEW FILE] Detected: {src.name}")

            # STEP 1: Archive the original file
            archive_dest = INBOX_ARCHIVE / src.name
            shutil.move(src, archive_dest)
            print(f"  -> Archived to: Inbox_Archive/{src.name}")

            # STEP 2: Create structured task in Needs_Action
            task_file = create_structured_task(src, archive_dest)

            if task_file:
                print(f"  -> Created task: {task_file.name}")
                print(f"[SUCCESS] Structured task created for {src.name}")
            else:
                print(f"[WARNING] Failed to create task for {src.name}")

        except Exception as e:
            # ERROR: Log the problem and remove from processed set
            log_error(f"Failed to process {file_path}: {e}")
            if src.name in self.processed:
                self.processed.discard(src.name)

    def on_created(self, event):
        """Triggered when a new file is created in Inbox."""
        if not event.is_directory:
            self.process_file(event.src_path)

    def on_modified(self, event):
        """Triggered when a file is modified in Inbox."""
        if not event.is_directory:
            self.process_file(event.src_path)


# ========================================
# MAIN EXECUTION
# ========================================
def main():
    """
    Main function that runs the file watcher.
    Includes error handling for startup and runtime issues.
    """
    print("[FILE WATCHER] Starting up...")

    # STEP 1: Ensure all required folders exist
    if not ensure_folders_exist():
        print("[FATAL] Cannot create required folders. Exiting.")
        return

    # STEP 2: Initialize the file watcher
    try:
        observer = Observer()
        observer.schedule(InboxHandler(), str(INBOX), recursive=False)
        observer.start()
        print("[FILE WATCHER] Running and monitoring Inbox folder...")
        print("[INFO] Press Ctrl+C to stop")

    except Exception as e:
        log_error(f"Failed to start watcher: {e}")
        print("[FATAL] Could not start file watcher. Check error log.")
        return

    # STEP 3: Keep watcher running until interrupted
    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        # USER STOPPED: Clean shutdown when Ctrl+C is pressed
        print("\n[SHUTDOWN] Stopping file watcher...")
        observer.stop()

    except Exception as e:
        # UNEXPECTED ERROR: Log it and shut down gracefully
        log_error(f"Unexpected error in main loop: {e}")
        print("[ERROR] Watcher encountered an error. Stopping...")
        observer.stop()

    # STEP 4: Wait for observer thread to finish
    observer.join()
    print("[FILE WATCHER] Stopped successfully")


# ========================================
# RUN THE WATCHER
# ========================================
if __name__ == "__main__":
    main()
