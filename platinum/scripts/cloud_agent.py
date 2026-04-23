#!/usr/bin/env python3
"""
cloud_agent.py — Cloud Agent (24/7 VM worker)

Responsibilities (read-only for secrets, draft-only for actions):
  1. Watch Gmail -> triage -> write task to Needs_Action/email/
  2. Claim task via atomic rename  (claim-by-move rule)
  3. Draft email reply or social post using Claude
  4. Write draft to Pending_Approval/<type>/ for Local to approve
  5. NEVER executes sends, payments, or WhatsApp — that belongs to Local

Usage:
    python cloud_agent.py --daemon   # run forever (PM2 manages this)
    python cloud_agent.py --once     # single cycle (cron-safe)
    python cloud_agent.py --status   # print queue snapshot
"""

from __future__ import annotations

import os
import sys
import time
import json
import signal
import textwrap
import uuid
from datetime import datetime
from pathlib import Path

# ── bootstrap ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

def _load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

_load_env()

from ownership import (
    OwnershipManager, AGENT_CLOUD,
    TASK_EMAIL, TASK_SOCIAL, TASK_OTHER,
)

VAULT  = ROOT / "AI_Employee_Vault"
LOGS   = ROOT / "Logs"
LOG_F  = LOGS / "cloud_agent.log"

POLL_INTERVAL = int(os.environ.get("CLOUD_POLL_SECONDS", "120"))  # 2 min

# ── logging ────────────────────────────────────────────────────────────────────

def _log(level: str, msg: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"[{ts}] [{level:5s}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_F, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ── Gmail triage ───────────────────────────────────────────────────────────────

class GmailTriager:
    """
    Polls Gmail and converts each unseen email into a task file in
    Needs_Action/email/.  Uses IMAP via imaplib (no external SDK needed).
    Falls back to mock mode when credentials are absent.
    """

    PROCESSED_LOG = LOGS / "cloud_processed_emails.json"

    def __init__(self, owner: OwnershipManager) -> None:
        self.owner = owner
        self._processed: set[str] = self._load_processed()

    def _load_processed(self) -> set[str]:
        if self.PROCESSED_LOG.exists():
            try:
                return set(json.loads(self.PROCESSED_LOG.read_text()))
            except Exception:
                return set()
        return set()

    def _save_processed(self) -> None:
        LOGS.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_LOG.write_text(
            json.dumps(sorted(self._processed), indent=2), encoding="utf-8"
        )

    def _fetch_emails(self) -> list[dict]:
        """Return list of {uid, subject, sender, body} dicts."""
        import imaplib, email as email_lib
        addr = os.environ.get("EMAIL_ADDRESS", "")
        pwd  = os.environ.get("EMAIL_PASSWORD", "")
        if not addr or not pwd:
            _log("WARN", "EMAIL_ADDRESS/PASSWORD not set — using mock emails")
            return self._mock_emails()

        try:
            M = imaplib.IMAP4_SSL("imap.gmail.com")
            M.login(addr, pwd)
            M.select("INBOX")
            _, data = M.search(None, "UNSEEN")
            uids = data[0].split()
            results = []
            for uid in uids[-20:]:  # cap at 20 per cycle
                uid_str = uid.decode()
                if uid_str in self._processed:
                    continue
                _, msg_data = M.fetch(uid, "(RFC822)")
                raw = msg_data[0][1]
                msg = email_lib.message_from_bytes(raw)
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                            break
                else:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                results.append({
                    "uid":     uid_str,
                    "subject": msg.get("Subject", "(no subject)"),
                    "sender":  msg.get("From", "unknown"),
                    "body":    body[:2000],
                })
            M.logout()
            return results
        except Exception as exc:
            _log("ERROR", f"IMAP fetch failed: {exc}")
            return []

    def _mock_emails(self) -> list[dict]:
        return [{
            "uid":     f"mock-{int(time.time())}",
            "subject": "Follow-up on proposal",
            "sender":  "client@example.com",
            "body":    "Hi, just checking in on the proposal we discussed last week.",
        }]

    def triage(self) -> int:
        emails = self._fetch_emails()
        count = 0
        for e in emails:
            if e["uid"] in self._processed:
                continue
            self._write_task(e)
            self._processed.add(e["uid"])
            count += 1
        if count:
            self._save_processed()
        return count

    def _write_task(self, e: dict) -> None:
        task_id = f"email-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        dest = VAULT / "Needs_Action" / "email" / f"{task_id}.md"
        content = textwrap.dedent(f"""\
            ---
            task_id: {task_id}
            task_type: email
            status: needs_action
            created_at: {datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')}
            source_uid: {e['uid']}
            ---

            # Email Task: {e['subject']}

            **From:** {e['sender']}
            **Subject:** {e['subject']}

            ## Body

            {e['body']}

            ## Action Required

            Draft a professional reply to this email.
        """)
        dest.write_text(content, encoding="utf-8")
        _log("INFO", f"Triaged email -> {dest.name}")


# ── Drafter ────────────────────────────────────────────────────────────────────

class CloudDrafter:
    """
    Claims tasks from Needs_Action and produces drafts using Claude API.
    Writes drafts to Pending_Approval/<type>/.
    """

    def __init__(self, owner: OwnershipManager) -> None:
        self.owner = owner

    def process_all(self) -> int:
        count = 0
        for task_type in [TASK_EMAIL, TASK_SOCIAL]:
            for task_file in self.owner.available_tasks(task_type):
                claimed = self.owner.claim(task_file, AGENT_CLOUD)
                if claimed is None:
                    continue  # another agent beat us
                _log("INFO", f"Claimed {claimed.name} ({task_type})")
                try:
                    draft_path = self._draft(claimed, task_type)
                    pending    = self.owner.release_to_pending_approval(draft_path, task_type)
                    _log("INFO", f"Draft ready -> {pending}")
                    count += 1
                except Exception as exc:
                    _log("ERROR", f"Draft failed for {claimed.name}: {exc}")
                    self.owner.release_to_error(claimed, str(exc))
        return count

    def _draft(self, task_file: Path, task_type: str) -> Path:
        text = task_file.read_text(encoding="utf-8")
        # Strip YAML frontmatter so AI doesn't echo metadata into the draft
        if text.startswith("---"):
            parts = text.split("---", 2)
            clean_text = parts[2].strip() if len(parts) >= 3 else text
        else:
            clean_text = text
        draft_body = self._call_claude(clean_text, task_type)
        _stamp_draft(task_file, draft_body)
        return task_file

    def _call_claude(self, task_text: str, task_type: str) -> str:
        api_key = os.environ.get("OPENROUTER_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            _log("WARN", "No API key set — using placeholder draft")
            return "[DRAFT PLACEHOLDER — set OPENROUTER_API_KEY to enable real drafts]"

        try:
            from openai import OpenAI
            model = os.environ.get("MODEL", "llama-3.1-8b-instant")
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.groq.com/openai/v1",
            )

            sender_name = os.environ.get("SENDER_NAME", "Maria Mohsin Channa")
            system = (
                "You are a professional AI assistant. "
                "Produce a concise, polished draft reply. "
                f"Sign the email as '{sender_name}'. "
                "Output only the draft text — no preamble."
            ) if task_type == TASK_EMAIL else (
                "You are a social media manager. "
                "Draft a professional LinkedIn post based on the task. "
                "Max 200 words. Output only the post text."
            )

            response = client.chat.completions.create(
                model=model,
                max_tokens=512,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": task_text},
                ],
            )
            return response.choices[0].message.content
        except Exception as exc:
            _log("ERROR", f"API call failed: {exc}")
            return f"[DRAFT FAILED: {exc}]"


def _stamp_draft(task_file: Path, draft_body: str) -> None:
    """Append the draft section to the task markdown file."""
    text = task_file.read_text(encoding="utf-8")
    separator = "\n\n---\n\n## Cloud Draft\n\n"
    updated = text + separator + draft_body + "\n\n---\n\n**Awaiting Local approval.**\n"
    task_file.write_text(updated, encoding="utf-8")


# ── Dashboard writer ───────────────────────────────────────────────────────────

class DashboardWriter:
    """
    Single-write rule: writes atomically via a temp file + rename so the
    dashboard is never half-written if two processes race.
    Cloud agent only updates its own section.
    """

    DASHBOARD = VAULT / "Dashboard.md"
    LOCK      = LOGS / "dashboard.lock"

    def update_cloud_section(self, stats: dict) -> None:
        # Acquire a simple advisory lock
        for _ in range(10):
            try:
                fd = os.open(str(self.LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                time.sleep(0.3)
        else:
            _log("WARN", "Dashboard lock timeout — skipping update")
            return

        try:
            self._write(stats)
        finally:
            try:
                os.unlink(str(self.LOCK))
            except OSError:
                pass

    def _write(self, stats: dict) -> None:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        section = textwrap.dedent(f"""\
            ## Cloud Agent — {ts}

            | Metric | Value |
            |--------|-------|
            | Emails triaged | {stats.get('emails_triaged', 0)} |
            | Drafts created | {stats.get('drafts_created', 0)} |
            | Pending approval | {stats.get('pending', 0)} |
            | Errors | {stats.get('errors', 0)} |
            | Cycle | #{stats.get('cycle', 0)} |
        """)

        # Read existing dashboard (or create blank)
        if self.DASHBOARD.exists():
            existing = self.DASHBOARD.read_text(encoding="utf-8")
        else:
            existing = "# AI Employee Dashboard\n\n"

        # Replace cloud section or append
        marker_start = "## Cloud Agent"
        marker_end   = "## Local Agent"
        if marker_start in existing:
            before = existing[: existing.index(marker_start)]
            after_raw = existing[existing.index(marker_start):]
            if marker_end in after_raw:
                after = after_raw[after_raw.index(marker_end):]
            else:
                after = ""
            new_content = before + section + "\n" + after
        else:
            new_content = existing + "\n" + section

        # Atomic write via temp file
        tmp = self.DASHBOARD.with_suffix(".tmp")
        tmp.write_text(new_content, encoding="utf-8")
        os.replace(tmp, self.DASHBOARD)


# ── Main loop ──────────────────────────────────────────────────────────────────

class CloudAgent:

    def __init__(self) -> None:
        self.owner    = OwnershipManager(VAULT)
        self.triager  = GmailTriager(self.owner)
        self.drafter  = CloudDrafter(self.owner)
        self.dash     = DashboardWriter()
        self.running  = False
        self.cycle    = 0

    def run_cycle(self) -> dict:
        self.cycle += 1
        stats: dict = {"cycle": self.cycle, "emails_triaged": 0,
                       "drafts_created": 0, "pending": 0, "errors": 0}
        _log("INFO", f"=== Cloud cycle #{self.cycle} ===")

        # Step 1: triage new emails
        try:
            stats["emails_triaged"] = self.triager.triage()
            _log("INFO", f"  Triaged {stats['emails_triaged']} emails")
        except Exception as exc:
            _log("ERROR", f"  Triage failed: {exc}")
            stats["errors"] += 1

        # Step 2: draft and move to Pending_Approval
        try:
            stats["drafts_created"] = self.drafter.process_all()
            _log("INFO", f"  Drafts created: {stats['drafts_created']}")
        except Exception as exc:
            _log("ERROR", f"  Drafting failed: {exc}")
            stats["errors"] += 1

        # Step 3: count pending approvals
        stats["pending"] = len(self.owner.pending_approvals())
        _log("INFO", f"  Pending approval: {stats['pending']}")

        # Step 4: update dashboard (atomic single-write)
        self.dash.update_cloud_section(stats)

        _log("INFO", f"=== Cloud cycle #{self.cycle} done ===")
        return stats

    def run_once(self) -> None:
        self.run_cycle()

    def run_daemon(self) -> None:
        self.running = True
        signal.signal(signal.SIGINT,  self._stop)
        signal.signal(signal.SIGTERM, self._stop)
        _log("INFO", f"Cloud agent daemon started (poll every {POLL_INTERVAL}s)")
        while self.running:
            self.run_cycle()
            if self.running:
                _log("INFO", f"  Sleeping {POLL_INTERVAL}s...")
                time.sleep(POLL_INTERVAL)
        _log("INFO", "Cloud agent stopped.")

    def _stop(self, *_) -> None:
        _log("INFO", "Stop signal received.")
        self.running = False

    def show_status(self) -> None:
        pending = self.owner.pending_approvals()
        approved = self.owner.approved_tasks()
        in_prog  = self.owner.in_progress(AGENT_CLOUD)
        print(f"Pending approval : {len(pending)}")
        print(f"Approved (queued): {len(approved)}")
        print(f"In progress      : {len(in_prog)}")


def main() -> None:
    agent = CloudAgent()
    mode = sys.argv[1] if len(sys.argv) > 1 else "--once"
    if mode == "--daemon":
        agent.run_daemon()
    elif mode == "--once":
        agent.run_once()
    elif mode == "--status":
        agent.show_status()
    else:
        print("Usage: cloud_agent.py [--daemon|--once|--status]")
        sys.exit(1)


if __name__ == "__main__":
    main()
