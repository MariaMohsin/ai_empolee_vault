#!/usr/bin/env bash
# sync.sh — Git-based vault sync for AI Employee
# Usage:
#   ./sync.sh pull    → Cloud agent: pull latest before running tasks
#   ./sync.sh push    → Local machine: push after approvals/edits
#   ./sync.sh status  → Show pending changes
set -euo pipefail

VAULT_DIR="/opt/ai_employee/platinum/AI_Employee_Vault"
LOCK_FILE="/tmp/vault_sync.lock"
LOG_FILE="/opt/ai_employee/platinum/Logs/vault_sync.log"
MODE="${1:-pull}"

# ── helpers ───────────────────────────────────────────────────────────────────

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

acquire_lock() {
  if [ -f "$LOCK_FILE" ]; then
    log "WARN  Another sync is running (lock exists). Skipping."
    exit 0
  fi
  echo $$ > "$LOCK_FILE"
  trap 'rm -f "$LOCK_FILE"' EXIT
}

# ── pull (Cloud agent) ────────────────────────────────────────────────────────

do_pull() {
  log "INFO  [pull] Fetching vault from origin..."
  cd "$VAULT_DIR"

  # Stash any local drift (safety net — should not happen on cloud)
  if ! git diff --quiet || ! git diff --cached --quiet; then
    log "WARN  Uncommitted changes found on cloud — stashing before pull."
    git stash push -m "auto-stash-$(date +%s)"
  fi

  git fetch origin main --quiet
  LOCAL=$(git rev-parse HEAD)
  REMOTE=$(git rev-parse origin/main)

  if [ "$LOCAL" = "$REMOTE" ]; then
    log "INFO  Vault already up to date."
    exit 0
  fi

  # Fast-forward only — never auto-merge on cloud
  if git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
    git merge --ff-only origin/main
    log "INFO  Pull OK. Now at $(git rev-parse --short HEAD)."
  else
    log "ERROR Diverged history detected. Manual intervention needed."
    log "      Run: git log --oneline HEAD...origin/main"
    exit 1
  fi
}

# ── push (Local machine) ──────────────────────────────────────────────────────

do_push() {
  cd "$VAULT_DIR"

  if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    log "INFO  Nothing to push — vault is clean."
    exit 0
  fi

  log "INFO  [push] Staging vault changes..."

  # Stage only safe files (markdown + state)
  git add \
    "Inbox/"        \
    "Needs_Action/" \
    "Pending_Approval/" \
    "In_Progress/"  \
    "Done/"         \
    "Accounting/"   \
    "Reports/"      \
    "Plans/"        \
    "Errors/"       \
    "Personal/"     \
    -- '*.md' '*.json' '*.yaml' '*.yml' 2>/dev/null || true

  STAGED=$(git diff --cached --name-only | wc -l)
  if [ "$STAGED" -eq 0 ]; then
    log "INFO  No safe files to stage."
    exit 0
  fi

  git commit -m "vault: sync $(date '+%Y-%m-%d %H:%M') [auto]" --no-verify
  git push origin main
  log "INFO  Push OK. $(git rev-parse --short HEAD) → origin/main."
}

# ── status ────────────────────────────────────────────────────────────────────

do_status() {
  cd "$VAULT_DIR"
  echo "=== Local changes ==="
  git status --short
  echo ""
  echo "=== Commits ahead of origin ==="
  git log --oneline origin/main..HEAD || echo "(none)"
  echo ""
  echo "=== Commits behind origin ==="
  git log --oneline HEAD..origin/main || echo "(none)"
}

# ── dispatch ──────────────────────────────────────────────────────────────────

mkdir -p "$(dirname "$LOG_FILE")"
acquire_lock

case "$MODE" in
  pull)   do_pull   ;;
  push)   do_push   ;;
  status) do_status ;;
  *) echo "Usage: $0 [pull|push|status]"; exit 1 ;;
esac
