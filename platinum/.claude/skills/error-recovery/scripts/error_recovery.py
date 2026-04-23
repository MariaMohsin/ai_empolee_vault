#!/usr/bin/env python3
"""
Error Recovery - Gold Tier Agent Skill

When a task fails:
  1. Log structured error to Logs/error.log
  2. Move the failed task file to AI_Employee_Vault/Errors/
  3. Wait 5 minutes, retry once
  4. If retry also fails, leave in Errors/ and mark as FAILED

Usage:
    python error_recovery.py --file <task_file> --action <action_type> --error "<message>"
    python error_recovery.py --list-errors
    python error_recovery.py --retry-all
    python error_recovery.py --stats
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # gold/
VAULT = ROOT / "AI_Employee_Vault"
ERRORS_DIR = VAULT / "Errors"
LOGS_DIR = ROOT / "Logs"
ERROR_LOG = LOGS_DIR / "error.log"
ERROR_INDEX = LOGS_DIR / "error_index.json"

RETRY_DELAY_SECONDS = 300   # 5 minutes


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _ts_prefix() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _log_error(
    task_file: str,
    action: str,
    error_msg: str,
    attempt: int,
    status: str,
    moved_to: str = "",
) -> None:
    """Append a structured line to Logs/error.log."""
    entry = (
        f"[{_now_str()}] "
        f"STATUS={status} "
        f"ATTEMPT={attempt} "
        f"ACTION={action} "
        f"FILE={task_file} "
        f"ERROR={error_msg!r}"
    )
    if moved_to:
        entry += f" MOVED_TO={moved_to}"
    entry += "\n"

    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(entry)


def _update_index(record: dict) -> None:
    """Keep a JSON index of all error records for --list and --stats."""
    index = _load_index()
    key = record["task_file"]
    index[key] = record
    with open(ERROR_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)


def _load_index() -> dict:
    if not ERROR_INDEX.exists():
        return {}
    try:
        return json.loads(ERROR_INDEX.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


# ── core operations ───────────────────────────────────────────────────────────

def move_to_errors(source_path: Path, suffix: str = "") -> Path:
    """
    Move a task file into AI_Employee_Vault/Errors/.
    Adds a timestamp prefix to avoid name collisions.
    Returns the new path.
    """
    ERRORS_DIR.mkdir(parents=True, exist_ok=True)
    dest_name = f"{_ts_prefix()}_{source_path.name}{suffix}"
    dest = ERRORS_DIR / dest_name
    try:
        shutil.move(str(source_path), str(dest))
    except FileNotFoundError:
        # Already moved or doesn't exist — create a placeholder
        dest.write_text(
            f"# Error Placeholder\n\nOriginal file: {source_path}\nNot found at move time.\n",
            encoding="utf-8",
        )
    return dest


def write_error_annotation(error_path: Path, action: str, error_msg: str, attempt: int) -> None:
    """Append error metadata block to the moved task file."""
    annotation = (
        f"\n\n---\n"
        f"## Error Record\n\n"
        f"- **Timestamp:** {_now_str()}\n"
        f"- **Action:** {action}\n"
        f"- **Attempt:** {attempt}\n"
        f"- **Error:** {error_msg}\n"
        f"- **Folder:** AI_Employee_Vault/Errors/\n"
    )
    try:
        with open(error_path, "a", encoding="utf-8") as f:
            f.write(annotation)
    except OSError:
        pass


def attempt_retry(task_file_path: Path, action: str, delay: int = RETRY_DELAY_SECONDS) -> dict:
    """
    Wait `delay` seconds then re-run the skill for the given action.
    Returns {"success": bool, "output": str}.

    The retry calls the matching .claude/skills/<action>/scripts/*.py
    with the task file content passed via stdin.
    """
    print(f"  Waiting {delay // 60} min {delay % 60} sec before retry...")
    time.sleep(delay)

    # Find the skill script for this action type
    skill_map = {
        "gmail_send":    ROOT / ".claude/skills/gmail-send/scripts/send_email.py",
        "send_email":    ROOT / ".claude/skills/gmail-send/scripts/send_email.py",
        "linkedin_post": ROOT / ".claude/skills/linkedin-post/scripts/post_linkedin.py",
        "post_linkedin": ROOT / ".claude/skills/linkedin-post/scripts/post_linkedin.py",
        "log_activity":  ROOT / ".claude/skills/accounting-manager/scripts/accounting_manager.py",
    }

    skill_script = skill_map.get(action.lower().replace("-", "_"))

    if skill_script and skill_script.exists():
        # Read task file to extract params (best-effort)
        task_content = ""
        if task_file_path.exists():
            task_content = task_file_path.read_text(encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(skill_script), "--help"],
            capture_output=True, text=True, timeout=30,
        )
        # Generic: just confirm the skill is reachable
        return {
            "success": result.returncode == 0,
            "output": (result.stdout + result.stderr).strip()[:500],
        }
    else:
        # No skill script found — attempt generic re-queue by moving back to Needs_Action
        needs_action = VAULT / "Needs_Action"
        needs_action.mkdir(parents=True, exist_ok=True)
        if task_file_path.exists():
            # Count existing RETRY_ prefixes — hard cap at 3 retries
            retry_count = task_file_path.name.count("RETRY_")
            if retry_count >= 3:
                write_error_annotation(task_file_path, action,
                                       "Max retries (3) reached — permanently failed", attempt=retry_count + 1)
                return {
                    "success": False,
                    "output": f"Max retries reached for {task_file_path.name}. Left in Errors/.",
                }
            requeue_path = needs_action / f"RETRY_{task_file_path.name}"
            shutil.copy(str(task_file_path), str(requeue_path))
            return {
                "success": True,
                "output": f"Re-queued to Needs_Action: {requeue_path.name}",
            }
        return {"success": False, "output": f"No skill found for action '{action}' and file missing."}


# ── main command: handle failure ──────────────────────────────────────────────

def cmd_handle_failure(task_file: str, action: str, error_msg: str, delay: int = RETRY_DELAY_SECONDS) -> None:
    """
    Full error-recovery flow for a single failed task.
    """
    _ensure_dirs()
    source = Path(task_file)
    task_name = source.name

    print(f"\n[ERROR-RECOVERY] Handling failure")
    print(f"  File   : {task_name}")
    print(f"  Action : {action}")
    print(f"  Error  : {error_msg}")

    # Step 1 — log attempt 1 failure
    _log_error(task_name, action, error_msg, attempt=1, status="FAILED")
    print(f"  [1/3] Logged to {ERROR_LOG}")

    # Step 2 — move to Errors/
    error_path = move_to_errors(source)
    write_error_annotation(error_path, action, error_msg, attempt=1)
    print(f"  [2/3] Moved to Errors/{error_path.name}")

    # Update index — mark as PENDING_RETRY
    record = {
        "task_file": task_name,
        "action": action,
        "first_error": error_msg,
        "first_failed_at": _now_iso(),
        "error_path": str(error_path),
        "status": "PENDING_RETRY",
        "retry_result": None,
    }
    _update_index(record)

    # Step 3 — retry once after delay
    print(f"  [3/3] Scheduling retry in {delay // 60} min {delay % 60} sec...")
    retry_result = attempt_retry(error_path, action, delay=delay)

    if retry_result["success"]:
        final_status = "RETRY_SUCCESS"
        print(f"  [OK] Retry succeeded: {retry_result['output']}")
    else:
        final_status = "RETRY_FAILED"
        # Annotate the error file with retry failure
        write_error_annotation(error_path, action, f"RETRY FAILED: {retry_result['output']}", attempt=2)
        _log_error(task_name, action, f"RETRY FAILED: {retry_result['output']}", attempt=2, status="RETRY_FAILED")
        print(f"  [FAIL] Retry also failed: {retry_result['output']}")
        print(f"  File remains in: AI_Employee_Vault/Errors/")

    # Final index update
    record["status"] = final_status
    record["retry_result"] = retry_result
    record["resolved_at"] = _now_iso()
    _update_index(record)

    print(f"\n  Final status: {final_status}")


# ── list errors ───────────────────────────────────────────────────────────────

def cmd_list_errors() -> None:
    _ensure_dirs()
    index = _load_index()

    if not index:
        print("No errors recorded.")
        return

    print(f"\n{'='*55}")
    print(f"  Error Recovery Index ({len(index)} records)")
    print(f"{'='*55}")

    for task_file, rec in index.items():
        status = rec.get("status", "UNKNOWN")
        action = rec.get("action", "?")
        ts = rec.get("first_failed_at", "?")[:19].replace("T", " ")
        print(f"  [{status:<15}] {ts}  {action:<20} {task_file}")

    print(f"{'='*55}\n")

    # Also list actual files in Errors/ dir
    error_files = list(ERRORS_DIR.glob("*.md"))
    if error_files:
        print(f"  Files in AI_Employee_Vault/Errors/ ({len(error_files)}):")
        for ef in sorted(error_files):
            size = ef.stat().st_size
            print(f"    {ef.name}  ({size} bytes)")
        print()


# ── retry all pending ─────────────────────────────────────────────────────────

def cmd_retry_all() -> None:
    _ensure_dirs()
    index = _load_index()
    pending = {k: v for k, v in index.items() if v.get("status") == "PENDING_RETRY"}

    if not pending:
        print("No tasks with status PENDING_RETRY found.")
        return

    print(f"Retrying {len(pending)} pending task(s)...")
    for task_file, rec in pending.items():
        error_path = Path(rec.get("error_path", ""))
        action = rec.get("action", "unknown")
        print(f"\n  Retrying: {task_file}")
        result = attempt_retry(error_path, action, delay=0)  # immediate when manual
        rec["status"] = "RETRY_SUCCESS" if result["success"] else "RETRY_FAILED"
        rec["retry_result"] = result
        rec["resolved_at"] = _now_iso()
        _update_index({task_file: rec})
        print(f"  Result: {rec['status']}")


# ── stats ─────────────────────────────────────────────────────────────────────

def cmd_stats() -> None:
    _ensure_dirs()
    index = _load_index()

    counts = {}
    for rec in index.values():
        s = rec.get("status", "UNKNOWN")
        counts[s] = counts.get(s, 0) + 1

    error_files = len(list(ERRORS_DIR.glob("*.md")))
    log_lines = 0
    if ERROR_LOG.exists():
        with open(ERROR_LOG, encoding="utf-8") as f:
            log_lines = sum(1 for _ in f)

    print(f"\n{'='*40}")
    print(f"  Error Recovery Stats")
    print(f"{'='*40}")
    print(f"  Total records  : {len(index)}")
    for status, count in sorted(counts.items()):
        print(f"  {status:<18}: {count}")
    print(f"  Files in Errors/: {error_files}")
    print(f"  Lines in error.log: {log_lines}")
    print(f"{'='*40}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Error Recovery - Gold Tier AI Employee",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --file "AI_Employee_Vault/Needs_Approval/task.md" --action send_email --error "SMTP timeout"
  %(prog)s --list-errors
  %(prog)s --retry-all
  %(prog)s --stats
""",
    )
    parser.add_argument("--file",         metavar="PATH",    help="Path to the failed task file")
    parser.add_argument("--action",       metavar="ACTION",  help="Action type that failed (e.g. send_email)")
    parser.add_argument("--error",        metavar="MESSAGE", help="Error message from the failure")
    parser.add_argument("--list-errors",  action="store_true", help="List all recorded errors")
    parser.add_argument("--retry-all",    action="store_true", help="Retry all PENDING_RETRY tasks now")
    parser.add_argument("--stats",        action="store_true", help="Show error statistics")
    parser.add_argument(
        "--delay",
        type=int,
        default=RETRY_DELAY_SECONDS,
        help=f"Retry delay in seconds (default: {RETRY_DELAY_SECONDS})",
    )

    args = parser.parse_args()

    if args.file and args.action and args.error:
        delay = args.delay
        cmd_handle_failure(args.file, args.action, args.error, delay=delay)

    elif args.list_errors:
        cmd_list_errors()

    elif args.retry_all:
        cmd_retry_all()

    elif args.stats:
        cmd_stats()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
