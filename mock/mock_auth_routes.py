"""Mock auth routes for demo mode — SSO is never enabled, so the frontend falls
back to its password UI (mock write routes still accept the demo password)."""

from flask import Blueprint, jsonify

mock_auth_bp = Blueprint("mock_auth", __name__)


@mock_auth_bp.route("/api/auth/me", methods=["GET"])
def mock_auth_me():
    return jsonify({
        "sso_enabled": False,
        "logged_in": False,
        "character_name": None,
        "authorized": False,
    })
