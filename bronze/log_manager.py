"""
LOG MANAGER - Automatic Log File Rotation
==========================================

Purpose:
    Prevents log files from growing forever by rotating them when they
    exceed 1 MB in size.

Behavior:
    1. Checks system_log.md and Logs/watcher_error.log
    2. If a file is larger than 1 MB:
       - Renames it with a timestamp (e.g., system_log_2026-02-10.md)
       - Creates a fresh empty file with the original name
    3. Logs all rotation activities

Usage:
    python log_manager.py

Dependencies:
    None - uses only Python standard library
"""

from pathlib import Path
from datetime import datetime
import os


# ========================================
# CONFIGURATION
# ========================================

# Maximum file size before rotation (1 MB = 1,048,576 bytes)
MAX_FILE_SIZE = 1024 * 1024  # 1 MB in bytes

# Vault location (where this script is located)
VAULT = Path(__file__).parent

# Files to monitor and rotate
LOG_FILES = [
    VAULT / "system_log.md",
    VAULT / "Logs" / "watcher_error.log"
]


# ========================================
# HELPER FUNCTIONS
# ========================================

def get_file_size(file_path):
    """
    Returns the size of a file in bytes.
    Returns 0 if file doesn't exist.

    Args:
        file_path (Path): Path to the file

    Returns:
        int: File size in bytes
    """
    try:
        if file_path.exists():
            return file_path.stat().st_size
        return 0
    except Exception as e:
        print(f"[ERROR] Could not get size of {file_path}: {e}")
        return 0


def format_size(size_bytes):
    """
    Converts bytes to human-readable format (KB, MB).

    Args:
        size_bytes (int): Size in bytes

    Returns:
        str: Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def generate_archive_name(original_path):
    """
    Generates a timestamped archive filename for a log file.

    Example:
        system_log.md -> system_log_2026-02-10_18-45-30.md
        watcher_error.log -> watcher_error_2026-02-10_18-45-30.log

    Args:
        original_path (Path): Original file path

    Returns:
        Path: New archived file path with timestamp
    """
    # Get timestamp (YYYY-MM-DD_HH-MM-SS format)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Get file parts
    stem = original_path.stem  # filename without extension
    suffix = original_path.suffix  # file extension (.md, .log, etc.)
    parent = original_path.parent  # directory

    # Create new name: filename_YYYY-MM-DD_HH-MM-SS.ext
    new_name = f"{stem}_{timestamp}{suffix}"

    return parent / new_name


def rotate_log_file(file_path):
    """
    Rotates a log file by renaming it with a timestamp and creating
    a fresh empty file.

    Steps:
        1. Rename original file with timestamp
        2. Create new empty file with original name
        3. Report success or failure

    Args:
        file_path (Path): Path to the log file to rotate

    Returns:
        bool: True if rotation succeeded, False otherwise
    """
    try:
        # Generate archive filename
        archive_path = generate_archive_name(file_path)

        print(f"\n[ROTATING] {file_path.name}")
        print(f"  -> Archiving to: {archive_path.name}")

        # Step 1: Rename original file
        file_path.rename(archive_path)

        # Step 2: Create fresh empty file
        file_path.touch()

        print(f"  -> Created fresh {file_path.name}")
        print(f"[SUCCESS] Rotation complete")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to rotate {file_path}: {e}")
        return False


def check_and_rotate(file_path):
    """
    Checks if a file needs rotation and rotates it if necessary.

    A file needs rotation if:
        - It exists
        - Its size exceeds MAX_FILE_SIZE (1 MB)

    Args:
        file_path (Path): Path to check

    Returns:
        bool: True if file was rotated, False otherwise
    """
    # Check if file exists
    if not file_path.exists():
        print(f"[SKIP] {file_path.name} does not exist")
        return False

    # Get file size
    size = get_file_size(file_path)
    size_str = format_size(size)

    print(f"[CHECK] {file_path.name}: {size_str}")

    # Check if rotation needed
    if size > MAX_FILE_SIZE:
        print(f"  -> Size exceeds limit ({format_size(MAX_FILE_SIZE)})")
        return rotate_log_file(file_path)
    else:
        print(f"  -> Size OK (limit: {format_size(MAX_FILE_SIZE)})")
        return False


# ========================================
# MAIN FUNCTION
# ========================================

def main():
    """
    Main function that checks all log files and rotates them if needed.
    """
    print("=" * 50)
    print("LOG MANAGER - Checking log files...")
    print("=" * 50)

    # Track rotations
    rotated_count = 0

    # Check each log file
    for log_file in LOG_FILES:
        if check_and_rotate(log_file):
            rotated_count += 1

    # Summary
    print("\n" + "=" * 50)
    if rotated_count == 0:
        print("[OK] All log files are within size limits")
    else:
        print(f"[OK] Rotated {rotated_count} log file(s)")
    print("=" * 50)


# ========================================
# RUN THE SCRIPT
# ========================================

if __name__ == "__main__":
    main()
