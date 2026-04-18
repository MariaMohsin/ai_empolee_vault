#!/usr/bin/env python3
"""
CEO Briefing Generator - Gold Tier Agent Skill
Generates AI_Employee_Vault/Reports/CEO_Weekly_<date>.md

Usage:
    python ceo_briefing.py              # Generate this week's briefing
    python ceo_briefing.py --preview    # Print to stdout only (no file written)
    python ceo_briefing.py --days 14    # Look back 14 days instead of 7
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # gold/
VAULT = ROOT / "AI_Employee_Vault"
REPORTS_DIR = VAULT / "Reports"
LOGS_DIR = ROOT / "Logs"
ACCOUNTING_FILE = VAULT / "Accounting" / "Current_Month.md"


# ── data collectors ───────────────────────────────────────────────────────────

def _cutoff(days: int) -> str:
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def collect_tasks_done(days: int) -> list[dict]:
    done_dir = VAULT / "Done"
    if not done_dir.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    tasks = []
    for f in done_dir.glob("*.md"):
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime >= cutoff:
            title = f.stem.replace("_", " ")
            tasks.append({
                "file": f.name,
                "title": title,
                "date": mtime.strftime("%Y-%m-%d"),
            })

    return sorted(tasks, key=lambda x: x["date"], reverse=True)


def collect_emails_sent(days: int) -> list[dict]:
    """Read from processed_emails.json — each entry was a processed/sent email."""
    log_file = LOGS_DIR / "processed_emails.json"
    if not log_file.exists():
        return []

    try:
        data = json.loads(log_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    emails = []
    for entry in data.get("processed_emails", []):
        processed_at = entry.get("processed_at", "")
        if processed_at >= cutoff:
            emails.append({
                "subject": entry.get("subject", "Unknown"),
                "date": processed_at[:10],
                "id": entry.get("email_id", ""),
            })

    return sorted(emails, key=lambda x: x["date"], reverse=True)


def collect_linkedin_posts(days: int) -> list[dict]:
    """Detect LinkedIn posts from Needs_Approval + actions.log."""
    posts = []
    cutoff = datetime.now() - timedelta(days=days)

    # Check Needs_Approval for linkedin post files (approved or pending)
    approval_dir = VAULT / "Needs_Approval"
    if approval_dir.exists():
        for f in approval_dir.iterdir():
            if "linkedin" not in f.name.lower():
                continue
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                continue
            status = "Approved" if f.suffix == ".approved" else "Pending"
            posts.append({
                "file": f.name,
                "date": mtime.strftime("%Y-%m-%d"),
                "status": status,
            })

    # Also scan action.log for linkedin execution lines
    action_log = LOGS_DIR / "action.log"
    if action_log.exists():
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        with open(action_log, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "linkedin" in line.lower() and "[EXECUTE]" in line:
                    date_part = line[1:11]  # [2026-04-18 ...]
                    if date_part >= cutoff_str:
                        posts.append({
                            "file": "from action.log",
                            "date": date_part,
                            "status": "Executed",
                        })

    return sorted(posts, key=lambda x: x["date"], reverse=True)


def collect_pending_approvals() -> list[dict]:
    approval_dir = VAULT / "Needs_Approval"
    if not approval_dir.exists():
        return []

    pending = []
    for f in approval_dir.glob("*.md"):
        # .approved and .rejected files are settled
        pending.append({
            "file": f.name,
            "date": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })

    return sorted(pending, key=lambda x: x["date"], reverse=True)


def collect_accounting(days: int) -> dict:
    """Parse Current_Month.md for income/expense totals in the period."""
    result = {
        "total_income": 0.0,
        "total_expense": 0.0,
        "net": 0.0,
        "entries_this_period": [],
        "source": str(ACCOUNTING_FILE),
    }

    if not ACCOUNTING_FILE.exists():
        return result

    cutoff_date = _cutoff(days)
    in_table = False

    for line in ACCOUNTING_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("| Date"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|") and line.endswith("|"):
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 4:
                try:
                    date, entry_type, amount_str, desc = parts
                    amount = float(amount_str.replace(",", ""))
                    if date >= cutoff_date:
                        result["entries_this_period"].append({
                            "date": date,
                            "type": entry_type.lower(),
                            "amount": amount,
                            "description": desc,
                        })
                    if entry_type.lower() == "income":
                        result["total_income"] += amount
                    else:
                        result["total_expense"] += amount
                except (ValueError, IndexError):
                    continue
        elif in_table and not line.startswith("|"):
            in_table = False

    result["net"] = result["total_income"] - result["total_expense"]
    return result


def collect_system_health() -> dict:
    """Check log sizes, last run time, and key directories."""
    health = {
        "status": "OK",
        "issues": [],
        "stats": {},
    }

    # Check log files
    for log_name in ["action.log", "actions.log", "ai_employee.log"]:
        log_file = LOGS_DIR / log_name
        if log_file.exists():
            size_kb = log_file.stat().st_size / 1024
            last_mod = datetime.fromtimestamp(log_file.stat().st_mtime)
            health["stats"][log_name] = {
                "size_kb": round(size_kb, 1),
                "last_modified": last_mod.strftime("%Y-%m-%d %H:%M"),
            }
            # Warn if log > 5MB
            if size_kb > 5120:
                health["issues"].append(f"{log_name} is large ({size_kb:.0f} KB) — consider rotation")
                health["status"] = "WARNING"

    # Check vault directories exist and are accessible
    for folder in ["Inbox", "Done", "Needs_Approval", "Needs_Action", "Accounting"]:
        folder_path = VAULT / folder
        health["stats"][f"vault_{folder.lower()}"] = {
            "exists": folder_path.exists(),
            "files": len(list(folder_path.glob("*"))) if folder_path.exists() else 0,
        }

    # Check if ai_employee ran in the last 24 hours
    ai_log = LOGS_DIR / "ai_employee.log"
    if ai_log.exists():
        last_run = datetime.fromtimestamp(ai_log.stat().st_mtime)
        hours_since = (datetime.now() - last_run).total_seconds() / 3600
        if hours_since > 24:
            health["issues"].append(f"AI employee last ran {hours_since:.0f}h ago — may be stalled")
            health["status"] = "WARNING"
        health["stats"]["last_ai_run"] = last_run.strftime("%Y-%m-%d %H:%M")
    else:
        health["issues"].append("ai_employee.log not found — scheduler may not be running")
        health["status"] = "WARNING"

    return health


# ── report builder ─────────────────────────────────────────────────────────────

def build_report(days: int = 7) -> str:
    now = datetime.now()
    period_start = (now - timedelta(days=days)).strftime("%b %d, %Y")
    period_end = now.strftime("%b %d, %Y")
    generated_at = now.strftime("%Y-%m-%d %H:%M")

    tasks = collect_tasks_done(days)
    emails = collect_emails_sent(days)
    linkedin = collect_linkedin_posts(days)
    pending = collect_pending_approvals()
    accounting = collect_accounting(days)
    health = collect_system_health()

    lines = []

    # ── header ──
    lines += [
        f"# CEO Weekly Briefing",
        f"",
        f"**Period:** {period_start} to {period_end}",
        f"**Generated:** {generated_at}",
        f"**System Status:** {health['status']}",
        f"",
        f"---",
        f"",
    ]

    # ── tasks completed ──
    lines += [
        f"## 1. Tasks Completed ({len(tasks)})",
        f"",
    ]
    if tasks:
        for t in tasks:
            lines.append(f"- [{t['date']}] {t['title']}")
    else:
        lines.append("- No tasks completed in this period.")
    lines.append("")

    # ── emails ──
    lines += [
        f"## 2. Emails Processed ({len(emails)})",
        f"",
    ]
    if emails:
        for e in emails:
            lines.append(f"- [{e['date']}] {e['subject']}")
    else:
        lines.append("- No emails processed in this period.")
    lines.append("")

    # ── linkedin ──
    lines += [
        f"## 3. LinkedIn Activity ({len(linkedin)})",
        f"",
    ]
    if linkedin:
        for p in linkedin:
            lines.append(f"- [{p['date']}] {p['status']} — {p['file']}")
    else:
        lines.append("- No LinkedIn activity in this period.")
    lines.append("")

    # ── pending approvals ──
    lines += [
        f"## 4. Pending Approvals ({len(pending)})",
        f"",
    ]
    if pending:
        for p in pending:
            lines.append(f"- {p['file']}  (waiting since {p['date']})")
        lines.append("")
        lines.append("> **Action Required:** Review files in `AI_Employee_Vault/Needs_Approval/`")
    else:
        lines.append("- No pending approvals. All clear.")
    lines.append("")

    # ── accounting ──
    net = accounting["net"]
    net_label = "[PROFIT]" if net >= 0 else "[DEFICIT]"
    lines += [
        f"## 5. Financial Summary (Month to Date)",
        f"",
        f"| Metric | Amount |",
        f"|--------|--------|",
        f"| Total Income | PKR {accounting['total_income']:,.2f} |",
        f"| Total Expenses | PKR {accounting['total_expense']:,.2f} |",
        f"| **Net Balance** | **PKR {net:,.2f} {net_label}** |",
        f"",
    ]

    period_entries = accounting["entries_this_period"]
    if period_entries:
        lines.append(f"**Transactions this period ({len(period_entries)}):**")
        lines.append("")
        for e in period_entries:
            sign = "+" if e["type"] == "income" else "-"
            lines.append(f"- [{e['date']}] {e['type'].capitalize()} {sign}PKR {e['amount']:,.2f} — {e['description']}")
    else:
        lines.append("_No new transactions recorded this period._")
    lines.append("")

    # ── system health ──
    lines += [
        f"## 6. System Health — {health['status']}",
        f"",
    ]

    if health["issues"]:
        lines.append("**Issues:**")
        for issue in health["issues"]:
            lines.append(f"- WARNING: {issue}")
        lines.append("")

    # Log stats table
    log_stats = {k: v for k, v in health["stats"].items() if "log" in k or "last_ai" in k}
    if log_stats:
        lines.append("**Log Files:**")
        lines.append("")
        lines.append("| File | Size | Last Modified |")
        lines.append("|------|------|---------------|")
        for name, info in log_stats.items():
            if isinstance(info, dict) and "size_kb" in info:
                lines.append(f"| {name} | {info['size_kb']} KB | {info['last_modified']} |")
        if "last_ai_run" in health["stats"]:
            lines.append(f"| Last AI Run | — | {health['stats']['last_ai_run']} |")
        lines.append("")

    # Vault stats
    vault_stats = {k: v for k, v in health["stats"].items() if k.startswith("vault_")}
    if vault_stats:
        lines.append("**Vault Folders:**")
        lines.append("")
        lines.append("| Folder | Files |")
        lines.append("|--------|-------|")
        for key, info in vault_stats.items():
            folder_name = key.replace("vault_", "").capitalize()
            status_mark = "OK" if info["exists"] else "MISSING"
            lines.append(f"| {folder_name} | {info['files']} ({status_mark}) |")
        lines.append("")

    # ── footer ──
    lines += [
        f"---",
        f"",
        f"*Auto-generated by ceo-briefing skill | AI Employee Gold Tier*",
        f"*Next briefing: {(now + timedelta(days=7)).strftime('%Y-%m-%d')}*",
    ]

    return "\n".join(lines)


# ── write report ──────────────────────────────────────────────────────────────

def write_report(content: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    report_path = REPORTS_DIR / f"CEO_Weekly_{date_str}.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="CEO Briefing Generator - Gold Tier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                 # Generate weekly briefing (7 days)
  %(prog)s --preview       # Print to stdout only
  %(prog)s --days 14       # Look back 14 days
""",
    )
    parser.add_argument("--preview", action="store_true", help="Print report to stdout without saving")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    args = parser.parse_args()

    print(f"Generating CEO briefing (last {args.days} days)...")
    report = build_report(days=args.days)

    if args.preview:
        print("\n" + "=" * 60)
        print(report)
        print("=" * 60)
        print("\n[PREVIEW] Report not saved.")
    else:
        path = write_report(report)
        print(f"[OK] Report saved: {path}")
        print(f"     Sections: Tasks | Emails | LinkedIn | Approvals | Finance | Health")


if __name__ == "__main__":
    main()
