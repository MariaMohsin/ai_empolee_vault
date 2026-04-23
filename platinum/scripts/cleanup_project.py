#!/usr/bin/env python3
"""
cleanup_project.py — Remove all unnecessary files from platinum project.
Run once: python scripts/cleanup_project.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── Folders to delete completely ──────────────────────────────────────────────
DELETE_FOLDERS = [
    # Old tier folders at root (replaced by AI_Employee_Vault/)
    "Done",
    "Plans",
    "Inbox",
    "Inbox_Archive",
    "Skills",
    "claude",               # replaced by .claude/
    "Needs_Approval",       # replaced by AI_Employee_Vault/Pending_Approval/
    "config",               # empty
    "mcp_server",           # unused
    "templates",            # replaced by AI_Employee_Vault/Templates/

    # Old error/retry chains in vault
    "AI_Employee_Vault/Plans",   # old plan files
]

# ── Files to delete ────────────────────────────────────────────────────────────
DELETE_FILES = [
    # Old root-level scripts (replaced by scripts/)
    "file_watcher.py",
    "log_manager.py",

    # Old docs (silver/gold tier planning, no longer needed)
    "system_log.md",
    "SILVER_TIER_PLAN.md",
    "IMPLEMENTATION_ROADMAP.md",
    "TASK_PLANNER_QUICKSTART.md",
    "MCP_EXECUTOR_QUICKSTART.md",
    "HUMAN_APPROVAL_QUICKSTART.md",
    "SILVER_SCHEDULER_QUICKSTART.md",
    "PRODUCTION_SKILLS_GUIDE.md",
    "PRODUCTION_SKILLS_TEST_RESULTS.md",
    "Dashboard.md",                         # replaced by Flask dashboard

    # Windows Task Scheduler script (not needed on Linux)
    "scripts/schedule_ceo_briefing.ps1",

    # Old approval file at root Needs_Approval (already deleted folder above)
]

# ── Infinite retry files in Errors/ ───────────────────────────────────────────
def clean_error_retries():
    errors_dir = ROOT / "AI_Employee_Vault" / "Errors"
    if not errors_dir.exists():
        return 0
    removed = 0
    for f in errors_dir.glob("*.md"):
        if f.name.count("RETRY_") > 1:
            f.unlink()
            print(f"  [DELETED] Errors/{f.name[:70]}...")
            removed += 1
    return removed

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  AI Employee — Project Cleanup")
    print("=" * 60)

    deleted_folders = 0
    deleted_files   = 0

    # Delete folders
    print("\n[Folders]")
    for folder in DELETE_FOLDERS:
        path = ROOT / folder
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            print(f"  [DELETED] {folder}/")
            deleted_folders += 1
        else:
            print(f"  [SKIP]    {folder}/ (not found)")

    # Delete files
    print("\n[Files]")
    for file in DELETE_FILES:
        path = ROOT / file
        if path.exists():
            path.unlink()
            print(f"  [DELETED] {file}")
            deleted_files += 1
        else:
            print(f"  [SKIP]    {file} (not found)")

    # Clean retry chains
    print("\n[Error retry chains]")
    retries = clean_error_retries()
    print(f"  Removed {retries} infinite retry file(s)")

    # Summary
    print("\n" + "=" * 60)
    print(f"  Done — {deleted_folders} folders + {deleted_files} files + {retries} retry files deleted")
    print("=" * 60)

if __name__ == "__main__":
    main()
