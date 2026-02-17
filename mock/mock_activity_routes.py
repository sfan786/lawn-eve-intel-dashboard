from flask import Blueprint, jsonify
from mock.mock_data import MOCK_ACTIVITY

mock_activity_bp = Blueprint("mock_activity", __name__)


@mock_activity_bp.route("/api/activity")
def api_activity():
    return jsonify(MOCK_ACTIVITY)
