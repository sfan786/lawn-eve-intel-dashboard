from flask import Blueprint, jsonify
import time

mock_ai_bp = Blueprint("mock_ai", __name__)

@mock_ai_bp.route("/api/ai/threat_summary", methods=["POST"])
def api_threat_summary_mock():
    # Simulate a brief delay to show loading state
    time.sleep(1)
    return jsonify({
        "summary": "MOCK AI SUMMARY: Multiple high-threat capital signatures detected alongside a cruiser support wing. Proceed with extreme caution and prepare for immediate escalation."
    })
