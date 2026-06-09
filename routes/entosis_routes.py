from flask import Blueprint, jsonify, request
from config import TIMER_PASSWORD
import db

entosis_bp = Blueprint("entosis", __name__)

VALID_STATUSES = {"unclaimed", "running", "contested", "captured", "lost"}


@entosis_bp.route("/api/entosis/nodes", methods=["GET"])
def api_get_nodes():
    return jsonify(db.get_entosis_nodes())


@entosis_bp.route("/api/entosis/nodes", methods=["POST"])
def api_add_node():
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    system_name = (data.get("system_name") or "").strip()
    if not system_name:
        return jsonify({"error": "system_name required"}), 400
    node_id = db.add_entosis_node(system_name, data.get("label"))
    return jsonify({"id": node_id}), 201


@entosis_bp.route("/api/entosis/nodes/<int:node_id>", methods=["PATCH"])
def api_update_node(node_id):
    data = request.json or {}
    status = data.get("status")
    claimed_by = data.get("claimed_by")  # None = don't touch, "" = unclaim

    if status is not None and status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}), 400

    db.update_entosis_node(node_id, status=status, claimed_by=claimed_by)
    return jsonify({"status": "ok"})


@entosis_bp.route("/api/entosis/nodes/<int:node_id>", methods=["DELETE"])
def api_delete_node(node_id):
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    db.delete_entosis_node(node_id)
    return jsonify({"status": "ok"})


@entosis_bp.route("/api/entosis/nodes", methods=["DELETE"])
def api_clear_nodes():
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    db.clear_entosis_nodes()
    return jsonify({"status": "ok"})
