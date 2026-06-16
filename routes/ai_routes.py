import os
from flask import Blueprint, jsonify, request
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

ai_bp = Blueprint("ai", __name__)

def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not genai:
        return None
    return genai.Client(api_key=api_key)

@ai_bp.route("/api/ai/threat_summary", methods=["POST"])
def api_threat_summary():
    client = get_client()
    if not client:
        return jsonify({"error": "AI features are not configured (missing GEMINI_API_KEY or google-genai package)."}), 501
    
    data = request.json
    if not data or "type" not in data or "data" not in data:
        return jsonify({"error": "Invalid payload."}), 400

    scan_type = data["type"]
    scan_data = data["data"]
    
    prompt = ""
    if scan_type == "dscan":
        prompt = f"""
You are a tactical AI assistant for an EVE Online fleet commander. 
Analyze the following D-scan data and provide a concise, military-style threat summary in 1-3 sentences.
Focus on the most dangerous ships, fleet composition, and potential roles (e.g. tackle, logi, capitals).
Do not list every ship. Be direct and analytical.

D-Scan Breakdown:
{scan_data}
"""
    elif scan_type == "local":
        prompt = f"""
You are a tactical AI assistant for an EVE Online fleet commander.
Analyze the following Local chat intel and provide a concise, military-style threat summary in 1-3 sentences.
Focus on the overall threat level, notable hostile alliances, and high-risk pilots or capital pilots.
Do not list every pilot. Be direct and analytical.

Local Chat Breakdown:
{scan_data}
"""
    else:
        return jsonify({"error": "Unknown scan type."}), 400

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.4,
            )
        )
        return jsonify({"summary": response.text})
    except Exception as e:
        return jsonify({"error": f"Failed to generate summary: {str(e)}"}), 500
