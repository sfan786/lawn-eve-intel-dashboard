#!/bin/bash
# First-time setup: Python venv + pip + npm install
# Bash equivalent of setup.fish (use this on bash-default systems / most VPS hosts).

set -e

echo "[*] LAWN Intel Dashboard — Setup"
echo ""

# Python venv
if [ ! -d ".venv" ]; then
    echo "[*] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[*] Python venv already exists, skipping"
fi

echo "[*] Installing Python dependencies..."
.venv/bin/pip install -q -r requirements.txt
echo "    done"

# Node deps
if [ -d "frontend" ]; then
    echo "[*] Installing Node dependencies..."
    (cd frontend && npm install --silent)
    echo "    done"
else
    echo "[!] frontend/ not found — skipping npm install"
fi

echo ""
echo "[*] Setup complete. Run options:"
echo "    ./run_dev.sh           live mode  (Flask :5000 + Vite :3000)"
echo "    ./run_dev.sh demo      demo mode  (Flask :5001 + Vite :3000)"
echo "    cd frontend && npm run build   build for production"
