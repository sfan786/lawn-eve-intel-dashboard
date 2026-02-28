from flask import Blueprint, jsonify
from mock.mock_data import MOCK_CONFIG
from config import PI_DATA

mock_config_bp = Blueprint("mock_config", __name__)


@mock_config_bp.route("/api/config")
def api_config():
    return jsonify(MOCK_CONFIG)


@mock_config_bp.route("/api/pi_data")
def api_pi_data():
    return jsonify({"pi_data": PI_DATA})


@mock_config_bp.route("/api/status")
def api_status():
    tke = sum(len(c["systems"]) for c in MOCK_CONFIG["constellations"].values())
    lawn = sum(len(c["systems"]) for c in MOCK_CONFIG["constellations"].values() if c.get("is_lawn"))
    neighbor = len(MOCK_CONFIG["neighbor_systems"])
    return jsonify({
        "status": "demo_mode",
        "constellations_monitored": len(MOCK_CONFIG["constellations"]),
        "systems_monitored": tke + neighbor,
        "lawn_systems": lawn,
        "tke_systems": tke,
        "neighbor_systems": neighbor,
    })
