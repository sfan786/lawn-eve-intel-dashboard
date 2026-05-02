from flask import Blueprint, jsonify, request

mock_annotation_bp = Blueprint("mock_annotation", __name__)

_MOCK_ANNOTATIONS = {
    "XTJ-5Q": {"note": "cloaky camper active since downtime", "updated_at": "2026-04-29T10:00:00Z"},
    "N-JK02": {"note": "gate camp reported in L-GY1B", "updated_at": "2026-04-29T11:30:00Z"},
    "UDVW-O": {"note": "JB to LS-JEP active (LAWN-NORTH)", "updated_at": "2026-04-29T08:00:00Z"},
}


@mock_annotation_bp.route("/api/annotations", methods=["GET"])
def api_get_annotations():
    return jsonify(dict(_MOCK_ANNOTATIONS))


@mock_annotation_bp.route("/api/annotations", methods=["POST"])
def api_upsert_annotation():
    data = request.json or {}
    system_name = data.get("system_name", "").strip()
    note = data.get("note", "")
    if not system_name:
        return jsonify({"error": "system_name required"}), 400
    if not note or not note.strip():
        _MOCK_ANNOTATIONS.pop(system_name, None)
    else:
        _MOCK_ANNOTATIONS[system_name] = {"note": note.strip(), "updated_at": "2026-04-29T12:00:00Z"}
    return jsonify({"status": "ok"})


@mock_annotation_bp.route("/api/annotations/<path:system_name>", methods=["DELETE"])
def api_delete_annotation(system_name):
    _MOCK_ANNOTATIONS.pop(system_name, None)
    return jsonify({"status": "ok"})
