"""
EVE Intel Dashboard - Flask Backend

Active deployment is selected by the DEPLOYMENT env var (default: lawn_perrigen).
See deployments/ for the available deployment modules.

Usage:
    ./run_dev.fish
    OR
    source .venv/bin/activate.fish
    python app.py
    Open http://localhost:5000
"""

from flask import Flask
from config import ALLIANCE, REGION, FLASK_HOST, FLASK_PORT, FLASK_DEBUG
from routes.system_state import state, resolve_all_systems
from routes.config_routes import config_bp
from routes.sov_routes import sov_bp
from routes.activity_routes import activity_bp
from routes.zkill_routes import zkill_bp
from routes.history_routes import history_bp
from routes.intel_routes import intel_bp
from routes.hostile_routes import hostile_bp
from routes.timer_routes import timer_bp
from routes.annotation_routes import annotation_bp
from routes.jb_routes import jb_bp
from routes.entosis_routes import entosis_bp
from routes.static_routes import static_bp
import db


def create_app():
    app = Flask(__name__)
    for bp in [config_bp, sov_bp, activity_bp, zkill_bp, history_bp, intel_bp, hostile_bp, timer_bp, annotation_bp, jb_bp, entosis_bp, static_bp]:
        app.register_blueprint(bp)
    return app


# Load all systems at module import time (works with gunicorn and Flask dev server).
# In debug mode, Werkzeug's reloader will cause this to run twice — but with
# parallel fetches the second load hits the ESI cache and is near-instant.
resolve_all_systems(state)
db.init()
app = create_app()

if __name__ == "__main__":
    primary_names = [c["name"] for c in state.constellation_data.values() if c.get("is_primary")]
    print(f"\n[*] Dashboard starting at http://localhost:{FLASK_PORT}")
    print(f"[*] {ALLIANCE['display_name']} Intel Dashboard - {REGION['name']}")
    print(f"[*] Primary constellations: {', '.join(primary_names)}")
    print(f"[*] Monitoring {len(state.all_monitored_ids)} systems total\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
