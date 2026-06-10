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
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400
    system_name = data.get("system_name")
    if not isinstance(system_name, str) or not system_name.strip():
        return jsonify({"error": "system_name must be a non-empty string"}), 400
    system_name = system_name.strip()[:64]
    label = data.get("label")
    if label is not None and not isinstance(label, str):
        return jsonify({"error": "label must be a string"}), 400
    label = label.strip()[:80] if label else None
    node_id = db.add_entosis_node(system_name, label)
    return jsonify({"id": node_id}), 201


@entosis_bp.route("/api/entosis/nodes/<int:node_id>", methods=["PATCH"])
def api_update_node(node_id):
    # Intentionally open (no X-Timer-Auth): any fleet member must be able to
    # claim a node and advance its status without knowing the FC password.
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400
    status = data.get("status")
    claimed_by = data.get("claimed_by")  # None = don't touch, "" = unclaim

    if status is not None and not isinstance(status, str):
        return jsonify({"error": "status must be a string"}), 400
    if claimed_by is not None and not isinstance(claimed_by, str):
        return jsonify({"error": "claimed_by must be a string"}), 400
    if status is not None and status not in VALID_STATUSES:
        return jsonify({"error": f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"}), 400
    if claimed_by is not None:
        claimed_by = claimed_by.strip()[:64]

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
