#!/usr/bin/env bash
set -euo pipefail

PROJ_DIR="/opt/ai_employee/platinum"
VENV_DIR="/opt/ai_employee/venv"
LOG_DIR="$PROJ_DIR/Logs"

echo "[start.sh] Activating venv..."
source "$VENV_DIR/bin/activate"

echo "[start.sh] Loading .env..."
set -a
source "$PROJ_DIR/.env"
set +a

echo "[start.sh] Creating log directory..."
mkdir -p "$LOG_DIR"

echo "[start.sh] Starting PM2 processes..."
cd "$PROJ_DIR"
pm2 start ecosystem.config.js

echo "[start.sh] Saving PM2 process list..."
pm2 save

echo "[start.sh] All processes started."
pm2 list
