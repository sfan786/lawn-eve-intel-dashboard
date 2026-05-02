from flask import Blueprint, jsonify, request
from config import TIMER_PASSWORD

mock_jb_bp = Blueprint("mock_jumpbridge", __name__)

_MOCK_JBS = [
    {"id": 1, "system_a": "IUU3-L", "system_b": "N-JK02", "label": "LAWN-SOUTH", "created_at": "2026-04-29T08:00:00Z"},
    {"id": 2, "system_a": "FB5U-I", "system_b": "UDVW-O", "label": "LAWN-NORTH", "created_at": "2026-04-29T09:00:00Z"},
]
_next_id = 3


@mock_jb_bp.route("/api/jumpbridges", methods=["GET"])
def api_get_jumpbridges():
    return jsonify(list(_MOCK_JBS))


@mock_jb_bp.route("/api/jumpbridges", methods=["POST"])
def api_add_jumpbridge():
    global _next_id
    auth_header = request.headers.get("X-Timer-Auth")
    if auth_header != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    data = request.json or {}
    a, b = sorted([data.get("system_a", "").strip(), data.get("system_b", "").strip()])
    new_jb = {"id": _next_id, "system_a": a, "system_b": b, "label": data.get("label"), "created_at": "2026-04-29T12:00:00Z"}
    _MOCK_JBS.append(new_jb)
    _next_id += 1
    return jsonify({"status": "ok", "id": new_jb["id"]})


@mock_jb_bp.route("/api/jumpbridges/<int:bridge_id>", methods=["DELETE"])
def api_delete_jumpbridge(bridge_id):
    auth_header = request.headers.get("X-Timer-Auth")
    if auth_header != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401
    for i, jb in enumerate(_MOCK_JBS):
        if jb["id"] == bridge_id:
            _MOCK_JBS.pop(i)
            break
    return jsonify({"status": "ok"})
