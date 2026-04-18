#!/usr/bin/env python3
"""
Personal Task Handler - Gold Tier
Manages personal domain tasks in AI_Employee_Vault/Personal/

Separate from Business domain — personal tasks are:
  - Never sent for external approval automatically
  - Logged to Personal/done_log.md (not business logs)
  - Processed by the same Ralph loop but with personal routing

Usage:
    python personal_tasks.py --add "Buy groceries" --priority low
    python personal_tasks.py --add "Call doctor" --priority high --due 2026-04-20
    python personal_tasks.py --list
    python personal_tasks.py --done "task_filename.md"
    python personal_tasks.py --summary
    python personal_tasks.py --process      # auto-process all pending personal tasks
"""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VAULT = ROOT / "AI_Employee_Vault"
PERSONAL_DIR  = VAULT / "Personal"
INBOX_DIR     = PERSONAL_DIR / "Inbox"
DONE_DIR      = PERSONAL_DIR / "Done"
NOTES_DIR     = PERSONAL_DIR / "Notes"
DONE_LOG      = PERSONAL_DIR / "done_log.md"
LOGS_DIR      = ROOT / "Logs"
PERSONAL_LOG  = LOGS_DIR / "personal.log"

PRIORITIES = ("high", "medium", "low")


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    for d in [INBOX_DIR, DONE_DIR, NOTES_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _log(msg: str) -> None:
    ts = _now()
    with open(PERSONAL_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] [PERSONAL] {msg}\n")


# ── done log ──────────────────────────────────────────────────────────────────

def _init_done_log() -> None:
    if DONE_LOG.exists():
        return
    DONE_LOG.write_text(
        "# Personal Tasks — Completed\n\n"
        "| Date | Task | Priority |\n"
        "|------|------|----------|\n"
        f"\n*Last updated: {_now()}*\n",
        encoding="utf-8",
    )


def _record_done(title: str, priority: str) -> None:
    _init_done_log()
    raw = DONE_LOG.read_text(encoding="utf-8")
    row = f"| {_today()} | {title} | {priority.capitalize()} |"
    lines = raw.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("|---"):
            lines.insert(i + 1, row)
            break
    # Update timestamp
    updated = f"*Last updated: {_now()}*"
    new_lines = []
    for line in lines:
        new_lines.append(updated if line.startswith("*Last updated") else line)
    DONE_LOG.write_text("\n".join(new_lines), encoding="utf-8")


# ── task file ─────────────────────────────────────────────────────────────────

def _task_filename(title: str) -> str:
    safe = "".join(c if c.isalnum() or c in "- " else "_" for c in title)[:40].strip().replace(" ", "_")
    return f"{_ts()}_{safe}.md"


def _write_task(title: str, priority: str, due: str, notes: str) -> Path:
    fname = _task_filename(title)
    content = (
        f"# {title}\n\n"
        f"**Domain:** Personal\n"
        f"**Priority:** {priority.capitalize()}\n"
        f"**Created:** {_now()}\n"
        f"**Due:** {due or 'No due date'}\n\n"
        f"---\n\n"
        f"{notes or '_No additional notes._'}\n\n"
        f"---\n\n"
        f"**Status:** Pending\n"
    )
    path = INBOX_DIR / fname
    path.write_text(content, encoding="utf-8")
    return path


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_add(title: str, priority: str, due: str, notes: str) -> None:
    _ensure_dirs()
    priority = priority.lower()
    if priority not in PRIORITIES:
        print(f"Error: priority must be one of {PRIORITIES}", file=sys.stderr)
        sys.exit(1)

    path = _write_task(title, priority, due, notes)
    _log(f"Task added: {path.name} | priority={priority}")
    print(f"[OK] Personal task created: {path.name}")
    print(f"     Title    : {title}")
    print(f"     Priority : {priority.capitalize()}")
    print(f"     Due      : {due or 'none'}")
    print(f"     Location : Personal/Inbox/")


def cmd_list() -> None:
    _ensure_dirs()
    tasks = sorted(INBOX_DIR.glob("*.md"))
    if not tasks:
        print("No pending personal tasks.")
        return

    print(f"\n{'='*50}")
    print(f"  Personal Tasks — Inbox ({len(tasks)})")
    print(f"{'='*50}")
    for f in tasks:
        content = f.read_text(encoding="utf-8")
        title    = content.splitlines()[0].lstrip("# ").strip()
        priority = "medium"
        due      = "none"
        for line in content.splitlines():
            if line.startswith("**Priority:**"):
                priority = line.split(":**")[1].strip().lower()
            if line.startswith("**Due:**"):
                due = line.split(":**")[1].strip()
        print(f"  [{priority.upper():<6}] due={due:<12} {title}")
    print(f"{'='*50}\n")


def cmd_done(filename: str) -> None:
    _ensure_dirs()
    src = INBOX_DIR / filename
    if not src.exists():
        # Try partial match
        matches = list(INBOX_DIR.glob(f"*{filename}*"))
        if not matches:
            print(f"Error: task '{filename}' not found in Personal/Inbox/", file=sys.stderr)
            sys.exit(1)
        src = matches[0]

    content = src.read_text(encoding="utf-8")
    title    = content.splitlines()[0].lstrip("# ").strip()
    priority = "medium"
    for line in content.splitlines():
        if line.startswith("**Priority:**"):
            priority = line.split(":**")[1].strip().lower()

    # Mark done in file
    content = content.replace("**Status:** Pending", f"**Status:** Done — {_today()}")
    src.write_text(content, encoding="utf-8")

    # Move to Done/
    dest = DONE_DIR / src.name
    shutil.move(str(src), str(dest))

    _record_done(title, priority)
    _log(f"Task completed: {src.name}")
    print(f"[OK] Task marked done: {title}")
    print(f"     Moved to: Personal/Done/")


def cmd_summary() -> None:
    _ensure_dirs()
    inbox_tasks = list(INBOX_DIR.glob("*.md"))
    done_tasks  = list(DONE_DIR.glob("*.md"))

    high   = sum(1 for f in inbox_tasks if "**Priority:** High" in f.read_text(encoding="utf-8"))
    medium = sum(1 for f in inbox_tasks if "**Priority:** Medium" in f.read_text(encoding="utf-8"))
    low    = sum(1 for f in inbox_tasks if "**Priority:** Low" in f.read_text(encoding="utf-8"))

    print(f"\n{'='*40}")
    print(f"  Personal Domain Summary")
    print(f"{'='*40}")
    print(f"  Pending tasks : {len(inbox_tasks)}")
    print(f"    High        : {high}")
    print(f"    Medium      : {medium}")
    print(f"    Low         : {low}")
    print(f"  Completed     : {len(done_tasks)}")
    print(f"  Log           : {PERSONAL_LOG}")
    print(f"{'='*40}\n")


def cmd_process() -> None:
    """
    Auto-process personal tasks:
    - High priority → log and move to Done immediately (no external action)
    - Medium/Low   → move to Done after logging
    Designed to be called by the scheduler.
    """
    _ensure_dirs()
    tasks = sorted(INBOX_DIR.glob("*.md"))
    if not tasks:
        print("No personal tasks to process.")
        return

    processed = 0
    for task in tasks:
        content = task.read_text(encoding="utf-8")
        title   = content.splitlines()[0].lstrip("# ").strip()
        priority = "medium"
        for line in content.splitlines():
            if line.startswith("**Priority:**"):
                priority = line.split(":**")[1].strip().lower()

        # Mark and move
        content = content.replace("**Status:** Pending", f"**Status:** Auto-processed — {_today()}")
        task.write_text(content, encoding="utf-8")
        dest = DONE_DIR / task.name
        shutil.move(str(task), str(dest))
        _record_done(title, priority)
        _log(f"Auto-processed: {task.name} | priority={priority}")
        print(f"  [processed] {title}")
        processed += 1

    print(f"\n[OK] Processed {processed} personal task(s)")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Personal Task Handler - Gold Tier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --add "Buy groceries" --priority low
  %(prog)s --add "Call doctor" --priority high --due 2026-04-20
  %(prog)s --list
  %(prog)s --done "task_filename.md"
  %(prog)s --summary
  %(prog)s --process
""",
    )
    parser.add_argument("--add",      metavar="TITLE",    help="Add a personal task")
    parser.add_argument("--priority", default="medium",   help="Priority: high/medium/low")
    parser.add_argument("--due",      default="",         help="Due date: YYYY-MM-DD")
    parser.add_argument("--notes",    default="",         help="Additional notes")
    parser.add_argument("--list",     action="store_true", help="List pending tasks")
    parser.add_argument("--done",     metavar="FILENAME",  help="Mark task as done")
    parser.add_argument("--summary",  action="store_true", help="Show domain summary")
    parser.add_argument("--process",  action="store_true", help="Auto-process all pending (scheduler use)")
    args = parser.parse_args()

    if args.add:
        cmd_add(args.add, args.priority, args.due, args.notes)
    elif args.list:
        cmd_list()
    elif args.done:
        cmd_done(args.done)
    elif args.summary:
        cmd_summary()
    elif args.process:
        cmd_process()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
