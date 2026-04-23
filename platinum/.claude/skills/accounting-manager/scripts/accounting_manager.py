#!/usr/bin/env python3
"""
Accounting Manager - Gold Tier Agent Skill
Maintains AI_Employee_Vault/Accounting/Current_Month.md

Usage:
    python accounting_manager.py --add income 5000 "Client payment - Acme Corp"
    python accounting_manager.py --add expense 200 "Office supplies"
    python accounting_manager.py --summary
    python accounting_manager.py --weekly
    python accounting_manager.py --view
"""

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # gold/
ACCOUNTING_DIR = ROOT / "AI_Employee_Vault" / "Accounting"
CURRENT_MONTH_FILE = ACCOUNTING_DIR / "Current_Month.md"
HISTORY_DIR = ACCOUNTING_DIR / "History"


# ── helpers ───────────────────────────────────────────────────────────────────

def _ensure_dirs() -> None:
    ACCOUNTING_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _month_header() -> str:
    return datetime.now().strftime("%B %Y")


# ── file initialisation ───────────────────────────────────────────────────────

def _init_month_file() -> None:
    """Create Current_Month.md if it doesn't exist or belongs to a past month."""
    header = _month_header()

    if CURRENT_MONTH_FILE.exists():
        first_line = CURRENT_MONTH_FILE.read_text(encoding="utf-8").splitlines()[0]
        if header in first_line:
            return  # already current month
        # Archive old file before starting fresh
        _archive_month()

    template = f"""# Accounting Ledger — {header}

> Auto-maintained by accounting-manager skill.

---

## Entries

| Date | Type | Amount (PKR) | Description |
|------|------|-------------|-------------|

---

## Summary

- **Total Income:** PKR 0.00
- **Total Expenses:** PKR 0.00
- **Net Balance:** PKR 0.00

---

*Last updated: {_now()}*
"""
    CURRENT_MONTH_FILE.write_text(template, encoding="utf-8")


def _archive_month() -> None:
    """Move current file to History/ with month-year name."""
    if not CURRENT_MONTH_FILE.exists():
        return
    content = CURRENT_MONTH_FILE.read_text(encoding="utf-8")
    first_line = content.splitlines()[0] if content else ""
    month_label = first_line.replace("#", "").replace("Accounting Ledger —", "").strip()
    safe_name = month_label.replace(" ", "_") if month_label else "Unknown_Month"
    archive_path = HISTORY_DIR / f"{safe_name}.md"
    CURRENT_MONTH_FILE.rename(archive_path)
    print(f"Archived: {archive_path.name}")


# ── read / parse entries ──────────────────────────────────────────────────────

def _parse_entries() -> list[dict]:
    """Parse all table rows from Current_Month.md."""
    if not CURRENT_MONTH_FILE.exists():
        return []

    entries = []
    in_table = False

    for line in CURRENT_MONTH_FILE.read_text(encoding="utf-8").splitlines():
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
                    entries.append({
                        "date": parts[0],
                        "type": parts[1].lower(),
                        "amount": float(parts[2].replace(",", "")),
                        "description": parts[3],
                    })
                except ValueError:
                    continue
        elif in_table and not line.startswith("|"):
            in_table = False

    return entries


def _totals(entries: list[dict]) -> tuple[float, float]:
    income = sum(e["amount"] for e in entries if e["type"] == "income")
    expense = sum(e["amount"] for e in entries if e["type"] == "expense")
    return income, expense


# ── rewrite summary section ───────────────────────────────────────────────────

def _update_summary(income: float, expense: float) -> None:
    """Rewrite the Summary block in Current_Month.md with fresh totals."""
    content = CURRENT_MONTH_FILE.read_text(encoding="utf-8")
    net = income - expense

    new_summary = (
        f"## Summary\n\n"
        f"- **Total Income:** PKR {income:,.2f}\n"
        f"- **Total Expenses:** PKR {expense:,.2f}\n"
        f"- **Net Balance:** PKR {net:,.2f}\n"
    )

    if "## Summary" in content:
        before = content.split("## Summary")[0]
        after_raw = content.split("## Summary", 1)[1]
        # Find next h2 or end
        if "\n## " in after_raw:
            after = "\n## " + after_raw.split("\n## ", 1)[1]
        else:
            after = ""
        content = before + new_summary + after
    else:
        content += "\n\n" + new_summary

    # Update timestamp
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("*Last updated"):
            lines[i] = f"*Last updated: {_now()}*"
            break
    content = "\n".join(lines)

    CURRENT_MONTH_FILE.write_text(content, encoding="utf-8")


# ── commands ──────────────────────────────────────────────────────────────────

def cmd_add(entry_type: str, amount: float, description: str) -> None:
    """Add an income or expense entry."""
    entry_type = entry_type.lower().strip()
    if entry_type not in ("income", "expense"):
        print("Error: type must be 'income' or 'expense'", file=sys.stderr)
        sys.exit(1)
    if amount <= 0:
        print("Error: amount must be positive", file=sys.stderr)
        sys.exit(1)
    if not description.strip():
        print("Error: description is required", file=sys.stderr)
        sys.exit(1)

    _ensure_dirs()
    _init_month_file()

    content = CURRENT_MONTH_FILE.read_text(encoding="utf-8")
    new_row = f"| {_today()} | {entry_type.capitalize()} | {amount:,.2f} | {description.strip()} |"

    # Insert after the table header separator (e.g. |------|------|...|)
    lines = content.splitlines()
    insert_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|---"):
            insert_idx = i + 1
            break
    if insert_idx is not None:
        lines.insert(insert_idx, new_row)
        content = "\n".join(lines)
    else:
        content += f"\n{new_row}"

    CURRENT_MONTH_FILE.write_text(content, encoding="utf-8")

    # Recalculate and update summary
    entries = _parse_entries()
    income, expense = _totals(entries)
    _update_summary(income, expense)

    symbol = "+" if entry_type == "income" else "-"
    print(f"[OK] {entry_type.capitalize()} logged: {symbol}PKR {amount:,.2f} | {description}")
    print(f"  File: {CURRENT_MONTH_FILE}")


def cmd_summary() -> None:
    """Print total income, expenses, and net balance."""
    _ensure_dirs()
    _init_month_file()

    entries = _parse_entries()
    income, expense = _totals(entries)
    net = income - expense

    SEP = "=" * 45
    print(f"\n{SEP}")
    print(f"  Accounting Summary - {_month_header()}")
    print(SEP)
    print(f"  Total Income   : PKR {income:>12,.2f}")
    print(f"  Total Expenses : PKR {expense:>12,.2f}")
    print(f"  {'-'*32}")
    print(f"  Net Balance    : PKR {net:>12,.2f}  {'[PROFIT]' if net >= 0 else '[DEFICIT]'}")
    print(f"  Entries        : {len(entries)}")
    print(f"{SEP}\n")


def cmd_weekly() -> None:
    """Print a summary for the last 7 days."""
    _ensure_dirs()
    _init_month_file()

    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    all_entries = _parse_entries()
    week_entries = [e for e in all_entries if e["date"] >= cutoff]

    income, expense = _totals(week_entries)
    net = income - expense

    start_label = (datetime.now() - timedelta(days=7)).strftime("%b %d")
    end_label = datetime.now().strftime("%b %d, %Y")

    SEP = "=" * 45
    print(f"\n{SEP}")
    print(f"  Weekly Summary  ({start_label} to {end_label})")
    print(SEP)

    if not week_entries:
        print("  No entries in the last 7 days.")
    else:
        for e in week_entries:
            sign = "+" if e["type"] == "income" else "-"
            print(f"  {e['date']}  {e['type'].capitalize():<10} {sign}PKR {e['amount']:>10,.2f}  {e['description']}")

    print(f"  {'-'*41}")
    print(f"  Income   : PKR {income:>10,.2f}")
    print(f"  Expenses : PKR {expense:>10,.2f}")
    print(f"  Net      : PKR {net:>10,.2f}  {'[PROFIT]' if net >= 0 else '[DEFICIT]'}")
    print(f"{SEP}\n")


def cmd_view() -> None:
    """Print the full Current_Month.md file."""
    _ensure_dirs()
    _init_month_file()
    print(CURRENT_MONTH_FILE.read_text(encoding="utf-8"))


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Accounting Manager — AI Employee Gold Tier",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --add income  5000  "Client payment - Acme Corp"
  %(prog)s --add expense  200  "Office supplies"
  %(prog)s --summary
  %(prog)s --weekly
  %(prog)s --view
""",
    )

    parser.add_argument(
        "--add",
        nargs=3,
        metavar=("TYPE", "AMOUNT", "DESCRIPTION"),
        help="Add entry: --add income|expense <amount> <description>",
    )
    parser.add_argument("--summary", action="store_true", help="Show month totals")
    parser.add_argument("--weekly",  action="store_true", help="Show last-7-day summary")
    parser.add_argument("--view",    action="store_true", help="Print full ledger")

    args = parser.parse_args()

    if args.add:
        entry_type, amount_str, description = args.add
        try:
            amount = float(amount_str.replace(",", ""))
        except ValueError:
            print(f"Error: '{amount_str}' is not a valid amount", file=sys.stderr)
            sys.exit(1)
        cmd_add(entry_type, amount, description)

    elif args.summary:
        cmd_summary()

    elif args.weekly:
        cmd_weekly()

    elif args.view:
        cmd_view()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
