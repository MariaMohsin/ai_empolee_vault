#!/usr/bin/env python3
"""
orchestrator.py — Platinum Tier Orchestrator

Replaces run_ai_employee.py.  Supports two runtime modes:

  --cloud   Run as Cloud Agent on VM (24/7, no sensitive actions)
  --local   Run as Local Agent on dev machine (approvals + execution)
  --once    Single cycle of whichever mode
  --status  Print queue snapshot

Usage:
    python orchestrator.py --cloud           # VM: daemon loop
    python orchestrator.py --local           # Dev: daemon loop
    python orchestrator.py --cloud --once    # VM: single cycle (cron)
    python orchestrator.py --local --once    # Dev: single cycle
    python orchestrator.py --status          # Any: show queues
"""

from __future__ import annotations

import os
import sys
import time
import signal
import json
from datetime import datetime
from pathlib import Path

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

LOGS     = ROOT / "Logs"
LOG_F    = LOGS / "orchestrator.log"
LOCK_F   = LOGS / "orchestrator.lock"

CLOUD_INTERVAL = int(os.environ.get("CLOUD_POLL_SECONDS", "120"))   # 2 min
LOCAL_INTERVAL = int(os.environ.get("LOCAL_POLL_SECONDS", "60"))    # 1 min


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


# ── lock ───────────────────────────────────────────────────────────────────────

def _acquire_lock(mode: str) -> bool:
    LOGS.mkdir(parents=True, exist_ok=True)
    if LOCK_F.exists():
        try:
            data = json.loads(LOCK_F.read_text())
            pid  = data.get("pid")
            if pid:
                try:
                    os.kill(pid, 0)
                    _log("ERROR", f"Already running (PID {pid}). Use --unlock.")
                    return False
                except OSError:
                    pass  # stale
        except Exception:
            pass
        LOCK_F.unlink(missing_ok=True)

    LOCK_F.write_text(json.dumps({
        "pid":    os.getpid(),
        "mode":   mode,
        "start":  datetime.utcnow().isoformat(),
    }), encoding="utf-8")
    return True


def _release_lock() -> None:
    LOCK_F.unlink(missing_ok=True)


# ── cloud cycle ────────────────────────────────────────────────────────────────

def run_cloud_cycle() -> dict:
    """Import and run one Cloud Agent cycle."""
    from cloud_agent import CloudAgent
    agent = CloudAgent()
    return agent.run_cycle()


# ── local cycle ────────────────────────────────────────────────────────────────

def run_local_cycle(interactive: bool = False) -> dict:
    """Import and run one Local Agent cycle (auto mode — no keyboard)."""
    from local_agent import LocalAgent
    agent = LocalAgent()
    if interactive:
        agent.review()
    else:
        agent.auto()
    n = len(agent.owner.approved_tasks())
    return {"pending": n}


# ── sync pull helper ───────────────────────────────────────────────────────────

def _sync_pull() -> None:
    """Run vault sync pull (cloud pulls from git before each cycle)."""
    sync_script = ROOT / "scripts" / "sync.sh"
    if not sync_script.exists():
        return
    import subprocess
    result = subprocess.run(
        ["bash", str(sync_script), "pull"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        _log("WARN", f"Sync pull warning: {result.stderr.strip()[:200]}")


def _sync_push() -> None:
    """Push vault changes after cloud writes drafts."""
    sync_script = ROOT / "scripts" / "sync.sh"
    if not sync_script.exists():
        return
    import subprocess
    subprocess.run(
        ["bash", str(sync_script), "push"],
        capture_output=True, text=True, timeout=30,
    )


# ── daemon loop ────────────────────────────────────────────────────────────────

_running = True

def _on_signal(*_) -> None:
    global _running
    _log("INFO", "Stop signal — finishing current cycle then exiting.")
    _running = False


def daemon_cloud() -> None:
    signal.signal(signal.SIGINT,  _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)
    cycle = 0
    _log("INFO", f"Cloud daemon started (interval={CLOUD_INTERVAL}s)")
    while _running:
        cycle += 1
        _log("INFO", f"--- Cloud cycle #{cycle} ---")
        _sync_pull()
        run_cloud_cycle()
        _sync_push()
        if _running:
            time.sleep(CLOUD_INTERVAL)
    _log("INFO", "Cloud daemon stopped.")


def daemon_local() -> None:
    signal.signal(signal.SIGINT,  _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)
    cycle = 0
    _log("INFO", f"Local daemon started (interval={LOCAL_INTERVAL}s)")
    while _running:
        cycle += 1
        _log("INFO", f"--- Local cycle #{cycle} ---")
        run_local_cycle(interactive=False)
        if _running:
            time.sleep(LOCAL_INTERVAL)
    _log("INFO", "Local daemon stopped.")


# ── status ─────────────────────────────────────────────────────────────────────

def show_status() -> None:
    from ownership import OwnershipManager, AGENT_CLOUD, AGENT_LOCAL
    VAULT = ROOT / "AI_Employee_Vault"
    mgr   = OwnershipManager(VAULT)

    print("\n" + "="*60)
    print("  AI EMPLOYEE — PLATINUM STATUS")
    print("="*60)

    for t in ["email", "social", "other"]:
        n = len(mgr.available_tasks(t))
        if n:
            print(f"  Needs_Action/{t:<8}: {n}")

    print(f"  Pending_Approval  : {len(mgr.pending_approvals())}")
    print(f"  Approved (queue)  : {len(mgr.approved_tasks())}")
    print(f"  In_Progress/cloud : {len(mgr.in_progress(AGENT_CLOUD))}")
    print(f"  In_Progress/local : {len(mgr.in_progress(AGENT_LOCAL))}")

    dashboard = VAULT / "Dashboard.md"
    if dashboard.exists():
        lines = dashboard.read_text().splitlines()
        last  = [l for l in lines if l.startswith("## ")]
        if last:
            print(f"\n  Last dashboard update: {last[-1]}")

    if LOCK_F.exists():
        try:
            d = json.loads(LOCK_F.read_text())
            print(f"\n  Running: mode={d['mode']} pid={d['pid']} since={d['start']}")
        except Exception:
            pass
    else:
        print("\n  Daemon: stopped")
    print("="*60 + "\n")


# ── entry ──────────────────────────────────────────────────────────────────────

def main() -> None:
    args = set(sys.argv[1:])

    if "--status" in args:
        show_status()
        return

    if "--unlock" in args:
        _release_lock()
        print("Lock released.")
        return

    once   = "--once"  in args
    cloud  = "--cloud" in args
    local  = "--local" in args

    if not cloud and not local:
        print(__doc__)
        sys.exit(1)

    mode = "cloud" if cloud else "local"

    if not _acquire_lock(mode):
        sys.exit(1)

    try:
        if once:
            if cloud:
                _sync_pull()
                run_cloud_cycle()
                _sync_push()
            else:
                run_local_cycle(interactive=False)
        else:
            if cloud:
                daemon_cloud()
            else:
                daemon_local()
    except Exception as exc:
        _log("ERROR", f"Orchestrator fatal: {exc}")
        sys.exit(1)
    finally:
        _release_lock()


if __name__ == "__main__":
    main()
