#!/usr/bin/env bash
# cron_setup.sh — Register all AI Employee cron jobs on the VM
# Run once after deployment: bash scripts/cron_setup.sh
set -euo pipefail

PROJ="/opt/ai_employee/platinum"
PY="/opt/ai_employee/venv/bin/python"
LOG="$PROJ/Logs"

echo "Installing AI Employee cron jobs…"

# Build crontab block (append-safe — checks for existing entries first)
CRON_BLOCK="
# ── AI Employee — Platinum Tier ───────────────────────────────────────────────

# Vault sync: pull every 2 minutes (cloud stays current)
*/2 * * * * $PY $PROJ/scripts/orchestrator.py --cloud --once >> $LOG/cron_cloud.log 2>&1

# Approval workflow: scan for decisions every 60 seconds
* * * * * $PY $PROJ/scripts/approval_workflow.py --scan >> $LOG/cron_approval.log 2>&1

# Watchdog: health check every 5 minutes
*/5 * * * * $PY $PROJ/scripts/watchdog.py --once >> $LOG/cron_watchdog.log 2>&1

# Vault git-pull every 2 minutes
*/2 * * * * bash $PROJ/scripts/sync.sh pull >> $LOG/vault_sync.log 2>&1

# CEO Briefing: every Sunday at 07:00 UTC
0 7 * * 0 $PY $PROJ/scripts/ceo_briefing.py >> $LOG/cron_briefing.log 2>&1

# ── end AI Employee ──────────────────────────────────────────────────────────
"

# Write to a temp file, merge with existing crontab, install
TMPFILE=$(mktemp)
crontab -l 2>/dev/null | grep -v "AI Employee" | grep -v "ceo_briefing\|approval_workflow\|watchdog\|sync\.sh\|orchestrator" > "$TMPFILE" || true
echo "$CRON_BLOCK" >> "$TMPFILE"
crontab "$TMPFILE"
rm "$TMPFILE"

echo "Cron jobs installed. Current crontab:"
echo "────────────────────────────────────────"
crontab -l
echo "────────────────────────────────────────"
echo ""
echo "To view CEO briefing logs:  tail -f $LOG/cron_briefing.log"
echo "To run briefing now:        $PY $PROJ/scripts/ceo_briefing.py --force"
echo "To preview:                 $PY $PROJ/scripts/ceo_briefing.py --preview"
