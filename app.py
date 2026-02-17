"""
EVE Intel Dashboard - Flask Backend
Get Off My Lawn [LAWN] — Kalevala Expanse

Usage:
    ./run_dev.fish
    OR
    source .venv/bin/activate.fish
    python app.py
    Open http://localhost:5000
"""

from flask import Flask
from config import FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from routes.system_state import state, resolve_all_systems
from routes.config_routes import config_bp
from routes.sov_routes import sov_bp
from routes.activity_routes import activity_bp
from routes.zkill_routes import zkill_bp
from routes.history_routes import history_bp
from routes.intel_routes import intel_bp
from routes.timer_routes import timer_bp
from routes.static_routes import static_bp
import db


def create_app():
    app = Flask(__name__)
    for bp in [config_bp, sov_bp, activity_bp, zkill_bp, history_bp, intel_bp, timer_bp, static_bp]:
        app.register_blueprint(bp)
    return app


# Load all systems at module import time (works with gunicorn and Flask dev server).
# In debug mode, Werkzeug's reloader will cause this to run twice — but with
# parallel fetches the second load hits the ESI cache and is near-instant.
resolve_all_systems(state)
db.init()
app = create_app()

if __name__ == "__main__":
    lawn_names = [c["name"] for c in state.constellation_data.values() if c.get("is_lawn")]
    print(f"\n[*] Dashboard starting at http://localhost:{FLASK_PORT}")
    print(f"[*] LAWN Intel Dashboard - Kalevala Expanse")
    print(f"[*] LAWN constellations: {', '.join(lawn_names)}")
    print(f"[*] Monitoring {len(state.all_monitored_ids)} systems total\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
