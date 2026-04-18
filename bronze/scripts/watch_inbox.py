#!/usr/bin/env python3
"""
Vault Watcher - Polling-based Inbox Monitor
Continuously monitors AI_Employee_Vault/Inbox for new .md files
and triggers AI processing workflow automatically.

Production-ready, lightweight, with deduplication.
"""

import os
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime
import subprocess
import sys

# ========================================
# CONFIGURATION
# ========================================
VAULT_ROOT = Path(__file__).parent.parent
INBOX_PATH = VAULT_ROOT / "AI_Employee_Vault" / "Inbox"
LOGS_DIR = VAULT_ROOT / "logs"
ACTIONS_LOG = LOGS_DIR / "actions.log"
PROCESSED_LOG = LOGS_DIR / "processed_files.json"
AI_SCRIPT = VAULT_ROOT / "run_ai_employee.py"

# Scan interval in seconds (10-30 recommended)
SCAN_INTERVAL = 30

# Maximum file size to process (10 MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# AI processing timeout (5 minutes)
AI_TIMEOUT = 300


# ========================================
# LOGGING FUNCTIONS
# ========================================
def log_action(level, message):
    """
    Write timestamped log entry to actions.log

    Args:
        level (str): Log level (SCAN, DETECT, TRIGGER, SUCCESS, ERROR, etc.)
        message (str): Log message
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"

    # Ensure logs directory exists
    LOGS_DIR.mkdir(exist_ok=True)

    # Write to log file
    with open(ACTIONS_LOG, "a", encoding="utf-8") as f:
        f.write(log_entry)

    # Also print to console
    print(log_entry.strip())


# ========================================
# PROCESSED FILES TRACKING
# ========================================
def load_processed_files():
    """
    Load the list of already processed files from JSON log.

    Returns:
        dict: Dictionary with processed files data
    """
    if not PROCESSED_LOG.exists():
        return {"processed_files": []}

    try:
        with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log_action("ERROR", f"Failed to load processed log: {e}")
        return {"processed_files": []}


def save_processed_files(data):
    """
    Save processed files data to JSON log.

    Args:
        data (dict): Processed files data to save
    """
    LOGS_DIR.mkdir(exist_ok=True)
    try:
        with open(PROCESSED_LOG, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        log_action("ERROR", f"Failed to save processed log: {e}")


def is_file_processed(filename, file_hash):
    """
    Check if file has already been processed.

    Args:
        filename (str): Name of the file
        file_hash (str): Hash of file content

    Returns:
        bool: True if already processed, False otherwise
    """
    data = load_processed_files()

    for entry in data["processed_files"]:
        if entry["filename"] == filename or entry.get("hash") == file_hash:
            return True

    return False


def mark_as_processed(filename, filepath):
    """
    Mark a file as processed in the log.

    Args:
        filename (str): Name of the file
        filepath (Path): Full path to the file
    """
    data = load_processed_files()

    # Calculate file hash
    try:
        with open(filepath, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
    except IOError:
        file_hash = "unknown"

    # Get file stats
    stats = filepath.stat()

    entry = {
        "filename": filename,
        "detected_at": datetime.now().isoformat(),
        "size_bytes": stats.st_size,
        "hash": file_hash,
        "processed_at": datetime.now().isoformat(),
        "status": "completed"
    }

    data["processed_files"].append(entry)
    save_processed_files(data)
    log_action("MARK", f"File marked as processed: {filename}")


# ========================================
# FILE SCANNING
# ========================================
def calculate_file_hash(filepath):
    """
    Calculate MD5 hash of file content.

    Args:
        filepath (Path): Path to file

    Returns:
        str: MD5 hash or None if error
    """
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except IOError as e:
        log_action("ERROR", f"Failed to hash file {filepath.name}: {e}")
        return None


def scan_inbox():
    """
    Scan inbox folder for new .md files.

    Returns:
        list: List of Path objects for new files to process
    """
    # Ensure inbox exists
    if not INBOX_PATH.exists():
        log_action("ERROR", f"Inbox path does not exist: {INBOX_PATH}")
        return []

    new_files = []

    # Get all .md files in inbox
    try:
        md_files = list(INBOX_PATH.glob("*.md"))
    except OSError as e:
        log_action("ERROR", f"Failed to scan inbox: {e}")
        return []

    for filepath in md_files:
        filename = filepath.name

        # Skip temporary and hidden files
        if filename.startswith(('.', '~')) or '.tmp' in filename:
            continue

        # Skip empty files
        if filepath.stat().st_size == 0:
            log_action("SKIP", f"Empty file: {filename}")
            continue

        # Skip very large files
        if filepath.stat().st_size > MAX_FILE_SIZE:
            log_action("SKIP", f"File too large: {filename} ({filepath.stat().st_size} bytes)")
            continue

        # Check if already processed
        file_hash = calculate_file_hash(filepath)
        if file_hash and is_file_processed(filename, file_hash):
            continue  # Already processed, skip silently

        new_files.append(filepath)

    return new_files


# ========================================
# AI WORKFLOW TRIGGER
# ========================================
def trigger_ai_workflow(filepath):
    """
    Trigger the AI processing workflow for a detected file.

    Args:
        filepath (Path): Path to the file to process

    Returns:
        bool: True if successful, False otherwise
    """
    filename = filepath.name
    log_action("TRIGGER", f"Starting AI workflow for: {filename}")

    try:
        # Check if AI script exists
        if not AI_SCRIPT.exists():
            log_action("ERROR", f"AI script not found: {AI_SCRIPT}")
            log_action("INFO", "Creating mock AI processing...")
            # Mock processing - just move file to Needs_Action
            return mock_ai_processing(filepath)

        # Execute AI script with timeout
        cmd = [sys.executable, str(AI_SCRIPT), "--once", "--file", str(filepath)]
        result = subprocess.run(
            cmd,
            timeout=AI_TIMEOUT,
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            log_action("SUCCESS", f"AI processing completed for: {filename}")
            return True
        else:
            log_action("ERROR", f"AI processing failed for: {filename}")
            log_action("ERROR", f"Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        log_action("ERROR", f"AI processing timeout for: {filename}")
        return False
    except Exception as e:
        log_action("ERROR", f"AI processing exception for {filename}: {e}")
        return False


def mock_ai_processing(filepath):
    """
    Mock AI processing when run_ai_employee.py doesn't exist.
    Simply logs the detection as a fallback.

    Args:
        filepath (Path): Path to the file

    Returns:
        bool: True (always succeeds)
    """
    filename = filepath.name
    log_action("INFO", f"Mock processing: {filename}")
    log_action("INFO", f"  → In production, this would trigger AI workflow")
    log_action("INFO", f"  → File: {filepath}")

    # In a real scenario, you might move the file or create a task here
    # For now, just log it

    return True


# ========================================
# MAIN WATCH LOOP
# ========================================
def watch_loop():
    """
    Main watching loop - continuously monitors inbox and processes new files.
    """
    log_action("START", "Vault Watcher started")
    log_action("INFO", f"Monitoring: {INBOX_PATH}")
    log_action("INFO", f"Scan interval: {SCAN_INTERVAL} seconds")
    log_action("INFO", f"Press Ctrl+C to stop")

    scan_count = 0
    files_processed = 0

    try:
        while True:
            scan_count += 1
            log_action("SCAN", f"Scanning inbox (scan #{scan_count})...")

            # Scan for new files
            new_files = scan_inbox()

            if not new_files:
                log_action("IDLE", "No new files detected")
            else:
                log_action("DETECT", f"Found {len(new_files)} new file(s)")

                # Process each new file
                for filepath in new_files:
                    filename = filepath.name
                    log_action("DETECT", f"New file found: {filename}")

                    # Trigger AI workflow
                    success = trigger_ai_workflow(filepath)

                    if success:
                        # Mark as processed
                        mark_as_processed(filename, filepath)
                        files_processed += 1
                        log_action("SUCCESS", f"Total files processed: {files_processed}")
                    else:
                        log_action("ERROR", f"Failed to process: {filename}")

            # Wait before next scan
            time.sleep(SCAN_INTERVAL)

    except KeyboardInterrupt:
        log_action("STOP", "Vault Watcher stopped by user")
        log_action("STATS", f"Total scans: {scan_count}")
        log_action("STATS", f"Total files processed: {files_processed}")
    except Exception as e:
        log_action("FATAL", f"Unexpected error: {e}")
        raise


# ========================================
# UTILITY COMMANDS
# ========================================
def show_status():
    """Display current watcher status and statistics."""
    print("\n" + "="*60)
    print("  VAULT WATCHER STATUS")
    print("="*60)

    print(f"\nConfiguration:")
    print(f"  Inbox Path: {INBOX_PATH}")
    print(f"  Scan Interval: {SCAN_INTERVAL}s")
    print(f"  Logs Directory: {LOGS_DIR}")

    # Check if inbox exists
    if INBOX_PATH.exists():
        files = list(INBOX_PATH.glob("*.md"))
        print(f"\nInbox Status:")
        print(f"  Files in inbox: {len(files)}")
        if files:
            print(f"  Files:")
            for f in files[:5]:  # Show first 5
                print(f"    - {f.name}")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more")
    else:
        print(f"\n[!] Inbox does not exist: {INBOX_PATH}")

    # Show processed files
    data = load_processed_files()
    processed_count = len(data["processed_files"])
    print(f"\nProcessed Files: {processed_count}")
    if processed_count > 0:
        recent = data["processed_files"][-5:]  # Last 5
        print(f"  Recent:")
        for entry in recent:
            print(f"    - {entry['filename']} ({entry['processed_at'][:19]})")

    print("\n" + "="*60 + "\n")


def reset_processed_log():
    """Reset the processed files log."""
    response = input("⚠️  This will reset the processed files log. Continue? (y/n): ")
    if response.lower() == 'y':
        save_processed_files({"processed_files": []})
        log_action("RESET", "Processed files log cleared")
        print("✓ Processed files log reset")
    else:
        print("✗ Reset cancelled")


# ========================================
# ENTRY POINT
# ========================================
def main():
    """Main entry point with command parsing."""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "status":
            show_status()
        elif command == "reset":
            reset_processed_log()
        elif command == "help":
            print("""
Vault Watcher - Inbox Monitor

Usage:
  python watch_inbox.py          Start the watcher
  python watch_inbox.py status   Show current status
  python watch_inbox.py reset    Reset processed files log
  python watch_inbox.py help     Show this help

Press Ctrl+C to stop the watcher.
            """)
        else:
            print(f"Unknown command: {command}")
            print("Use 'python watch_inbox.py help' for usage")
    else:
        # Start the watcher
        watch_loop()


if __name__ == "__main__":
    main()
