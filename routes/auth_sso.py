"""
EVE SSO (OAuth2) auth + write authorization.

Provides "Log in with EVE" identity and gates write actions (timers, entosis
nodes, annotations, jump bridges) by alliance membership. Authorization state is
held in a signed Flask session cookie. The legacy TIMER_PASSWORD is kept as a
fallback so demo/local work without a registered EVE application.

Identity is derived from the access-token JWT (sub = "CHARACTER:EVE:<id>",
name = character name); alliance is resolved from the public character endpoint.
No ESI scopes are requested.
"""

import hmac
import secrets
from functools import wraps
from urllib.parse import urlencode

import jwt
import requests
from flask import Blueprint, jsonify, redirect, request, session

import config
from esi_client import esi_get
from eve_constants import (
    SSO_AUTHORIZE_URL,
    SSO_ISSUER,
    SSO_JWKS_URL,
    SSO_TOKEN_URL,
)

auth_sso_bp = Blueprint("auth_sso", __name__)

# Cached JWKS client — fetches EVE's signing keys lazily on first login.
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(SSO_JWKS_URL)
    return _jwks_client


def _character_alliance_id(character_id):
    """Resolve a character's alliance ID via public ESI (None if unaffiliated)."""
    try:
        data = esi_get(f"/characters/{character_id}/")
        return data.get("alliance_id")
    except Exception:
        return None


def is_authorized(character_id, alliance_id):
    """A character may write if it's in an allowed alliance or on the allowlist."""
    return (
        character_id in config.AUTH_ALLOWED_CHARACTER_IDS
        or (alliance_id is not None and alliance_id in config.AUTH_ALLOWED_ALLIANCE_IDS)
    )


def request_is_authorized():
    """True if the request carries a valid SSO session OR the legacy password."""
    if session.get("authorized"):
        return True
    header = request.headers.get("X-Timer-Auth") or ""
    return bool(config.TIMER_PASSWORD) and hmac.compare_digest(header, config.TIMER_PASSWORD)


def current_character_name():
    """The logged-in character name (used to stamp entosis claims), else None."""
    return session.get("character_name")


def require_write_auth(view):
    """Decorator: 401 unless the request is authorized (SSO session or password)."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        if not request_is_authorized():
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapper


# ============ Routes ============

@auth_sso_bp.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    return jsonify({
        "sso_enabled": config.SSO_ENABLED,
        "logged_in": bool(session.get("character_id")),
        "character_name": session.get("character_name"),
        "authorized": bool(session.get("authorized")),
    })


@auth_sso_bp.route("/api/auth/sso/login", methods=["GET"])
def api_sso_login():
    if not config.SSO_ENABLED:
        return jsonify({"error": "SSO not configured"}), 404

    state = secrets.token_urlsafe(16)
    session["sso_state"] = state
    # Remember where to send the user back to (same-origin paths only).
    nxt = request.args.get("next") or "/"
    session["sso_next"] = nxt if nxt.startswith("/") else "/"

    params = {
        "response_type": "code",
        "redirect_uri": config.EVE_CALLBACK_URL,
        "client_id": config.EVE_CLIENT_ID,
        "scope": "",
        "state": state,
    }
    return redirect(f"{SSO_AUTHORIZE_URL}?{urlencode(params)}")


@auth_sso_bp.route("/api/auth/sso/callback", methods=["GET"])
def api_sso_callback():
    if not config.SSO_ENABLED:
        return jsonify({"error": "SSO not configured"}), 404

    # CSRF: state must match what we stored at login.
    state = request.args.get("state")
    expected = session.pop("sso_state", None)
    if not state or not expected or not hmac.compare_digest(state, expected):
        return jsonify({"error": "Invalid SSO state"}), 400

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Missing authorization code"}), 400

    # Exchange the code for tokens (confidential client: HTTP Basic auth).
    try:
        resp = requests.post(
            SSO_TOKEN_URL,
            data={"grant_type": "authorization_code", "code": code},
            auth=(config.EVE_CLIENT_ID, config.EVE_CLIENT_SECRET),
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Host": "login.eveonline.com"},
            timeout=15,
        )
        resp.raise_for_status()
        access_token = resp.json()["access_token"]
    except Exception:
        return jsonify({"error": "Token exchange failed"}), 502

    # Validate the access-token JWT signature + issuer against EVE's JWKS.
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(access_token)
        claims = jwt.decode(
            access_token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=SSO_ISSUER,
            options={"verify_aud": False},
        )
    except Exception:
        return jsonify({"error": "Invalid SSO token"}), 502

    # sub looks like "CHARACTER:EVE:123456789"
    sub = claims.get("sub", "")
    try:
        character_id = int(sub.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return jsonify({"error": "Malformed token subject"}), 502
    character_name = claims.get("name", "")

    alliance_id = _character_alliance_id(character_id)
    session["character_id"] = character_id
    session["character_name"] = character_name
    session["alliance_id"] = alliance_id
    session["authorized"] = is_authorized(character_id, alliance_id)
    session.permanent = True

    return redirect(session.pop("sso_next", "/") or "/")


@auth_sso_bp.route("/api/auth/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"status": "ok"})
