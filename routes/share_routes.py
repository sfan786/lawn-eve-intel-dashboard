"""
Shareable parser snapshots.

The D-scan, Local and Fleet parsers produce a read-out that only exists in the
tab that made it; COPY flattens it to plain text and loses the colour coding,
sorting and risk annotations that make it readable at a glance. A share freezes
the parsed result and publishes it at an unguessable URL.

The snapshot is deliberately frozen rather than re-derived on view. A local
scan's standings and risk tiers are only true as of when they were scanned, so
re-running the lookups would both change the answer under the reader and spend
the rate-limited zKill/ESI fan-out on every page load.

Two audiences, chosen per share: `link` (anyone holding the URL, for pasting
into a coalition channel) and `alliance` (viewer must pass the same write-auth
gate as timers and entosis).
"""

import json
import logging
import secrets

from flask import Blueprint, jsonify, request

import db
from routes.auth_sso import current_character_name, request_is_authorized, require_write_auth
from routes.limiter import SHARE_LIMIT, SHARE_READ_LIMIT, limiter

log = logging.getLogger(__name__)

share_bp = Blueprint("share", __name__)

VALID_KINDS = {"dscan", "local", "fleet"}
VALID_VISIBILITY = {"link", "alliance"}

# Bound what one share may weigh. A 300-pilot local scan with risk data
# serializes to well under 100 KB, so this is headroom rather than a ceiling
# anyone should meet.
#
# Note this REJECTS rather than truncating, unlike the AI route's input cap
# (ai_routes._MAX_INPUT_CHARS), which trims and logs. That is right there and
# wrong here: half a prompt is still a prompt, but half a JSON document is not
# a smaller report, it is a corrupt one. Do not "make this consistent".
MAX_PAYLOAD_BYTES = 262144

# ~192 bits. Guessing is hopeless on entropy alone; the read rate limit is
# belt-and-braces.
TOKEN_BYTES = 24


@share_bp.route("/api/share", methods=["POST"])
@require_write_auth
@limiter.limit(SHARE_LIMIT)
def api_create_share():
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON payload"}), 400

    kind = data.get("kind")
    if kind not in VALID_KINDS:
        return jsonify({"error": f"kind must be one of: {', '.join(sorted(VALID_KINDS))}"}), 400

    visibility = data.get("visibility", "link")
    if visibility not in VALID_VISIBILITY:
        return jsonify({"error": f"visibility must be one of: {', '.join(sorted(VALID_VISIBILITY))}"}), 400

    payload = data.get("payload")
    if not isinstance(payload, dict):
        return jsonify({"error": "payload must be an object"}), 400

    title = data.get("title")
    if title is not None and not isinstance(title, str):
        return jsonify({"error": "title must be a string"}), 400
    title = title.strip()[:120] if title else None

    payload_json = json.dumps(payload, separators=(",", ":"))
    if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        return jsonify({"error": "payload too large"}), 413

    token = secrets.token_urlsafe(TOKEN_BYTES)
    db.create_shared_report(
        token,
        kind,
        payload_json,
        visibility=visibility,
        title=title,
        # None under password-only auth, same as an entosis claim made without SSO.
        created_by=current_character_name(),
    )
    log.info("Shared %s report created (visibility=%s)", kind, visibility)

    report = db.get_shared_report(token)
    return jsonify({
        "token": token,
        "url": f"/s/{token}",
        "kind": kind,
        "visibility": visibility,
        "expires_at": report["expires_at"] if report else None,
    }), 201


@share_bp.route("/api/share/<token>", methods=["GET"])
@limiter.limit(SHARE_READ_LIMIT)
def api_get_share(token):
    report = db.get_shared_report(token)
    # Unknown and expired answer identically, so the endpoint never confirms
    # that a given token was ever real.
    if not report:
        return jsonify({"error": "not found"}), 404

    if report["visibility"] == "alliance" and not request_is_authorized():
        # Distinguishable error value: the frontend renders this as a login
        # prompt rather than a dead end.
        return jsonify({"error": "alliance only"}), 403

    return jsonify({
        "token": report["token"],
        "kind": report["kind"],
        "visibility": report["visibility"],
        "title": report["title"],
        "created_by": report["created_by"],
        "created_at": report["created_at"],
        "expires_at": report["expires_at"],
        "payload": json.loads(report["payload"]),
    })
