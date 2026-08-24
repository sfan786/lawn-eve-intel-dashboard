"""Mock parser shares — in-memory, so demo mode round-trips a real share flow.

Kept stateful rather than serving one canned token because the thing worth
exercising in demo mode is create → open the URL → see the snapshot, and a
fixed fixture can only test the last step.
"""

import secrets

from flask import Blueprint, jsonify, request

mock_share_bp = Blueprint("mock_share", __name__)

VALID_KINDS = {"dscan", "local", "fleet"}
VALID_VISIBILITY = {"link", "alliance"}

_MOCK_SHARES = {}


@mock_share_bp.route("/api/share", methods=["POST"])
def api_create_share():
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400
    kind = data.get("kind")
    if kind not in VALID_KINDS:
        return jsonify({"error": f"kind must be one of: {', '.join(sorted(VALID_KINDS))}"}), 400
    visibility = data.get("visibility", "link")
    if visibility not in VALID_VISIBILITY:
        return jsonify({"error": "invalid visibility"}), 400
    payload = data.get("payload")
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be an object"}), 400

    token = secrets.token_urlsafe(24)
    _MOCK_SHARES[token] = {
        "token": token,
        "kind": kind,
        "visibility": visibility,
        "title": (data.get("title") or None),
        "created_by": "Demo Pilot",
        "created_at": "2026-04-29T12:00:00Z",
        "expires_at": "2026-05-02T12:00:00Z",
        "payload": payload,
    }
    return jsonify({
        "token": token,
        "url": f"/s/{token}",
        "kind": kind,
        "visibility": visibility,
        "expires_at": _MOCK_SHARES[token]["expires_at"],
    }), 201


@mock_share_bp.route("/api/share/<token>", methods=["GET"])
def api_get_share(token):
    report = _MOCK_SHARES.get(token)
    if not report:
        return jsonify({"error": "not found"}), 404
    # Demo mode reports sso_enabled=False and has no write gate, so an
    # alliance-only share is always viewable here.
    return jsonify(report)
