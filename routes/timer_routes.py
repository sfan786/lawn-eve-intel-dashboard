import hmac
from flask import Blueprint, jsonify, request
from config import TIMER_PASSWORD
from routes.auth_sso import require_write_auth
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
    if isinstance(password, str) and TIMER_PASSWORD and hmac.compare_digest(password, TIMER_PASSWORD):
        return jsonify({"status": "ok"})
    return jsonify({"error": "Invalid password"}), 401


@timer_bp.route("/api/timers", methods=["POST"])
@require_write_auth
def api_add_timer():
    data = request.json or {}
    required = ("system_name", "structure_type", "owner", "event_type", "timestamp")
    if not all(isinstance(data.get(k), str) and data[k].strip() for k in required):
        return jsonify({"error": "Missing fields"}), 400
    notes = data.get("notes")
    if notes is not None and not isinstance(notes, str):
        return jsonify({"error": "notes must be a string"}), 400

    db.add_timer(
        data["system_name"].strip()[:64],
        data["structure_type"].strip()[:64],
        data["owner"].strip()[:64],
        data["event_type"].strip()[:64],
        data["timestamp"].strip()[:64],
        notes[:500] if notes else None,
    )
    return jsonify({"status": "ok"})


@timer_bp.route("/api/timers/<int:timer_id>", methods=["DELETE"])
@require_write_auth
def api_delete_timer(timer_id):
    db.delete_timer(timer_id)
    return jsonify({"status": "ok"})
