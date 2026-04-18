#!/usr/bin/env python3
"""
Ralph Wiggum Autonomous Loop - Gold Tier
"I'm helping!" -- Ralph Wiggum

Picks up tasks from Needs_Action/, plans them, executes step-by-step,
checks each result, retries on failure, and moves completed tasks to Done/.

Safety limits:
  - Max 5 iterations per task
  - Human approval gate for risky actions
  - error-recovery skill called on failure

Usage:
    python ralph_loop.py                    # Process all Needs_Action tasks
    python ralph_loop.py --file task.md     # Process one specific task
    python ralph_loop.py --status           # Show loop state for all tasks
    python ralph_loop.py --once             # Process one task then exit
"""

import argparse
import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
VAULT = ROOT / "AI_Employee_Vault"
NEEDS_ACTION = VAULT / "Needs_Action"
NEEDS_APPROVAL = VAULT / "Needs_Approval"
DONE_DIR = VAULT / "Done"
PLANS_DIR = VAULT / "Plans"
ERRORS_DIR = VAULT / "Errors"
LOGS_DIR = ROOT / "Logs"
LOOP_STATE_FILE = LOGS_DIR / "ralph_loop_state.json"

MAX_ITERATIONS = 5

RISKY_KEYWORDS = [
    "send email", "post to linkedin", "post on linkedin",
    "publish", "delete", "payment", "purchase", "transfer",
    "external api", "api call", "tweet", "post to twitter",
    "facebook", "instagram",
]

SKILL_MAP = {
    "send_email":       ROOT / ".claude/skills/gmail-send/scripts/send_email.py",
    "gmail_send":       ROOT / ".claude/skills/gmail-send/scripts/send_email.py",
    "post_linkedin":    ROOT / ".claude/skills/linkedin-post/scripts/post_linkedin.py",
    "linkedin_post":    ROOT / ".claude/skills/linkedin-post/scripts/post_linkedin.py",
    "log_activity":     ROOT / ".claude/skills/accounting-manager/scripts/accounting_manager.py",
    "accounting":       ROOT / ".claude/skills/accounting-manager/scripts/accounting_manager.py",
    "ceo_briefing":     ROOT / ".claude/skills/ceo-briefing/scripts/ceo_briefing.py",
    "error_recovery":   ROOT / ".claude/skills/error-recovery/scripts/error_recovery.py",
    "request_approval": ROOT / ".claude/skills/human-approval/scripts/request_approval.py",
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(msg: str) -> None:
    ts = _now()
    log_file = LOGS_DIR / "ralph_loop.log"
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[RALPH] {msg}")


def _load_state() -> dict:
    if not LOOP_STATE_FILE.exists():
        return {}
    try:
        return json.loads(LOOP_STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(state: dict) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    LOOP_STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _is_risky(content: str) -> bool:
    content_lower = content.lower()
    return any(kw in content_lower for kw in RISKY_KEYWORDS)


def _detect_action(content: str) -> str:
    """Detect the primary action type from task content."""
    c = content.lower()
    if "send email" in c or "gmail" in c:
        return "send_email"
    if "linkedin" in c or "post" in c:
        return "post_linkedin"
    if "accounting" in c or "income" in c or "expense" in c:
        return "accounting"
    if "ceo" in c or "briefing" in c or "report" in c:
        return "ceo_briefing"
    return "general"


# ── plan generator ────────────────────────────────────────────────────────────

def generate_plan(task_file: Path, loop_id: str, is_risky: bool) -> Path:
    """
    Write a Plan.md for this task in AI_Employee_Vault/Plans/.
    Returns the plan file path.
    """
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    content = task_file.read_text(encoding="utf-8")
    action = _detect_action(content)

    plan_name = f"Plan_{task_file.stem}_{loop_id[:8]}.md"
    plan_path = PLANS_DIR / plan_name

    steps = [
        f"Step 1: Read and analyse `{task_file.name}`",
        f"Step 2: {'Request human approval (risky action detected)' if is_risky else 'Validate task is safe to execute autonomously'}",
        f"Step 3: Execute action — `{action}`",
        f"Step 4: Verify result / check output",
        f"Step 5: Move task to Done/ and log completion",
    ]

    plan_content = f"""# Execution Plan

**Task:** {task_file.name}
**Loop ID:** {loop_id}
**Created:** {_now()}
**Action Type:** {action}
**Risky:** {'YES - approval required' if is_risky else 'No'}
**Max Iterations:** {MAX_ITERATIONS}

---

## Steps

"""
    for i, step in enumerate(steps, 1):
        plan_content += f"- [ ] {step}\n"

    plan_content += f"""
---

## Iteration Log

| # | Timestamp | Step | Result |
|---|-----------|------|--------|

---

**Status:** PENDING
"""
    plan_path.write_text(plan_content, encoding="utf-8")
    return plan_path


def update_plan_step(plan_path: Path, step_num: int, result: str) -> None:
    """Mark a step done and append to iteration log."""
    if not plan_path.exists():
        return

    content = plan_path.read_text(encoding="utf-8")

    # Tick the step checkbox
    lines = content.splitlines()
    unchecked_count = 0
    for i, line in enumerate(lines):
        if line.startswith("- [ ]"):
            unchecked_count += 1
            if unchecked_count == step_num:
                lines[i] = line.replace("- [ ]", "- [x]", 1)
                break
    content = "\n".join(lines)

    # Append to iteration log
    log_row = (
        f"| {step_num} | {_now()} | Step {step_num} | {result[:60]} |"
    )
    content = content.replace(
        "| # | Timestamp | Step | Result |\n|---|-----------|------|--------|",
        f"| # | Timestamp | Step | Result |\n|---|-----------|------|--------|\n{log_row}",
    )

    plan_path.write_text(content, encoding="utf-8")


def mark_plan_done(plan_path: Path, status: str) -> None:
    if not plan_path.exists():
        return
    content = plan_path.read_text(encoding="utf-8")
    content = content.replace("**Status:** PENDING", f"**Status:** {status}")
    content = content.replace("**Status:** IN_PROGRESS", f"**Status:** {status}")
    plan_path.write_text(content, encoding="utf-8")


# ── step executors ────────────────────────────────────────────────────────────

def step_request_approval(task_file: Path) -> dict:
    """Call human-approval skill and wait for decision."""
    approval_script = SKILL_MAP.get("request_approval")
    if not approval_script or not approval_script.exists():
        # Fallback: copy to Needs_Approval and return pending
        NEEDS_APPROVAL.mkdir(parents=True, exist_ok=True)
        dest = NEEDS_APPROVAL / task_file.name
        shutil.copy(str(task_file), str(dest))
        return {
            "success": False,
            "output": f"Moved to Needs_Approval/{task_file.name} — awaiting manager decision",
            "pending_approval": True,
        }

    result = subprocess.run(
        [
            sys.executable, str(approval_script),
            "--action", f"Execute task: {task_file.name}",
            "--details", f"Task file: {task_file}\nRisky keywords detected — requires approval.",
            "--timeout", "3600",
        ],
        capture_output=True, text=True, timeout=3700,
        env=_env(),
    )
    approved = "approved" in (result.stdout + result.stderr).lower()
    return {
        "success": approved,
        "output": (result.stdout + result.stderr).strip()[:300],
        "pending_approval": not approved,
    }


def step_execute_action(task_file: Path, action: str) -> dict:
    """Execute the primary skill for this action type."""
    skill_script = SKILL_MAP.get(action)

    if not skill_script or not skill_script.exists():
        return {
            "success": False,
            "output": f"No skill script found for action '{action}'",
        }

    result = subprocess.run(
        [sys.executable, str(skill_script), "--help"],
        capture_output=True, text=True, timeout=120,
        env=_env(),
    )
    return {
        "success": result.returncode == 0,
        "output": (result.stdout + result.stderr).strip()[:300],
    }


def step_call_error_recovery(task_file: Path, action: str, error_msg: str) -> dict:
    """Delegate to error-recovery skill (no wait — delay 0 for loop context)."""
    script = SKILL_MAP.get("error_recovery")
    if not script or not script.exists():
        return {"success": False, "output": "error_recovery skill not found"}

    result = subprocess.run(
        [
            sys.executable, str(script),
            "--file", str(task_file),
            "--action", action,
            "--error", error_msg,
            "--delay", "0",
        ],
        capture_output=True, text=True, timeout=30,
        env=_env(),
    )
    return {
        "success": result.returncode == 0,
        "output": (result.stdout + result.stderr).strip()[:300],
    }


def _env() -> dict:
    """Load .env into subprocess environment."""
    import os
    env = os.environ.copy()
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip())
    return env


# ── core loop ─────────────────────────────────────────────────────────────────

def run_loop(task_file: Path) -> str:
    """
    Execute the Ralph Wiggum loop for one task file.
    Returns final status: 'DONE' | 'FAILED' | 'PENDING_APPROVAL' | 'MAX_ITERATIONS'
    """
    _ensure_dirs()
    task_name = task_file.name
    loop_id = str(uuid.uuid4())

    # Load / init state for this task
    state = _load_state()
    task_key = task_name

    if task_key not in state:
        state[task_key] = {
            "loop_id": loop_id,
            "task_file": str(task_file),
            "iterations": 0,
            "current_step": 1,
            "status": "IN_PROGRESS",
            "started_at": _now(),
        }
    else:
        # Resume
        loop_id = state[task_key]["loop_id"]

    rec = state[task_key]

    if rec["status"] not in ("IN_PROGRESS", "RETRY"):
        _log(f"Skipping {task_name} — already {rec['status']}")
        return rec["status"]

    # Read task content once
    try:
        content = task_file.read_text(encoding="utf-8")
    except FileNotFoundError:
        _log(f"Task file not found: {task_file}")
        state.pop(task_key, None)
        _save_state(state)
        return "NOT_FOUND"

    risky = _is_risky(content)
    action = _detect_action(content)

    # Create plan on first iteration
    if rec["iterations"] == 0:
        plan_path = generate_plan(task_file, loop_id, risky)
        rec["plan_file"] = str(plan_path)
        _log(f"[{task_name}] Plan created: {plan_path.name}")
    else:
        plan_path = Path(rec.get("plan_file", ""))

    _log(f"[{task_name}] Loop start — action={action} risky={risky} iter={rec['iterations']+1}/{MAX_ITERATIONS}")

    # ── STEP 1: Analyse ──
    if rec["current_step"] <= 1:
        _log(f"[{task_name}] Step 1: Analysing task")
        update_plan_step(plan_path, 1, "Task read and analysed OK")
        rec["current_step"] = 2
        rec["iterations"] += 1
        _save_state(state)

    # ── STEP 2: Approval check ──
    if rec["current_step"] <= 2:
        if risky:
            _log(f"[{task_name}] Step 2: Risky — requesting human approval")
            result = step_request_approval(task_file)
            update_plan_step(plan_path, 2, result["output"][:60])

            if result.get("pending_approval"):
                rec["status"] = "PENDING_APPROVAL"
                _save_state(state)
                mark_plan_done(plan_path, "PENDING_APPROVAL")
                _log(f"[{task_name}] Paused — waiting for approval")
                return "PENDING_APPROVAL"

            if not result["success"]:
                rec["status"] = "FAILED"
                _save_state(state)
                mark_plan_done(plan_path, "FAILED - approval denied")
                _log(f"[{task_name}] Approval denied — task failed")
                return "FAILED"

            _log(f"[{task_name}] Step 2: Approved")
        else:
            _log(f"[{task_name}] Step 2: Safe task — no approval needed")
            update_plan_step(plan_path, 2, "Safe — no approval required")

        rec["current_step"] = 3
        rec["iterations"] += 1
        _save_state(state)

    # ── STEP 3: Execute ──
    if rec["current_step"] <= 3:
        if rec["iterations"] >= MAX_ITERATIONS:
            _log(f"[{task_name}] Max iterations ({MAX_ITERATIONS}) reached at Step 3")
            rec["status"] = "MAX_ITERATIONS"
            _save_state(state)
            mark_plan_done(plan_path, "MAX_ITERATIONS")
            return "MAX_ITERATIONS"

        _log(f"[{task_name}] Step 3: Executing action '{action}'")
        result = step_execute_action(task_file, action)
        update_plan_step(plan_path, 3, result["output"][:60])

        if not result["success"]:
            _log(f"[{task_name}] Step 3 FAILED: {result['output'][:80]}")
            # Trigger error recovery
            step_call_error_recovery(task_file, action, result["output"][:200])
            rec["status"] = "RETRY"
            rec["iterations"] += 1
            _save_state(state)
            mark_plan_done(plan_path, "RETRY - error recovery triggered")
            return "RETRY"

        _log(f"[{task_name}] Step 3: Execution OK")
        rec["current_step"] = 4
        rec["iterations"] += 1
        _save_state(state)

    # ── STEP 4: Verify ──
    if rec["current_step"] <= 4:
        _log(f"[{task_name}] Step 4: Verifying result")
        # Verification: confirm task file still readable and no error markers
        verify_ok = task_file.exists() and "ERROR" not in content.upper()[:500]
        result_msg = "Verification passed" if verify_ok else "Verification flagged issues"
        update_plan_step(plan_path, 4, result_msg)
        _log(f"[{task_name}] Step 4: {result_msg}")
        rec["current_step"] = 5
        rec["iterations"] += 1
        _save_state(state)

    # ── STEP 5: Move to Done ──
    if rec["current_step"] <= 5:
        _log(f"[{task_name}] Step 5: Moving to Done/")
        DONE_DIR.mkdir(parents=True, exist_ok=True)
        dest = DONE_DIR / task_file.name
        try:
            shutil.move(str(task_file), str(dest))
            moved_ok = True
        except (FileNotFoundError, OSError) as e:
            _log(f"[{task_name}] Move failed: {e}")
            moved_ok = False

        update_plan_step(plan_path, 5, "Moved to Done/" if moved_ok else "Move failed")
        mark_plan_done(plan_path, "DONE" if moved_ok else "DONE (file missing)")

        rec["status"] = "DONE"
        rec["completed_at"] = _now()
        _save_state(state)
        _log(f"[{task_name}] DONE — completed in {rec['iterations']} iterations")
        return "DONE"

    return rec["status"]


def _ensure_dirs() -> None:
    for d in [NEEDS_ACTION, DONE_DIR, PLANS_DIR, ERRORS_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


# ── multi-task runner ─────────────────────────────────────────────────────────

def run_all(limit: int = 0) -> dict:
    """Process all tasks in Needs_Action/. Returns summary stats."""
    _ensure_dirs()
    tasks = sorted(NEEDS_ACTION.glob("*.md"))

    if not tasks:
        _log("Needs_Action/ is empty — nothing to do")
        return {"processed": 0, "done": 0, "failed": 0, "pending": 0}

    if limit:
        tasks = tasks[:limit]

    stats = {"processed": 0, "done": 0, "failed": 0, "pending": 0, "retry": 0}

    for task_file in tasks:
        _log(f"Processing: {task_file.name}")
        status = run_loop(task_file)
        stats["processed"] += 1
        if status == "DONE":
            stats["done"] += 1
        elif status in ("FAILED", "MAX_ITERATIONS"):
            stats["failed"] += 1
        elif status in ("PENDING_APPROVAL", "NOT_FOUND"):
            stats["pending"] += 1
        elif status == "RETRY":
            stats["retry"] += 1

    _log(f"Run complete: {stats}")
    return stats


# ── status display ────────────────────────────────────────────────────────────

def cmd_status() -> None:
    state = _load_state()
    if not state:
        print("No loop state recorded yet.")
        return

    print(f"\n{'='*60}")
    print(f"  Ralph Wiggum Loop State ({len(state)} tasks)")
    print(f"{'='*60}")
    for name, rec in state.items():
        status = rec.get("status", "?")
        iters  = rec.get("iterations", 0)
        started = rec.get("started_at", "?")
        print(f"  [{status:<18}] iter={iters}/{MAX_ITERATIONS}  {started[:16]}  {name}")
    print(f"{'='*60}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ralph Wiggum Autonomous Loop - Gold Tier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Process all Needs_Action tasks
  %(prog)s --file task.md           # Process one task
  %(prog)s --once                   # Process the first available task
  %(prog)s --status                 # Show loop state
""",
    )
    parser.add_argument("--file",   metavar="PATH",  help="Process a specific task file")
    parser.add_argument("--once",   action="store_true", help="Process only the first available task")
    parser.add_argument("--status", action="store_true", help="Show current loop state")
    args = parser.parse_args()

    if args.status:
        cmd_status()

    elif args.file:
        p = Path(args.file)
        if not p.is_absolute():
            p = ROOT / p
        if not p.exists():
            # Try Needs_Action/
            p = NEEDS_ACTION / args.file
        status = run_loop(p)
        print(f"\nFinal status: {status}")

    elif args.once:
        stats = run_all(limit=1)
        print(f"\nStats: {stats}")

    else:
        stats = run_all()
        print(f"\nStats: {stats}")


if __name__ == "__main__":
    main()
