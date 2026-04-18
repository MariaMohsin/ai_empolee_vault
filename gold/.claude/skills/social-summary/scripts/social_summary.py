#!/usr/bin/env python3
"""
Social Summary - Gold Tier Agent Skill
Logs every social media post to AI_Employee_Vault/Social_Log.md

Usage:
    python social_summary.py --log linkedin "Your post content here"
    python social_summary.py --log twitter  "Tweet content"
    python social_summary.py --log facebook "Facebook post content"
    python social_summary.py --from-file  AI_Employee_Vault/Needs_Approval/linkedin_post_xyz.md
    python social_summary.py --view
    python social_summary.py --stats
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


# ── paths ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent  # gold/
VAULT = ROOT / "AI_Employee_Vault"
SOCIAL_LOG = VAULT / "Social_Log.md"

SUPPORTED_PLATFORMS = ("linkedin", "twitter", "facebook", "instagram")


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ── log file init ─────────────────────────────────────────────────────────────

def _init_log() -> None:
    VAULT.mkdir(parents=True, exist_ok=True)
    if SOCIAL_LOG.exists():
        return

    SOCIAL_LOG.write_text(
        "# Social Media Log\n\n"
        "> Auto-maintained by social-summary skill.\n\n"
        "---\n\n"
        "## Posts\n\n"
        "| Date | Platform | Preview | Status |\n"
        "|------|----------|---------|--------|\n"
        "\n---\n\n"
        "## Full Content\n\n"
        f"*Last updated: {_now()}*\n",
        encoding="utf-8",
    )


# ── core log operation ────────────────────────────────────────────────────────

def log_post(platform: str, content: str, status: str = "posted") -> None:
    """
    Append one post to Social_Log.md — both the summary table row
    and the full content block.
    """
    platform = platform.lower().strip()
    if platform not in SUPPORTED_PLATFORMS:
        print(f"Warning: '{platform}' is not a recognised platform. Logging anyway.")

    _init_log()

    # Build table row
    preview = content.strip().replace("\n", " ")[:60]
    if len(content.strip()) > 60:
        preview += "..."
    date = _today()
    platform_label = platform.capitalize()
    table_row = f"| {date} | {platform_label} | {preview} | {status.capitalize()} |"

    # Build full content block
    separator = "-" * 50
    content_block = (
        f"\n### {platform_label} — {_now()}\n\n"
        f"**Status:** {status.capitalize()}\n\n"
        f"```\n{content.strip()}\n```\n\n"
        f"{separator}\n"
    )

    # Read file and insert in both sections
    raw = SOCIAL_LOG.read_text(encoding="utf-8")

    # 1. Insert table row after header separator |---| line
    if "|------|" in raw:
        lines = raw.splitlines()
        for i, line in enumerate(lines):
            if line.strip().startswith("|---"):
                lines.insert(i + 1, table_row)
                break
        raw = "\n".join(lines)
    else:
        raw += f"\n{table_row}"

    # 2. Insert full content block before the last timestamp line
    if "*Last updated:" in raw:
        raw = raw.replace(
            raw[raw.rfind("*Last updated:"):],
            content_block + f"*Last updated: {_now()}*\n",
        )
    else:
        raw += content_block + f"\n*Last updated: {_now()}*\n"

    SOCIAL_LOG.write_text(raw, encoding="utf-8")

    print(f"[OK] Logged to Social_Log.md")
    print(f"     Platform : {platform_label}")
    print(f"     Date     : {date}")
    print(f"     Preview  : {preview}")
    print(f"     Status   : {status.capitalize()}")


# ── parse from approval file ──────────────────────────────────────────────────

def log_from_file(filepath: Path) -> None:
    """
    Parse a LinkedIn/social post approval file and log it.
    Detects platform from filename or file content.
    """
    if not filepath.exists():
        print(f"Error: file not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    raw = filepath.read_text(encoding="utf-8")

    # Detect platform
    fname = filepath.name.lower()
    if "linkedin" in fname or "linkedin" in raw.lower()[:200]:
        platform = "linkedin"
    elif "twitter" in fname or "twitter" in raw.lower()[:200]:
        platform = "twitter"
    elif "facebook" in fname or "facebook" in raw.lower()[:200]:
        platform = "facebook"
    elif "instagram" in fname or "instagram" in raw.lower()[:200]:
        platform = "instagram"
    else:
        platform = "social"

    # Detect status
    if "DECISION: APPROVED" in raw:
        status = "approved"
    elif "DECISION: REJECTED" in raw:
        status = "rejected"
    else:
        status = "pending"

    # Extract content between "**Content:**" and the next "---"
    content = ""
    m = re.search(r"\*\*Content:\*\*\s*\n(.*?)(?=\n---|\Z)", raw, re.DOTALL)
    if m:
        content = m.group(1).strip()
    else:
        # Fallback: take everything after "## Post Content"
        m2 = re.search(r"## Post Content\s*\n+(.*?)(?=\n##|\Z)", raw, re.DOTALL)
        if m2:
            content = m2.group(1).strip()

    if not content:
        content = f"(content not parsed from {filepath.name})"

    log_post(platform, content, status=status)


# ── view / stats ──────────────────────────────────────────────────────────────

def cmd_view() -> None:
    _init_log()
    print(SOCIAL_LOG.read_text(encoding="utf-8"))


def cmd_stats() -> None:
    _init_log()
    raw = SOCIAL_LOG.read_text(encoding="utf-8")

    counts: dict[str, int] = {}
    statuses: dict[str, int] = {}
    total = 0

    for line in raw.splitlines():
        if not line.startswith("| ") or "Platform" in line or "---" in line:
            continue
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) >= 4:
            platform = parts[1].lower()
            status   = parts[3].lower()
            counts[platform]  = counts.get(platform, 0) + 1
            statuses[status]  = statuses.get(status, 0) + 1
            total += 1

    SEP = "=" * 40
    print(f"\n{SEP}")
    print(f"  Social Media Summary")
    print(SEP)
    print(f"  Total posts  : {total}")
    print()
    if counts:
        print("  By platform:")
        for p, n in sorted(counts.items()):
            print(f"    {p.capitalize():<12}: {n}")
    if statuses:
        print()
        print("  By status:")
        for s, n in sorted(statuses.items()):
            print(f"    {s.capitalize():<12}: {n}")
    print(f"{SEP}\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Social Summary - Gold Tier AI Employee",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --log linkedin "We just shipped a new feature! #AI"
  %(prog)s --log twitter  "Exciting news coming soon..."
  %(prog)s --from-file AI_Employee_Vault/Needs_Approval/linkedin_post_xyz.md
  %(prog)s --view
  %(prog)s --stats
""",
    )
    parser.add_argument(
        "--log",
        nargs=2,
        metavar=("PLATFORM", "CONTENT"),
        help="Log a post: --log <platform> '<content>'",
    )
    parser.add_argument(
        "--status",
        default="posted",
        metavar="STATUS",
        help="Post status: posted | approved | rejected | pending (default: posted)",
    )
    parser.add_argument(
        "--from-file",
        metavar="PATH",
        help="Parse and log from a Needs_Approval post file",
    )
    parser.add_argument("--view",  action="store_true", help="Print full Social_Log.md")
    parser.add_argument("--stats", action="store_true", help="Show post counts by platform/status")

    args = parser.parse_args()

    if args.log:
        platform, content = args.log
        log_post(platform, content, status=args.status)

    elif args.from_file:
        p = Path(args.from_file)
        if not p.is_absolute():
            p = ROOT / p
        log_from_file(p)

    elif args.view:
        cmd_view()

    elif args.stats:
        cmd_stats()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
