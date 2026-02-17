from flask import Blueprint, jsonify, request
import db

history_bp = Blueprint("history", __name__)


@history_bp.route("/api/history/adm")
def api_history_adm():
    hours = request.args.get("hours", 168, type=int)
    hours = max(1, min(hours, 720))
    history = db.get_adm_history(hours=hours)
    return jsonify(history)


@history_bp.route("/api/history/activity/heatmap")
def api_activity_heatmap():
    days = request.args.get("days", 7, type=int)
    days = max(1, min(days, 30))
    heatmap = db.get_activity_heatmap_data(hours=days * 24)
    return jsonify(heatmap)
