from flask import Blueprint, jsonify
from mock.mock_data import MOCK_KILL_FEED

mock_zkill_bp = Blueprint("mock_zkill", __name__)


@mock_zkill_bp.route("/api/zkill/feed")
def api_zkill_feed():
    return jsonify(MOCK_KILL_FEED)


@mock_zkill_bp.route("/api/zkill/<int:system_id>")
def api_zkill(system_id):
    return jsonify([])
