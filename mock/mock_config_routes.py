from flask import Blueprint, jsonify
from mock.mock_data import MOCK_CONFIG
from config import PI_DATA, ALLIANCE, REGION, DEPLOYMENT_ID

mock_config_bp = Blueprint("mock_config", __name__)


@mock_config_bp.route("/api/config")
def api_config():
    return jsonify(MOCK_CONFIG)


@mock_config_bp.route("/api/pi_data")
def api_pi_data():
    return jsonify({"pi_data": PI_DATA})


@mock_config_bp.route("/api/status")
def api_status():
    region_systems = sum(len(c["systems"]) for c in MOCK_CONFIG["constellations"].values())
    primary_systems = sum(
        len(c["systems"]) for c in MOCK_CONFIG["constellations"].values()
        if c.get("is_primary") or c.get("is_lawn")
    )
    neighbor_systems = len(MOCK_CONFIG["neighbor_systems"])
    return jsonify({
        "status": "demo_mode",
        "deployment_id": DEPLOYMENT_ID + "-demo",
        "alliance": ALLIANCE,
        "region": REGION,
        "constellations_monitored": len(MOCK_CONFIG["constellations"]),
        "systems_monitored": region_systems + neighbor_systems,
        "primary_systems": primary_systems,
        "region_systems": region_systems,
        "neighbor_systems": neighbor_systems,
    })
