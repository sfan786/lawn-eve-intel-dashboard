from flask import Blueprint, jsonify, request
from routes.auth_sso import require_write_auth
import db

jb_bp = Blueprint("jumpbridge", __name__)


@jb_bp.route("/api/jumpbridges", methods=["GET"])
def api_get_jumpbridges():
    return jsonify(db.get_jump_bridges())


@jb_bp.route("/api/jumpbridges", methods=["POST"])
@require_write_auth
def api_add_jumpbridge():
    data = request.json or {}
    system_a = data.get("system_a", "").strip()
    system_b = data.get("system_b", "").strip()
    if not system_a or not system_b:
        return jsonify({"error": "system_a and system_b required"}), 400
    if system_a == system_b:
        return jsonify({"error": "system_a and system_b must differ"}), 400

    new_id = db.add_jump_bridge(system_a, system_b, data.get("label"))
    return jsonify({"status": "ok", "id": new_id})


@jb_bp.route("/api/jumpbridges/<int:bridge_id>", methods=["DELETE"])
@require_write_auth
def api_delete_jumpbridge(bridge_id):
    db.delete_jump_bridge(bridge_id)
    return jsonify({"status": "ok"})
