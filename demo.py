"""
Demo mode - Run the dashboard with mock data for UI testing.
Usage: python demo.py
       FLASK_PORT=5001 python demo.py   # run alongside live mode
"""

import os
from flask import Flask
from mock.mock_config_routes import mock_config_bp
from mock.mock_sov_routes import mock_sov_bp
from mock.mock_activity_routes import mock_activity_bp
from mock.mock_zkill_routes import mock_zkill_bp
from mock.mock_history_routes import mock_history_bp
from mock.mock_intel_routes import mock_intel_bp
from mock.mock_timer_routes import mock_timer_bp
from routes.static_routes import static_bp
from mock.mock_data import MOCK_CONFIG


def create_demo_app():
    app = Flask(__name__)
    for bp in [
        mock_config_bp, mock_sov_bp, mock_activity_bp, mock_zkill_bp,
        mock_history_bp, mock_intel_bp, mock_timer_bp, static_bp,
    ]:
        app.register_blueprint(bp)
    return app


app = create_demo_app()

if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", 5000))
    tke = sum(len(c["systems"]) for c in MOCK_CONFIG["constellations"].values())
    neighbors = len(MOCK_CONFIG["neighbor_systems"])
    print("\n[*] \u2550\u2550\u2550 DEMO MODE \u2550\u2550\u2550")
    print("[*] Running with mock data \u2014 no ESI connection needed")
    print(f"[*] {len(MOCK_CONFIG['constellations'])} constellations, {tke} TKE + {neighbors} neighbors")
    print(f"[*] Open http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
