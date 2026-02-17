from flask import Blueprint, jsonify
from mock.mock_data import generate_mock_adm_history

mock_history_bp = Blueprint("mock_history", __name__)


@mock_history_bp.route("/api/history/adm")
def api_history_adm():
    return jsonify(generate_mock_adm_history())


@mock_history_bp.route("/api/history/activity/heatmap")
def api_activity_heatmap():
    # Return empty heatmap in demo mode (no historical data)
    return jsonify({})
