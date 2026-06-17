#!/usr/bin/env fish

# Kill any existing Flask/Vite instances
echo "[*] Killing existing Flask and Vite instances..."
pkill -f "python app.py" 2>/dev/null
pkill -f "python demo.py" 2>/dev/null
# Only free our own Vite port (3000) rather than pkill-ing every vite on the box.
lsof -ti:3000 2>/dev/null | xargs -r kill 2>/dev/null
sleep 0.5

if not test -d ".venv"
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate.fish
    pip install -r requirements.txt
else
    source .venv/bin/activate.fish
end

# Parse mode argument: live (default) or demo
set mode "live"
if test (count $argv) -ge 1
    if test $argv[1] = "demo"
        set mode "demo"
    end
end

if test $mode = "demo"
    # Demo mode: Flask mock API on :5001 + Vite dev server on :3000
    echo "[*] Starting DEMO mode (mock API :5001 + Vite :3000)..."
    set -x FLASK_PORT 5001
    set -x FLASK_DEBUG true
    python demo.py &
    set flask_pid $last_pid
    echo "[*] Demo Flask PID: $flask_pid"
    sleep 1
    if not kill -0 $flask_pid 2>/dev/null
        echo "[-] Demo Flask failed to start — see the error above."
        exit 1
    end

    if test -d "frontend"
        cd frontend
        npm run dev:demo
        cd ..
    else
        echo "[*] No frontend/ yet — serving legacy static/index.html from Flask"
        wait $flask_pid
    end

    # Kill Flask when Vite exits
    kill $flask_pid 2>/dev/null
else
    # Live mode: Flask on :5000 + Vite dev server on :3000
    echo "[*] Starting LIVE mode (ESI API :5000 + Vite :3000)..."
    set -x FLASK_DEBUG true
    python app.py &
    set flask_pid $last_pid
    echo "[*] Live Flask PID: $flask_pid"
    sleep 1
    if not kill -0 $flask_pid 2>/dev/null
        echo "[-] Live Flask failed to start — see the error above."
        exit 1
    end

    if test -d "frontend"
        cd frontend
        npm run dev
        cd ..
    else
        echo "[*] No frontend/ yet — serving legacy static/index.html from Flask"
        wait $flask_pid
    end

    # Kill Flask when Vite exits
    kill $flask_pid 2>/dev/null
end
