#!/usr/bin/env fish
# First-time setup: Python venv + pip + npm install

echo "[*] LAWN Intel Dashboard — Setup"
echo ""

# Python venv
if not test -d ".venv"
    echo "[*] Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "[*] Python venv already exists, skipping"
end

echo "[*] Installing Python dependencies..."
.venv/bin/pip install -q -r requirements.txt
echo "    done"

# Node deps
if test -d "frontend"
    echo "[*] Installing Node dependencies..."
    cd frontend && npm install --silent
    cd ..
    echo "    done"
else
    echo "[!] frontend/ not found — skipping npm install"
end

echo ""
echo "[*] Setup complete. Run options:"
echo "    ./run_dev.fish           live mode  (Flask :5000 + Vite :3000)"
echo "    ./run_dev.fish demo      demo mode  (Flask :5001 + Vite :3000)"
echo "    cd frontend && npm run build   build for production"
