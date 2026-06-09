from flask import Blueprint, jsonify, request
from config import TIMER_PASSWORD

mock_entosis_bp = Blueprint("mock_entosis", __name__)

_MOCK_NODES = []
_next_id = 1

VALID_STATUSES = {"unclaimed", "running", "contested", "captured", "lost"}


@mock_entosis_bp.route("/api/entosis/nodes", methods=["GET"])
def api_get_nodes():
    return jsonify(list(_MOCK_NODES))


@mock_entosis_bp.route("/api/entosis/nodes", methods=["POST"])
def api_add_node():
    global _next_id
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400
    system_name = data.get("system_name")
    if not isinstance(system_name, str) or not system_name.strip():
        return jsonify({"error": "system_name must be a non-empty string"}), 400
    label = data.get("label")
    node = {
        "id": _next_id,
        "system_name": system_name.strip(),
        "label": label.strip() if isinstance(label, str) and label.strip() else None,
        "status": "unclaimed",
        "claimed_by": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    _MOCK_NODES.append(node)
    _next_id += 1
    return jsonify({"id": node["id"]}), 201


@mock_entosis_bp.route("/api/entosis/nodes/<int:node_id>", methods=["PATCH"])
def api_update_node(node_id):
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400
    status = data.get("status")
    claimed_by = data.get("claimed_by")
    if status is not None and status not in VALID_STATUSES:
        return jsonify({"error": "Invalid status"}), 400
    for node in _MOCK_NODES:
        if node["id"] == node_id:
            if status is not None:
                node["status"] = status
            if claimed_by is not None:
                node["claimed_by"] = claimed_by or None
            break
    return jsonify({"status": "ok"})


@mock_entosis_bp.route("/api/entosis/nodes/<int:node_id>", methods=["DELETE"])
def api_delete_node(node_id):
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    for i, node in enumerate(_MOCK_NODES):
        if node["id"] == node_id:
            _MOCK_NODES.pop(i)
            break
    return jsonify({"status": "ok"})


@mock_entosis_bp.route("/api/entosis/nodes", methods=["DELETE"])
def api_clear_nodes():
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    _MOCK_NODES.clear()
    return jsonify({"status": "ok"})
