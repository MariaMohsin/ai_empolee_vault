#!/usr/bin/env python3
"""
Vault File Manager - Production Implementation
Manages task workflow by moving files between vault folders
"""

import argparse
import os
import sys
import shutil
from pathlib import Path


def move_task(filename, from_folder, to_folder):
    """
    Move task file between vault folders

    Args:
        filename: Name of file to move
        from_folder: Source folder name (Inbox, Needs_Action, Done, Needs_Approval)
        to_folder: Destination folder name

    Returns:
        dict: {"success": bool, "message": str}
    """
    # Get vault base path
    script_dir = Path(__file__).parent
    vault_base = script_dir.parent.parent.parent.parent / "AI_Employee_Vault"

    # Validate folder names
    valid_folders = ["Inbox", "Needs_Action", "Done", "Needs_Approval"]
    if from_folder not in valid_folders or to_folder not in valid_folders:
        return {
            "success": False,
            "message": f"Invalid folder name. Valid folders: {', '.join(valid_folders)}"
        }

    # Build paths
    source_path = vault_base / from_folder / filename
    dest_folder_path = vault_base / to_folder
    dest_path = dest_folder_path / filename

    # Check if source file exists
    if not source_path.exists():
        return {
            "success": False,
            "message": f"File not found: {filename} in {from_folder}"
        }

    # Check if destination file already exists
    if dest_path.exists():
        return {
            "success": False,
            "message": f"File already exists in {to_folder}: {filename}"
        }

    try:
        # Create destination folder if it doesn't exist
        dest_folder_path.mkdir(parents=True, exist_ok=True)

        # Move file
        shutil.move(str(source_path), str(dest_path))

        return {
            "success": True,
            "message": f"Moved {filename} from {from_folder} to {to_folder}"
        }

    except PermissionError:
        return {
            "success": False,
            "message": f"Permission denied: Cannot move {filename}"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to move file: {str(e)}"
        }


def main():
    parser = argparse.ArgumentParser(description="Move task files between vault folders")
    parser.add_argument("--file", required=True, help="Filename to move")
    parser.add_argument(
        "--from",
        dest="from_folder",
        required=True,
        help="Source folder (Inbox, Needs_Action, Done, Needs_Approval)"
    )
    parser.add_argument(
        "--to",
        dest="to_folder",
        required=True,
        help="Destination folder (Inbox, Needs_Action, Done, Needs_Approval)"
    )

    args = parser.parse_args()

    # Move task
    result = move_task(
        filename=args.file,
        from_folder=args.from_folder,
        to_folder=args.to_folder
    )

    # Print result
    print(result["message"])

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
