#!/usr/bin/env bash
# sync_local.sh — Run this on your LOCAL Windows/Mac machine after approvals.
# Wraps git pull-then-push so Local never overwrites Cloud work.
set -euo pipefail

# Edit this to match your local path
VAULT_DIR="$HOME/Desktop/ai_employee/platinum/AI_Employee_Vault"

cd "$VAULT_DIR"

echo "[sync_local] Pulling latest from cloud first..."
git fetch origin main
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
  if git merge-base --is-ancestor "$LOCAL" "$REMOTE"; then
    git merge --ff-only origin/main
    echo "[sync_local] Pulled $(git rev-parse --short HEAD) OK."
  else
    echo "ERROR: Histories diverged. Resolve manually:"
    echo "  git log --oneline HEAD...origin/main"
    echo "  git mergetool"
    exit 1
  fi
fi

echo "[sync_local] Staging your local changes..."
git add -- '*.md' '*.json' '*.yaml' '*.yml'

if git diff --cached --quiet; then
  echo "[sync_local] Nothing new to push."
  exit 0
fi

git commit -m "vault: local sync $(date '+%Y-%m-%d %H:%M')" --no-verify
git push origin main
echo "[sync_local] Pushed OK → $(git rev-parse --short HEAD)."
