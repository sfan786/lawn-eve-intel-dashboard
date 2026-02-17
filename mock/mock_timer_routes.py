from flask import Blueprint, jsonify, request
from config import TIMER_PASSWORD

mock_timer_bp = Blueprint("mock_timer", __name__)


@mock_timer_bp.route("/api/timers", methods=["GET"])
def api_get_timers():
    return jsonify([])


@mock_timer_bp.route("/api/auth/check", methods=["POST"])
def api_check_auth():
    data = request.json or {}
    if data.get("password") == TIMER_PASSWORD:
        return jsonify({"status": "ok"})
    return jsonify({"error": "Invalid password"}), 401


@mock_timer_bp.route("/api/timers", methods=["POST"])
def api_add_timer():
    return jsonify({"status": "ok"})


@mock_timer_bp.route("/api/timers/<int:timer_id>", methods=["DELETE"])
def api_delete_timer(timer_id):
    return jsonify({"status": "ok"})
