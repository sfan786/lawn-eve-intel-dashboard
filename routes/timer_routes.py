from flask import Blueprint, jsonify, request
from config import TIMER_PASSWORD
import db

timer_bp = Blueprint("timer", __name__)


@timer_bp.route("/api/timers", methods=["GET"])
def api_get_timers():
    timers = db.get_active_timers()
    return jsonify(timers)


@timer_bp.route("/api/auth/check", methods=["POST"])
def api_check_auth():
    data = request.json or {}
    password = data.get("password")
    if password == TIMER_PASSWORD:
        return jsonify({"status": "ok"})
    return jsonify({"error": "Invalid password"}), 401


@timer_bp.route("/api/timers", methods=["POST"])
def api_add_timer():
    auth_header = request.headers.get("X-Timer-Auth")
    if auth_header != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    if not all(k in data for k in ("system_name", "structure_type", "owner", "event_type", "timestamp")):
        return jsonify({"error": "Missing fields"}), 400

    db.add_timer(
        data["system_name"],
        data["structure_type"],
        data["owner"],
        data["event_type"],
        data["timestamp"],
        data.get("notes"),
    )
    return jsonify({"status": "ok"})


@timer_bp.route("/api/timers/<int:timer_id>", methods=["DELETE"])
def api_delete_timer(timer_id):
    auth_header = request.headers.get("X-Timer-Auth")
    if auth_header != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    db.delete_timer(timer_id)
    return jsonify({"status": "ok"})
