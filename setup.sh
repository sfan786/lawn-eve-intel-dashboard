#!/bin/bash
# First-time setup: Python venv + pip + npm install
# Bash equivalent of setup.fish (use this on bash-default systems / most VPS hosts).
#
# Safe to re-run, and safe in a git worktree: .venv/ and node_modules/ are
# gitignored, so `git worktree add` produces a checkout with neither. Run this
# in the worktree to make it testable. Pass --dev to also install the test and
# lint tooling from requirements-dev.txt.

set -e

INSTALL_DEV=0
for arg in "$@"; do
    case "$arg" in
        --dev) INSTALL_DEV=1 ;;
        *) echo "[!] Unknown option: $arg (expected --dev)"; exit 1 ;;
    esac
done

cd "$(dirname "$0")"

echo "[*] LAWN Intel Dashboard — Setup"
if [ -f .git ]; then
    echo "[*] Detected a git worktree — setting up its own venv/node_modules"
fi
echo ""

# Python venv
if [ ! -d ".venv" ]; then
    echo "[*] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[*] Python venv already exists, reusing"
fi

echo "[*] Installing Python dependencies..."
.venv/bin/pip install -q -r requirements.txt
if [ "$INSTALL_DEV" -eq 1 ]; then
    echo "[*] Installing dev dependencies (pytest, ruff)..."
    .venv/bin/pip install -q -r requirements-dev.txt
fi
echo "    done"

# Node deps
if [ -d "frontend" ]; then
    if [ -d "frontend/node_modules" ]; then
        echo "[*] Node dependencies already present, reusing"
    else
        echo "[*] Installing Node dependencies..."
        (cd frontend && npm install --silent)
    fi
    echo "    done"
else
    echo "[!] frontend/ not found — skipping npm install"
fi

echo ""
echo "[*] Setup complete. Run options:"
echo "    ./run_dev.sh           live mode  (Flask :5000 + Vite :3000)"
echo "    ./run_dev.sh demo      demo mode  (Flask :5001 + Vite :3000)"
echo "    cd frontend && npm run build   build for production"
if [ "$INSTALL_DEV" -eq 1 ]; then
    echo ""
    echo "[*] Checks:"
    echo "    .venv/bin/pytest tests/ -q     backend tests"
    echo "    .venv/bin/ruff check .         backend lint"
    echo "    cd frontend && npm test        frontend tests"
    echo "    cd frontend && npm run lint    frontend lint"
fi
