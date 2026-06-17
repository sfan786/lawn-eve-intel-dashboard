#!/bin/bash
# Local dev launcher (Flask + Vite together).
# Bash equivalent of run_dev.fish (use this on bash-default systems / most VPS hosts).
#   ./run_dev.sh        live mode (ESI API :5000 + Vite :3000)
#   ./run_dev.sh demo   demo mode (mock API :5001 + Vite :3000)

set -e

# Kill any existing Flask/Vite instances
echo "[*] Killing existing Flask and Vite instances..."
pkill -f "python app.py" 2>/dev/null || true
pkill -f "python demo.py" 2>/dev/null || true
# Only free our own Vite port (3000) rather than pkill-ing every vite on the box.
lsof -ti:3000 2>/dev/null | xargs -r kill 2>/dev/null || true
sleep 0.5

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Parse mode argument: live (default) or demo
mode="live"
if [ "$1" = "demo" ]; then
    mode="demo"
fi

# Kill Flask when this script exits (Vite quits or Ctrl-C)
flask_pid=""
trap '[ -n "$flask_pid" ] && kill "$flask_pid" 2>/dev/null' EXIT

if [ "$mode" = "demo" ]; then
    # Demo mode: Flask mock API on :5001 + Vite dev server on :3000
    echo "[*] Starting DEMO mode (mock API :5001 + Vite :3000)..."
    export FLASK_PORT=5001
    export FLASK_DEBUG=true
    python demo.py &
    flask_pid=$!
    echo "[*] Demo Flask PID: $flask_pid"
    sleep 1
    if ! kill -0 "$flask_pid" 2>/dev/null; then
        echo "[-] Demo Flask failed to start — see the error above."
        exit 1
    fi

    if [ -d "frontend" ]; then
        (cd frontend && npm run dev:demo)
    else
        echo "[*] No frontend/ yet — serving legacy static/index.html from Flask"
        wait $flask_pid
    fi
else
    # Live mode: Flask on :5000 + Vite dev server on :3000
    echo "[*] Starting LIVE mode (ESI API :5000 + Vite :3000)..."
    export FLASK_DEBUG=true
    python app.py &
    flask_pid=$!
    echo "[*] Live Flask PID: $flask_pid"
    sleep 1
    if ! kill -0 "$flask_pid" 2>/dev/null; then
        echo "[-] Live Flask failed to start — see the error above."
        exit 1
    fi

    if [ -d "frontend" ]; then
        (cd frontend && npm run dev)
    else
        echo "[*] No frontend/ yet — serving legacy static/index.html from Flask"
        wait $flask_pid
    fi
fi
