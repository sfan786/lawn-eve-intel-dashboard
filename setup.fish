#!/usr/bin/env fish
# First-time setup: Python venv + pip + npm install
#
# Safe to re-run, and safe in a git worktree: .venv/ and node_modules/ are
# gitignored, so `git worktree add` produces a checkout with neither. Run this
# in the worktree to make it testable. Pass --dev to also install the test and
# lint tooling from requirements-dev.txt.

set -l install_dev 0
for arg in $argv
    switch $arg
        case --dev
            set install_dev 1
        case '*'
            echo "[!] Unknown option: $arg (expected --dev)"
            exit 1
    end
end

cd (dirname (status --current-filename))

echo "[*] LAWN Intel Dashboard — Setup"
if test -f .git
    echo "[*] Detected a git worktree — setting up its own venv/node_modules"
end
echo ""

# Python venv
if not test -d ".venv"
    echo "[*] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[*] Python venv already exists, reusing"
end

echo "[*] Installing Python dependencies..."
.venv/bin/pip install -q -r requirements.txt
if test $install_dev -eq 1
    echo "[*] Installing dev dependencies (pytest, ruff)..."
    .venv/bin/pip install -q -r requirements-dev.txt
end
echo "    done"

# Node deps
if test -d "frontend"
    if test -d "frontend/node_modules"
        echo "[*] Node dependencies already present, reusing"
    else
        echo "[*] Installing Node dependencies..."
        cd frontend; and npm install --silent
        cd ..
    end
    echo "    done"
else
    echo "[!] frontend/ not found — skipping npm install"
end

echo ""
echo "[*] Setup complete. Run options:"
echo "    ./run_dev.fish           live mode  (Flask :5000 + Vite :3000)"
echo "    ./run_dev.fish demo      demo mode  (Flask :5001 + Vite :3000)"
echo "    cd frontend && npm run build   build for production"
if test $install_dev -eq 1
    echo ""
    echo "[*] Checks:"
    echo "    .venv/bin/pytest tests/ -q     backend tests"
    echo "    .venv/bin/ruff check .         backend lint"
    echo "    cd frontend && npm test        frontend tests"
    echo "    cd frontend && npm run lint    frontend lint"
end
