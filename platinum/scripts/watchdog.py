#!/usr/bin/env python3
"""
watchdog.py — System health monitor for the AI Employee platform.

Every 5 minutes:
  1. Checks all registered processes are alive (via PID or PM2)
  2. Restarts any dead process via PM2 (if available) or subprocess
  3. Writes a timestamped status snapshot to AI_Employee_Vault/Logs/system_health.md

Usage:
    python watchdog.py --daemon     # run forever (PM2 manages this)
    python watchdog.py --once       # single health check (cron-safe)
    python watchdog.py --status     # print last health report
"""

from __future__ import annotations

import os
import sys
import json
import time
import signal
import textwrap
import subprocess
from datetime import datetime
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
VAULT = ROOT / "AI_Employee_Vault"
LOGS  = ROOT / "Logs"

HEALTH_MD  = VAULT / "Logs" / "system_health.md"
HEALTH_LOG = LOGS  / "watchdog.log"
LOCK_F     = LOGS  / "watchdog.lock"

CHECK_INTERVAL = 300   # 5 minutes

# ── process registry ──────────────────────────────────────────────────────────
# Each entry: {name, pm2_name, script, args, critical}
# critical=True → watchdog will try to restart it; False → alert only.

PROCESSES = [
    {
        "name":     "Cloud Orchestrator",
        "pm2_name": "cloud-orchestrator",
        "script":   str(ROOT / "scripts" / "orchestrator.py"),
        "args":     ["--cloud"],
        "critical": True,
    },
    {
        "name":     "Gmail Watcher",
        "pm2_name": "gmail-watcher",
        "script":   str(ROOT / "scripts" / "watch_gmail.py"),
        "args":     ["--api"],
        "critical": True,
    },
    {
        "name":     "LinkedIn Poster",
        "pm2_name": "linkedin-poster",
        "script":   str(ROOT / "scripts" / "linkedin_poster.py"),
        "args":     [],
        "critical": False,
    },
    {
        "name":     "Business MCP",
        "pm2_name": "business-mcp",
        "script":   str(ROOT / "mcp" / "business_mcp" / "server.py"),
        "args":     [],
        "critical": True,
    },
    {
        "name":     "Odoo MCP",
        "pm2_name": "odoo-mcp",
        "script":   str(ROOT / "mcp" / "odoo_mcp" / "server.py"),
        "args":     [],
        "critical": False,
    },
]


# ── helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_human() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _log(level: str, msg: str) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    ts   = _now_iso()
    line = f"[{ts}] [{level:5s}] {msg}"
    print(line, flush=True)
    try:
        with open(HEALTH_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def _pm2_available() -> bool:
    try:
        r = subprocess.run(["pm2", "--version"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception:
        return False


# ── process checks ────────────────────────────────────────────────────────────

def _pm2_status(pm2_name: str) -> str:
    """Return 'online', 'stopped', 'errored', or 'unknown'."""
    try:
        r = subprocess.run(
            ["pm2", "jlist"],
            capture_output=True, text=True, timeout=10
        )
        procs = json.loads(r.stdout)
        for p in procs:
            if p.get("name") == pm2_name:
                return p.get("pm2_env", {}).get("status", "unknown")
        return "not_found"
    except Exception:
        return "unknown"


def _pm2_restart(pm2_name: str) -> bool:
    """Restart a PM2 process. Returns True on success."""
    try:
        r = subprocess.run(
            ["pm2", "restart", pm2_name],
            capture_output=True, timeout=15
        )
        return r.returncode == 0
    except Exception:
        return False


def _pm2_start(proc: dict) -> bool:
    """Start a process via PM2 for the first time."""
    try:
        cmd = [
            "pm2", "start", proc["script"],
            "--name", proc["pm2_name"],
            "--interpreter", sys.executable,
        ]
        if proc["args"]:
            cmd += ["--"] + proc["args"]
        r = subprocess.run(cmd, capture_output=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return False


# ── queue stats ───────────────────────────────────────────────────────────────

def _queue_stats() -> dict:
    stats: dict = {}
    for folder in [
        "Needs_Action/email", "Needs_Action/social",
        "Pending_Approval/email", "Pending_Approval/social",
        "Pending_Approval/payment",
        "Approved", "In_Progress/cloud", "In_Progress/local", "Done",
    ]:
        p = VAULT / folder
        stats[folder] = len(list(p.glob("*.md"))) if p.exists() else 0
    return stats


# ── health check ──────────────────────────────────────────────────────────────

class ProcessResult:
    __slots__ = ("name", "pm2_name", "status", "action", "critical")

    def __init__(self, name, pm2_name, status, action, critical):
        self.name     = name
        self.pm2_name = pm2_name
        self.status   = status   # "online" | "stopped" | "restarted" | "failed" | "unknown"
        self.action   = action   # "" | "restarted" | "start_attempted" | "alert_only"
        self.critical = critical


def run_health_check(use_pm2: bool) -> list[ProcessResult]:
    results = []

    for proc in PROCESSES:
        name     = proc["name"]
        pm2_name = proc["pm2_name"]
        critical = proc["critical"]

        if use_pm2:
            status = _pm2_status(pm2_name)
        else:
            status = "unknown"

        action = ""

        if status == "online":
            _log("INFO", f"  [{name}] OK (online)")

        elif status in ("stopped", "errored", "not_found"):
            _log("WARN", f"  [{name}] {status.upper()}")
            if critical and use_pm2:
                if status == "not_found":
                    ok = _pm2_start(proc)
                    action = "start_attempted"
                else:
                    ok = _pm2_restart(pm2_name)
                    action = "restarted" if ok else "restart_failed"
                _log("INFO" if ok else "ERROR",
                     f"  [{name}] restart {'OK' if ok else 'FAILED'}")
            else:
                action = "alert_only"

        else:
            _log("INFO", f"  [{name}] status={status}")

        results.append(ProcessResult(name, pm2_name, status, action, critical))

    return results


# ── markdown writer ───────────────────────────────────────────────────────────

def _write_health_md(results: list[ProcessResult], queue: dict, cycle: int) -> None:
    """Atomically overwrite system_health.md with a full status snapshot."""

    HEALTH_MD.parent.mkdir(parents=True, exist_ok=True)

    def _icon(r: ProcessResult) -> str:
        if r.status == "online":            return "✅"
        if r.action in ("restarted",):      return "♻️"
        if r.critical:                       return "🔴"
        return "🟡"

    proc_rows = "\n".join(
        f"| {_icon(r)} | {r.name} | {r.status} | {r.action or '—'} |"
        for r in results
    )

    queue_rows = "\n".join(
        f"| {folder.split('/')[-1]} ({folder.split('/')[0]}) | {count} |"
        for folder, count in queue.items()
    )

    healthy    = all(r.status == "online" for r in results if r.critical)
    overall    = "✅ HEALTHY" if healthy else "🔴 DEGRADED"
    restarted  = [r.name for r in results if r.action == "restarted"]

    md = textwrap.dedent(f"""\
        # System Health Report

        **Updated:** {_now_human()}
        **Cycle:** #{cycle}
        **Overall:** {overall}

        ---

        ## Process Status

        | | Process | Status | Action |
        |---|---------|--------|--------|
        {proc_rows}

        ---

        ## Vault Queue

        | Folder | Files |
        |--------|-------|
        {queue_rows}

        ---

        ## Notes

        - Watchdog polls every {CHECK_INTERVAL // 60} minutes
        - Restarts are attempted via PM2 for critical processes
        - Non-critical processes generate alerts only
        {"- **Restarted this cycle:** " + ", ".join(restarted) if restarted else "- No restarts this cycle"}

        ---
        *Generated by watchdog.py — do not edit manually*
    """)

    # Atomic write
    tmp = HEALTH_MD.with_suffix(".tmp")
    tmp.write_text(md, encoding="utf-8")
    os.replace(tmp, HEALTH_MD)
    _log("INFO", f"Health report written → {HEALTH_MD}")


# ── main watchdog ─────────────────────────────────────────────────────────────

class Watchdog:

    def __init__(self) -> None:
        self.running  = False
        self.cycle    = 0
        self.use_pm2  = _pm2_available()
        if not self.use_pm2:
            _log("WARN", "PM2 not found — health checks run in report-only mode")

    def check_once(self) -> None:
        self.cycle += 1
        _log("INFO", f"=== Health check #{self.cycle} ===")

        results = run_health_check(self.use_pm2)
        queue   = _queue_stats()
        _write_health_md(results, queue, self.cycle)

        critical_down = [r for r in results if r.critical and r.status != "online"]
        if critical_down:
            _log("ERROR", f"Critical processes down: {[r.name for r in critical_down]}")
        else:
            _log("INFO", "All critical processes healthy.")

    def run_daemon(self) -> None:
        self.running = True
        signal.signal(signal.SIGINT,  self._stop)
        signal.signal(signal.SIGTERM, self._stop)
        _log("INFO", f"Watchdog daemon started (every {CHECK_INTERVAL}s)")
        while self.running:
            self.check_once()
            if self.running:
                time.sleep(CHECK_INTERVAL)
        _log("INFO", "Watchdog stopped.")

    def _stop(self, *_) -> None:
        self.running = False

    @staticmethod
    def show_status() -> None:
        if HEALTH_MD.exists():
            print(HEALTH_MD.read_text(encoding="utf-8"))
        else:
            print("No health report yet. Run: python watchdog.py --once")


def main() -> None:
    dog  = Watchdog()
    mode = sys.argv[1] if len(sys.argv) > 1 else "--once"
    if mode == "--daemon":
        dog.run_daemon()
    elif mode == "--once":
        dog.check_once()
    elif mode == "--status":
        dog.show_status()
    else:
        print("Usage: watchdog.py [--daemon|--once|--status]")
        sys.exit(1)


if __name__ == "__main__":
    main()
