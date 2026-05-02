from flask import Blueprint, jsonify, request
import db

annotation_bp = Blueprint("annotation", __name__)


@annotation_bp.route("/api/annotations", methods=["GET"])
def api_get_annotations():
    return jsonify(db.get_all_annotations())


@annotation_bp.route("/api/annotations", methods=["POST"])
def api_upsert_annotation():
    data = request.json or {}
    system_name = data.get("system_name", "").strip()
    note = data.get("note", "")
    if not system_name:
        return jsonify({"error": "system_name required"}), 400
    db.upsert_annotation(system_name, note)
    return jsonify({"status": "ok"})


@annotation_bp.route("/api/annotations/<path:system_name>", methods=["DELETE"])
def api_delete_annotation(system_name):
    db.delete_annotation(system_name)
    return jsonify({"status": "ok"})
