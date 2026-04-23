#!/usr/bin/env python3
"""
ceo_briefing.py — Platinum Tier Weekly CEO Briefing

Reads live data from the vault every Sunday and writes:
    AI_Employee_Vault/Briefings/YYYY-MM-DD.md

Data sources:
    Done/                     → completed tasks
    Pending_Approval/         → items waiting for human
    Approved/                 → approved but unexecuted
    Accounting/Current_Month  → revenue / expenses
    Logs/system_health.md     → process health
    Logs/approval_workflow.log → approval audit trail
    Logs/cloud_agent.log      → cloud activity

Usage:
    python ceo_briefing.py               # generate + save (Sunday auto-run)
    python ceo_briefing.py --preview     # print to stdout, do not save
    python ceo_briefing.py --days 14     # extend lookback window
    python ceo_briefing.py --force       # run on any day (skip Sunday check)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT  = Path(__file__).resolve().parent.parent
VAULT = ROOT / "AI_Employee_Vault"
LOGS  = ROOT / "Logs"

BRIEFINGS_DIR  = VAULT / "Briefings"
ACCOUNTING_DIR = VAULT / "Accounting"
DONE_DIR       = VAULT / "Done"
PENDING_DIR    = VAULT / "Pending_Approval"
APPROVED_DIR   = VAULT / "Approved"
IN_PROG_DIR    = VAULT / "In_Progress"
HEALTH_MD      = VAULT / "Logs" / "system_health.md"


# ── helpers ────────────────────────────────────────────────────────────────────

def _cutoff(days: int) -> datetime:
    return datetime.now() - timedelta(days=days)


def _fmt(n: float, currency: str = "PKR") -> str:
    return f"{currency} {n:,.2f}"


# ── collectors ─────────────────────────────────────────────────────────────────

def collect_done_tasks(days: int) -> list[dict]:
    if not DONE_DIR.exists():
        return []
    cutoff = _cutoff(days)
    tasks  = []
    for f in DONE_DIR.glob("*.md"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            continue
        # Read first heading or use stem
        title = f.stem.replace("-", " ").replace("_", " ")
        try:
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        except OSError:
            pass
        # Detect task type from filename
        task_type = "other"
        for t in ("email", "social", "payment"):
            if t in f.name:
                task_type = t
                break
        tasks.append({"title": title, "date": mtime.strftime("%Y-%m-%d"),
                      "type": task_type, "file": f.name})
    return sorted(tasks, key=lambda x: x["date"], reverse=True)


def collect_pending_approvals() -> list[dict]:
    items = []
    if not PENDING_DIR.exists():
        return items
    for type_folder in PENDING_DIR.iterdir():
        if not type_folder.is_dir():
            continue
        for f in type_folder.glob("*.md"):
            age_h = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 3600
            items.append({
                "file":    f.name,
                "type":    type_folder.name,
                "age_h":   round(age_h, 1),
                "old":     age_h > 4,
            })
    return sorted(items, key=lambda x: x["age_h"], reverse=True)


def collect_approved_unexecuted() -> list[dict]:
    if not APPROVED_DIR.exists():
        return []
    return [
        {"file": f.name,
         "age_h": round((datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).total_seconds() / 3600, 1)}
        for f in APPROVED_DIR.glob("*.md")
    ]


def collect_accounting(days: int) -> dict:
    result = {"income": 0.0, "expense": 0.0, "net": 0.0,
              "entries": [], "currency": "PKR"}

    # Try current month file
    acct_file = ACCOUNTING_DIR / "Current_Month.md"
    if not acct_file.exists():
        # Try any markdown in Accounting/
        candidates = list(ACCOUNTING_DIR.glob("*.md"))
        if not candidates:
            return result
        acct_file = sorted(candidates)[-1]

    cutoff_str = _cutoff(days).strftime("%Y-%m-%d")
    in_table   = False

    for line in acct_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if "| Date" in line:
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 3:
                try:
                    date, etype, amount_str = parts[0], parts[1], parts[2]
                    amount = float(amount_str.replace(",", "").replace("PKR", "").strip())
                    desc   = parts[3] if len(parts) > 3 else ""
                    if etype.lower() == "income":
                        result["income"] += amount
                    else:
                        result["expense"] += amount
                    if date >= cutoff_str:
                        result["entries"].append({
                            "date": date, "type": etype.lower(),
                            "amount": amount, "desc": desc
                        })
                except (ValueError, IndexError):
                    pass
        elif in_table and not line.startswith("|"):
            in_table = False

    result["net"] = result["income"] - result["expense"]
    return result


def collect_cloud_stats(days: int) -> dict:
    """Parse cloud_agent.log for cycle count and draft stats."""
    stats = {"cycles": 0, "emails_triaged": 0, "drafts": 0, "errors": 0}
    log   = LOGS / "cloud_agent.log"
    if not log.exists():
        return stats
    cutoff = _cutoff(days).strftime("%Y-%m-%dT")
    try:
        for line in log.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line[:17] < cutoff:
                continue
            if "Cloud cycle #" in line:
                stats["cycles"] += 1
            if "Triaged" in line:
                m = re.search(r"Triaged (\d+)", line)
                if m:
                    stats["emails_triaged"] += int(m.group(1))
            if "Drafts created:" in line:
                m = re.search(r"Drafts created: (\d+)", line)
                if m:
                    stats["drafts"] += int(m.group(1))
            if "[ERROR]" in line:
                stats["errors"] += 1
    except OSError:
        pass
    return stats


def collect_approval_stats(days: int) -> dict:
    """Parse approval_workflow.log for decision counts."""
    stats = {"approved": 0, "rejected": 0, "expired": 0}
    log   = LOGS / "approval_workflow.log"
    if not log.exists():
        return stats
    cutoff = _cutoff(days).strftime("%Y-%m-%dT")
    try:
        for line in log.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line[:17] < cutoff:
                continue
            if "APPROVED" in line:
                stats["approved"] += 1
            elif "REJECTED" in line:
                stats["rejected"] += 1
            elif "EXPIRED" in line:
                stats["expired"] += 1
    except OSError:
        pass
    return stats


def collect_health() -> dict:
    """Read last system_health.md for overall status."""
    health = {"overall": "UNKNOWN", "issues": [], "processes": []}
    if not HEALTH_MD.exists():
        health["issues"].append("system_health.md not found — watchdog may not be running")
        return health
    text = HEALTH_MD.read_text(encoding="utf-8")
    if "✅ HEALTHY" in text:
        health["overall"] = "HEALTHY"
    elif "🔴 DEGRADED" in text:
        health["overall"] = "DEGRADED"
    # Pull issue lines
    for line in text.splitlines():
        if line.startswith("- **Restarted") or "WARNING" in line:
            clean = line.lstrip("- ").strip()
            if clean:
                health["issues"].append(clean)
    return health


def collect_in_progress() -> dict:
    counts = {"cloud": 0, "local": 0}
    for agent in ("cloud", "local"):
        d = IN_PROG_DIR / agent
        counts[agent] = len(list(d.glob("*.md"))) if d.exists() else 0
    return counts


# ── AI suggestions (optional) ──────────────────────────────────────────────────

def generate_suggestions(summary_text: str) -> str:
    """Call Claude via OpenRouter to produce 3 actionable suggestions from the briefing data."""
    api_key = os.environ.get("OPENROUTER_API_KEY", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "_Set OPENROUTER_API_KEY to enable AI-generated suggestions._"
    try:
        from openai import OpenAI
        model = os.environ.get("MODEL", "llama-3.1-8b-instant")
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        response = client.chat.completions.create(
            model=model,
            max_tokens=300,
            messages=[
                {"role": "system", "content": (
                    "You are a sharp business advisor. "
                    "Given a weekly AI employee status report, produce exactly 3 "
                    "concrete, actionable suggestions numbered 1–3. "
                    "Be brief — one sentence each. No preamble."
                )},
                {"role": "user", "content": summary_text},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        return f"_Suggestion generation failed: {exc}_"


# ── alert builder ──────────────────────────────────────────────────────────────

def build_alerts(pending: list, unexecuted: list, acct: dict,
                 health: dict, cloud: dict) -> list[str]:
    alerts = []
    stale  = [p for p in pending if p["old"]]
    if stale:
        alerts.append(f"🔴 {len(stale)} approval(s) waiting >4 hours — review immediately")
    if unexecuted:
        alerts.append(f"🟡 {len(unexecuted)} approved task(s) not yet executed by Local agent")
    if acct["net"] < 0:
        alerts.append(f"🔴 Net balance is negative: {_fmt(acct['net'])}")
    if health["overall"] == "DEGRADED":
        alerts.append("🔴 System health DEGRADED — check Logs/system_health.md")
    if cloud["errors"] > 10:
        alerts.append(f"🟡 Cloud agent logged {cloud['errors']} errors this week")
    for issue in health.get("issues", []):
        if issue and "Restarted" in issue:
            alerts.append(f"♻️ Auto-restart occurred: {issue}")
    return alerts


# ── report builder ─────────────────────────────────────────────────────────────

def build_report(days: int = 7) -> str:
    now    = datetime.now()
    p_from = (now - timedelta(days=days)).strftime("%b %d, %Y")
    p_to   = now.strftime("%b %d, %Y")

    tasks      = collect_done_tasks(days)
    pending    = collect_pending_approvals()
    unexecuted = collect_approved_unexecuted()
    acct       = collect_accounting(days)
    cloud      = collect_cloud_stats(days)
    approvals  = collect_approval_stats(days)
    health     = collect_health()
    in_prog    = collect_in_progress()
    alerts     = build_alerts(pending, unexecuted, acct, health, cloud)

    # Build a plain-text summary for Claude suggestions
    summary = (
        f"Tasks completed: {len(tasks)}. "
        f"Pending approvals: {len(pending)}. "
        f"Approved but unexecuted: {len(unexecuted)}. "
        f"Revenue: {_fmt(acct['income'])}. Expenses: {_fmt(acct['expense'])}. "
        f"Net: {_fmt(acct['net'])}. "
        f"Cloud errors: {cloud['errors']}. "
        f"System: {health['overall']}. "
        f"Alerts: {'; '.join(alerts) or 'none'}."
    )
    suggestions = generate_suggestions(summary)

    # ── task type breakdown
    type_counts: dict[str, int] = {}
    for t in tasks:
        type_counts[t["type"]] = type_counts.get(t["type"], 0) + 1
    type_breakdown = ", ".join(f"{k}: {v}" for k, v in type_counts.items()) or "none"

    lines: list[str] = []

    lines += [
        f"# CEO Weekly Briefing — {now.strftime('%Y-%m-%d')}",
        f"",
        f"**Period:** {p_from} → {p_to}  |  **Generated:** {now.strftime('%Y-%m-%d %H:%M')}  |  **System:** {health['overall']}",
        f"",
    ]

    # ── ALERTS ──
    if alerts:
        lines += ["## ⚠️ Alerts", ""]
        for a in alerts:
            lines.append(f"- {a}")
        lines.append("")
    else:
        lines += ["## ✅ Alerts", "", "- No active alerts.", ""]

    lines.append("---")
    lines.append("")

    # ── REVENUE ──
    net_tag = "PROFIT" if acct["net"] >= 0 else "DEFICIT"
    lines += [
        "## 1. Revenue Summary",
        "",
        f"| Metric | Amount |",
        f"|--------|--------|",
        f"| Income | {_fmt(acct['income'])} |",
        f"| Expenses | {_fmt(acct['expense'])} |",
        f"| **Net** | **{_fmt(acct['net'])} [{net_tag}]** |",
        "",
    ]
    if acct["entries"]:
        lines.append(f"**Transactions this period ({len(acct['entries'])}):**")
        lines.append("")
        for e in acct["entries"][-10:]:  # cap at last 10
            sign = "+" if e["type"] == "income" else "-"
            lines.append(f"- `{e['date']}` {e['type'].capitalize()} {sign}{_fmt(e['amount'])} — {e['desc']}")
        lines.append("")
    else:
        lines += ["_No new transactions this period._", ""]

    # ── TASKS ──
    lines += [
        f"## 2. Tasks Completed ({len(tasks)})",
        f"",
        f"Breakdown by type: {type_breakdown}",
        "",
    ]
    if tasks:
        for t in tasks[:20]:  # cap at 20 in report
            lines.append(f"- `{t['date']}` [{t['type']}] {t['title']}")
        if len(tasks) > 20:
            lines.append(f"- _…and {len(tasks) - 20} more_")
    else:
        lines.append("- No tasks completed this period.")
    lines.append("")

    # ── PENDING APPROVALS ──
    lines += [
        f"## 3. Pending Approvals ({len(pending)})",
        "",
    ]
    if pending:
        for p in pending:
            flag = " ⚠️ STALE" if p["old"] else ""
            lines.append(f"- `{p['type']}/{p['file']}`  waiting {p['age_h']}h{flag}")
        lines += [
            "",
            "> **Action:** Open `AI_Employee_Vault/Pending_Approval/` and add `DECISION: APPROVED` or `DECISION: REJECTED`.",
        ]
    else:
        lines.append("- No pending approvals — inbox clear.")
    lines.append("")

    # ── CLOUD AGENT ──
    lines += [
        "## 4. Cloud Agent Activity",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Cycles run | {cloud['cycles']} |",
        f"| Emails triaged | {cloud['emails_triaged']} |",
        f"| Drafts created | {cloud['drafts']} |",
        f"| Errors logged | {cloud['errors']} |",
        f"| In-progress now (cloud) | {in_prog['cloud']} |",
        f"| In-progress now (local) | {in_prog['local']} |",
        "",
        f"**Approval decisions this period:**  "
        f"Approved {approvals['approved']}  |  Rejected {approvals['rejected']}  |  Expired {approvals['expired']}",
        "",
    ]

    # ── SYSTEM HEALTH ──
    lines += [
        f"## 5. System Health — {health['overall']}",
        "",
    ]
    if health["issues"]:
        for issue in health["issues"]:
            lines.append(f"- {issue}")
    else:
        lines.append("- All systems nominal.")
    lines += [
        "",
        f"> Full report: `AI_Employee_Vault/Logs/system_health.md`",
        "",
    ]

    # ── SUGGESTIONS ──
    lines += [
        "## 6. Suggestions",
        "",
        suggestions,
        "",
    ]

    # ── FOOTER ──
    next_sunday = now + timedelta(days=(6 - now.weekday() + 7) % 7 or 7)
    lines += [
        "---",
        "",
        f"*Platinum AI Employee — auto-generated every Sunday*",
        f"*Next briefing: {next_sunday.strftime('%Y-%m-%d')} (Sunday)*",
    ]

    return "\n".join(lines)


# ── writer ─────────────────────────────────────────────────────────────────────

def write_report(content: str) -> Path:
    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    path     = BRIEFINGS_DIR / f"{date_str}.md"
    # Atomic write
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
    return path


# ── entry ──────────────────────────────────────────────────────────────────────

def _load_env() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main() -> None:
    _load_env()
    parser = argparse.ArgumentParser(description="CEO Weekly Briefing — Platinum Tier")
    parser.add_argument("--preview", action="store_true", help="Print to stdout, do not save")
    parser.add_argument("--days",    type=int, default=7, help="Lookback window in days (default 7)")
    parser.add_argument("--force",   action="store_true", help="Run even if today is not Sunday")
    args = parser.parse_args()

    today = datetime.now().weekday()  # 6 = Sunday
    if today != 6 and not args.preview and not args.force:
        print(f"Today is not Sunday (weekday={today}). Use --force to run anyway.")
        sys.exit(0)

    print(f"Generating CEO briefing (last {args.days} days)…")
    report = build_report(days=args.days)

    if args.preview:
        print("\n" + "=" * 70)
        print(report)
        print("=" * 70)
        print("\n[PREVIEW] Not saved.")
    else:
        path = write_report(report)
        print(f"[OK] Saved → {path}")


if __name__ == "__main__":
    main()
