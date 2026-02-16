#!/usr/bin/env fish

if not test -d ".venv"
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate.fish
    pip install -r requirements.txt
else
    source .venv/bin/activate.fish
end

set -x FLASK_APP app.py
set -x FLASK_DEBUG 1

echo "[*] Starting EVE Intel Dashboard..."
flask run --host=0.0.0.0 --port=5000 --reload
