from flask import Blueprint, jsonify, request
from config import TIMER_PASSWORD
import db

annotation_bp = Blueprint("annotation", __name__)

MAX_NOTE_LENGTH = 500


@annotation_bp.route("/api/annotations", methods=["GET"])
def api_get_annotations():
    return jsonify(db.get_all_annotations())


@annotation_bp.route("/api/annotations", methods=["POST"])
def api_upsert_annotation():
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    system_name = data.get("system_name", "").strip()
    note = data.get("note", "")
    if not system_name:
        return jsonify({"error": "system_name required"}), 400
    if not isinstance(note, str):
        return jsonify({"error": "note must be a string"}), 400
    db.upsert_annotation(system_name[:64], note[:MAX_NOTE_LENGTH])
    return jsonify({"status": "ok"})


@annotation_bp.route("/api/annotations/<path:system_name>", methods=["DELETE"])
def api_delete_annotation(system_name):
    if request.headers.get("X-Timer-Auth") != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    db.delete_annotation(system_name)
    return jsonify({"status": "ok"})
