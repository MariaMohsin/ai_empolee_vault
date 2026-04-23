#!/usr/bin/env python3
"""
approval_workflow.py — Secure approval lifecycle manager.

Flow:
    Cloud writes draft → Pending_Approval/<type>/
    Human marks APPROVED or REJECTED in the file
    This script moves files through:
        Pending_Approval/ → Approved/ → (executor picks up) → Done/

Rules:
    - NO execution without explicit approval in file
    - NO auto email sending ever
    - Expired approvals auto-move to Done/ with EXPIRED status
    - Rejected items move to Done/ with REJECTED status
    - Every transition is logged

Usage:
    python approval_workflow.py --scan        # process all pending files once
    python approval_workflow.py --daemon      # loop every 60s
    python approval_workflow.py --list        # show pending + status
    python approval_workflow.py --expire-all  # force-expire all pending (safety)
"""

from __future__ import annotations

import os
import sys
import time
import signal
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
VAULT = ROOT / "AI_Employee_Vault"
LOGS  = ROOT / "Logs"
LOG_F = LOGS / "approval_workflow.log"

# How long before a pending approval is auto-expired (per task type)
EXPIRY_SECONDS: dict[str, int] = {
    "email":   3600 * 4,    # 4 hours
    "social":  3600 * 8,    # 8 hours
    "payment": 3600 * 24,   # 24 hours — payments get longer window
    "other":   3600 * 2,    # 2 hours
}
DEFAULT_EXPIRY = 3600 * 4

SCAN_INTERVAL = 60   # seconds between scans in daemon mode

# Decision strings the human writes into the file
APPROVE_MARKER = "DECISION: APPROVED"
REJECT_MARKER  = "DECISION: REJECTED"


# ── logging ───────────────────────────────────────────────────────────────────

def _log(level: str, msg: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    ts   = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [{level:5s}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_F, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ── approval file template ────────────────────────────────────────────────────

def create_approval_file(
    task_id: str,
    task_type: str,
    draft_content: str,
    dest_folder: Path,
    meta: dict | None = None,
) -> Path:
    """
    Write a new pending approval file.
    Called by cloud_agent / cloud orchestrator — not by local agent.
    """
    dest_folder.mkdir(parents=True, exist_ok=True)

    now      = datetime.utcnow()
    expiry_s = EXPIRY_SECONDS.get(task_type, DEFAULT_EXPIRY)
    expires  = (now + timedelta(seconds=expiry_s)).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_iso  = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    extra_meta = ""
    if meta:
        for k, v in meta.items():
            extra_meta += f"{k}: {v}\n"

    content = textwrap.dedent(f"""\
        ---
        task_id: {task_id}
        task_type: {task_type}
        status: pending
        created_at: {now_iso}
        expires_at: {expires}
        {extra_meta.rstrip()}
        ---

        # Approval Request — {task_type.upper()}

        **Task ID:** `{task_id}`
        **Created:** {now_iso}
        **Expires:** {expires}

        ---

        ## Draft Content

        {draft_content}

        ---

        ## ⚠️ Human Decision Required

        Review the draft above, then write ONE of these lines at the bottom of
        this file and save. The system will pick it up automatically.

        **To approve:**
        ```
        DECISION: APPROVED
        ```

        **To reject:**
        ```
        DECISION: REJECTED
        Reason: (optional explanation)
        ```

        > Safety rule: nothing executes until this file contains DECISION: APPROVED.
        > Approval expires at {expires} — expired items are auto-rejected.

        ---

        <!-- system: do not edit below this line -->
    """)

    filepath = dest_folder / f"{task_id}.md"
    filepath.write_text(content, encoding="utf-8")
    _log("INFO", f"Approval file created: {filepath.name}  expires={expires}")
    return filepath


# ── file reader ───────────────────────────────────────────────────────────────

def _read_meta(path: Path) -> dict:
    """Parse YAML front-matter from approval file."""
    meta: dict = {}
    text = path.read_text(encoding="utf-8")
    in_fm = False
    for line in text.splitlines():
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
            else:
                break
            continue
        if in_fm and ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta


def _read_decision(path: Path) -> str:
    """Return 'APPROVED', 'REJECTED', or 'PENDING'."""
    text = path.read_text(encoding="utf-8")
    if APPROVE_MARKER in text:
        return "APPROVED"
    if REJECT_MARKER in text:
        return "REJECTED"
    return "PENDING"


def _read_reject_reason(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("reason:"):
            return line.partition(":")[2].strip()
    return ""


def _is_expired(meta: dict) -> bool:
    exp_str = meta.get("expires_at", "")
    if not exp_str:
        return False
    try:
        exp = datetime.fromisoformat(exp_str.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= exp
    except ValueError:
        return False


# ── file transitions (atomic) ─────────────────────────────────────────────────

def _stamp(path: Path, key: str, value: str) -> None:
    """Insert/update a metadata line in the front-matter."""
    try:
        text  = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        tag   = f"{key}:"
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith(tag):
                lines[i] = f"{key}: {value}"
                updated = True
                break
        if not updated:
            # Insert before closing ---
            if "---" in lines[1:]:
                close_idx = lines.index("---", 1)
                lines.insert(close_idx, f"{key}: {value}")
            else:
                lines.append(f"{key}: {value}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass


def _move(src: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    os.replace(src, dest)
    return dest


# ── scanner ───────────────────────────────────────────────────────────────────

class ApprovalWorkflow:

    def scan(self) -> dict:
        """
        Scan all Pending_Approval subfolders.
        Move files based on decision or expiry.
        Returns counts: {approved, rejected, expired, pending}.
        """
        counts = {"approved": 0, "rejected": 0, "expired": 0, "pending": 0}

        for type_folder in (VAULT / "Pending_Approval").iterdir():
            if not type_folder.is_dir():
                continue
            task_type = type_folder.name

            for path in sorted(type_folder.glob("*.md")):
                if path.name.startswith("."):
                    continue
                try:
                    self._process_one(path, task_type, counts)
                except Exception as exc:
                    _log("ERROR", f"Error processing {path.name}: {exc}")

        _log("INFO",
             f"Scan complete — approved={counts['approved']} "
             f"rejected={counts['rejected']} expired={counts['expired']} "
             f"pending={counts['pending']}")
        return counts

    def _process_one(self, path: Path, task_type: str, counts: dict) -> None:
        meta     = _read_meta(path)
        decision = _read_decision(path)
        ts       = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        # ── expired ──────────────────────────────────────────────────────────
        if decision == "PENDING" and _is_expired(meta):
            _stamp(path, "status",   "expired")
            _stamp(path, "expired_at", ts)
            dest = _move(path, VAULT / "Done")
            _log("WARN", f"EXPIRED → Done/{dest.name}")
            counts["expired"] += 1
            return

        # ── approved ─────────────────────────────────────────────────────────
        if decision == "APPROVED":
            _stamp(path, "status",      "approved")
            _stamp(path, "approved_at", ts)
            dest = _move(path, VAULT / "Approved")
            _log("INFO", f"APPROVED → Approved/{dest.name}")
            counts["approved"] += 1
            return

        # ── rejected ─────────────────────────────────────────────────────────
        if decision == "REJECTED":
            reason = _read_reject_reason(path)
            _stamp(path, "status",      "rejected")
            _stamp(path, "rejected_at", ts)
            if reason:
                _stamp(path, "rejection_reason", reason)
            dest = _move(path, VAULT / "Done")
            _log("INFO", f"REJECTED → Done/{dest.name}  reason='{reason}'")
            counts["rejected"] += 1
            return

        # ── still pending ─────────────────────────────────────────────────────
        counts["pending"] += 1

    def list_pending(self) -> None:
        print(f"\n{'='*60}")
        print(f"  PENDING APPROVALS — {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
        print(f"{'='*60}")
        any_found = False
        for type_folder in (VAULT / "Pending_Approval").iterdir():
            if not type_folder.is_dir():
                continue
            files = sorted(type_folder.glob("*.md"))
            for path in files:
                any_found = True
                meta    = _read_meta(path)
                expires = meta.get("expires_at", "?")
                expired = _is_expired(meta)
                flag    = " [EXPIRED]" if expired else ""
                print(f"  [{type_folder.name}] {path.name}  expires={expires}{flag}")
        if not any_found:
            print("  No pending approvals.")
        print(f"{'='*60}\n")

    def expire_all(self) -> None:
        """Force-expire every pending approval (safety/reset operation)."""
        _log("WARN", "Force-expiring all pending approvals")
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        for type_folder in (VAULT / "Pending_Approval").iterdir():
            if not type_folder.is_dir():
                continue
            for path in type_folder.glob("*.md"):
                _stamp(path, "status",     "expired")
                _stamp(path, "expired_at", ts)
                dest = _move(path, VAULT / "Done")
                _log("WARN", f"Force-expired → Done/{dest.name}")

    def run_daemon(self) -> None:
        self._running = True
        signal.signal(signal.SIGINT,  self._stop)
        signal.signal(signal.SIGTERM, self._stop)
        _log("INFO", f"Approval workflow daemon started (scan every {SCAN_INTERVAL}s)")
        while self._running:
            self.scan()
            if self._running:
                time.sleep(SCAN_INTERVAL)
        _log("INFO", "Approval workflow daemon stopped.")

    def _stop(self, *_) -> None:
        self._running = False


# ── entry ─────────────────────────────────────────────────────────────────────

def main() -> None:
    wf   = ApprovalWorkflow()
    mode = sys.argv[1] if len(sys.argv) > 1 else "--list"
    if mode == "--scan":
        wf.scan()
    elif mode == "--daemon":
        wf.run_daemon()
    elif mode == "--list":
        wf.list_pending()
    elif mode == "--expire-all":
        wf.expire_all()
    else:
        print("Usage: approval_workflow.py [--scan|--daemon|--list|--expire-all]")
        sys.exit(1)


if __name__ == "__main__":
    main()
