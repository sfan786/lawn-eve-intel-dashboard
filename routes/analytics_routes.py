"""
Basic traffic analytics — is anybody actually using this dashboard?

Records two things per request and nothing else: a hit against
(hour, kind, path) and a daily row per visitor. Both are rollups (see the
tables in db.py), so the storage cost is a few hundred rows a day no matter how
much the dashboard is polled.

Privacy: no IP addresses, user agents, or request bodies are stored. A visitor
is identified by a truncated HMAC of (IP + user agent) keyed on a server-side
secret, which is enough to count "how many distinct people" without keeping
anything that identifies them. Logged-in SSO sessions additionally stamp the
character name, since knowing which pilots use the tool is the whole point.

Counts are buffered in memory and flushed on an interval so an SQLite write is
not on the path of every dashboard poll. A crash loses at most one flush window
of counts, which is an acceptable trade for a usage metric.

Reading the stats is operator-only and closed by default: an explicit character
allowlist (ANALYTICS_ALLOWED_CHARACTER_IDS) and/or a dedicated password
(ANALYTICS_PASSWORD), never the fleet-wide write-auth credential. Recording
still runs when neither is set, so data accumulates until you unlock it.
"""

import hashlib
import hmac
import logging
import os
import re
import threading
import time
from datetime import UTC, datetime
from functools import wraps

from flask import Blueprint, jsonify, request, session

import config
import db
from routes.limiter import ANALYTICS_LIMIT, limiter

log = logging.getLogger(__name__)

analytics_bp = Blueprint("analytics", __name__)

ANALYTICS_ENABLED = os.environ.get("ANALYTICS_ENABLED", "true").lower() != "false"
# How long counts may sit in memory before being written.
FLUSH_INTERVAL_SECONDS = int(os.environ.get("ANALYTICS_FLUSH_SECONDS", "60"))
# Hard cap so a traffic spike can't grow the buffer without bound.
FLUSH_MAX_ENTRIES = 500
PRUNE_INTERVAL_SECONDS = 24 * 3600

# SPA routes we count by name. Anything else that reaches the catch-all is
# bucketed as "/other" — scanners probing /wp-login.php and friends would
# otherwise give the path column unbounded cardinality.
KNOWN_PAGES = {"/", "/entosis", "/analytics", "/war"}

_BOT_UA = re.compile(
    r"bot|crawl|spider|slurp|bingpreview|facebookexternalhit|headless|"
    r"monitor|uptime|curl/|wget/|python-requests|httpx|scrapy",
    re.I,
)

# Buffers: {(hour, kind, path): views} and {(day, hash): {...}}
_hourly = {}
_visitors = {}
_buffer_lock = threading.Lock()
_last_flush = time.time()
_last_prune = 0.0

# Keyed on the same secret that signs session cookies unless an explicit salt is
# set. A per-process random fallback (config's own default) means visitor counts
# reset on restart — fine for local dev, which is the only place that happens.
_SALT = (os.environ.get("ANALYTICS_SALT") or config.FLASK_SECRET_KEY).encode()


def _client_ip():
    """Client IP for visitor hashing only — never stored, only hashed.

    With TRUSTED_PROXY_HOPS set, ProxyFix has already rewritten remote_addr
    from the trusted hop, so it is both correct and unforgeable — prefer it.
    Without it we read the forwarding headers directly: a client can spoof
    those, but for a usage metric a forgeable identity beats a shared one
    (every visitor behind nginx collapsing into a single "visitor").
    """
    if config.TRUSTED_PROXY_HOPS > 0:
        return request.remote_addr or "?"
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.headers.get("X-Real-IP") or request.remote_addr or "?"


def visitor_hash():
    """Stable pseudonymous ID for the caller. Not reversible to an IP."""
    raw = f"{_client_ip()}|{request.headers.get('User-Agent', '')}"
    return hmac.new(_SALT, raw.encode(), hashlib.sha256).hexdigest()[:16]


def classify_request():
    """Return (kind, path) to count this request under, or None to ignore it.

    kind is 'page' (SPA load), 'api' (XHR) or 'bot'. Static assets are ignored
    entirely — they say nothing about usage that the page load didn't already.
    """
    path = request.path
    if path.startswith("/assets/") or path.startswith("/static/") or path == "/favicon.ico":
        return None
    if _BOT_UA.search(request.headers.get("User-Agent", "")):
        return ("bot", "*")
    if path.startswith("/api/"):
        # The url_rule keeps parameterised routes ("/api/zkill/<id>") from
        # exploding into one path per system.
        return ("api", request.url_rule.rule if request.url_rule else path)
    return ("page", path if path in KNOWN_PAGES else "/other")


def _buffer(kind, path, vhash, character_name):
    now = datetime.now(UTC)
    hour = now.strftime("%Y-%m-%dT%H")
    day = now.strftime("%Y-%m-%d")
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    with _buffer_lock:
        hkey = (hour, kind, path)
        _hourly[hkey] = _hourly.get(hkey, 0) + 1
        if kind == "bot":
            # Bots are counted in the hourly totals so the operator can see how
            # much of the traffic is not human, but they are never visitors.
            return len(_hourly)

        vkey = (day, vhash)
        entry = _visitors.get(vkey)
        if entry is None:
            entry = _visitors[vkey] = {
                "character_name": None,
                "page_views": 0,
                "api_calls": 0,
                "first_seen": stamp,
                "last_seen": stamp,
            }
        entry["page_views" if kind == "page" else "api_calls"] += 1
        entry["last_seen"] = stamp
        if character_name:
            entry["character_name"] = character_name
        return len(_hourly) + len(_visitors)


def flush(force=False):
    """Write buffered counts to SQLite. Cheap no-op when there is nothing to do."""
    global _last_flush, _last_prune
    with _buffer_lock:
        if not force and (time.time() - _last_flush) < FLUSH_INTERVAL_SECONDS:
            return
        if not _hourly and not _visitors:
            _last_flush = time.time()
            return
        hourly, visitors = _hourly.copy(), _visitors.copy()
        _hourly.clear()
        _visitors.clear()
        _last_flush = time.time()

    try:
        db.record_traffic(hourly, visitors)
    except Exception:
        # Analytics must never break the app; losing a window of counts is fine.
        log.exception("Traffic analytics flush failed, dropping %d buckets", len(hourly))

    if time.time() - _last_prune > PRUNE_INTERVAL_SECONDS:
        _last_prune = time.time()
        try:
            db.prune_traffic()
        except Exception:
            log.exception("Traffic analytics prune failed")


@analytics_bp.after_app_request
def _record(response):
    """Count the request that just completed. Registered app-wide by the blueprint."""
    if not ANALYTICS_ENABLED or response.status_code == 404:
        # 404s are almost entirely scanners probing for PHP admin panels, and
        # unknown /api/ paths land on the SPA catch-all rule — neither is usage.
        return response
    try:
        classified = classify_request()
        if classified:
            kind, path = classified
            size = _buffer(kind, path, visitor_hash(), session.get("character_name"))
            flush(force=size >= FLUSH_MAX_ENTRIES)
    except Exception:
        log.exception("Traffic analytics recording failed")
    return response


# ============ Operator auth ============
#
# Reading usage stats is NOT gated by require_write_auth on purpose. That
# credential is fleet-wide — TIMER_PASSWORD is handed out for timers and
# entosis, and SSO write access covers every member of the alliance. Analytics
# gets its own, narrower gate: an explicit character allowlist and/or a separate
# password, both off by default. Recording keeps running when neither is set;
# only reading is closed.


def analytics_auth_state():
    """Return (configured, authorized) for the current request."""
    if not config.ANALYTICS_AUTH_CONFIGURED:
        return False, False
    character_id = session.get("character_id")
    if character_id and character_id in config.ANALYTICS_ALLOWED_CHARACTER_IDS:
        return True, True
    header = request.headers.get("X-Analytics-Auth") or ""
    if config.ANALYTICS_PASSWORD and hmac.compare_digest(header, config.ANALYTICS_PASSWORD):
        return True, True
    return True, False


def require_analytics_auth(view):
    """Decorator: only an allowlisted character or the analytics password gets in."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        configured, authorized = analytics_auth_state()
        if not configured:
            return jsonify({
                "error": "Analytics access not configured",
                "detail": "Set ANALYTICS_ALLOWED_CHARACTER_IDS or ANALYTICS_PASSWORD to unlock.",
            }), 503
        if not authorized:
            log.warning("Rejected unauthorized analytics request to %s", request.path)
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapper


# ============ Routes ============

@analytics_bp.route("/api/analytics/auth")
@limiter.limit(ANALYTICS_LIMIT)
def api_analytics_auth():
    """What the /analytics page needs to draw its unlock UI. Reveals no data."""
    configured, authorized = analytics_auth_state()
    return jsonify({
        "configured": configured,
        "authorized": authorized,
        "sso": bool(config.SSO_ENABLED and config.ANALYTICS_ALLOWED_CHARACTER_IDS),
        "password": bool(config.ANALYTICS_PASSWORD),
        "character_name": session.get("character_name") if authorized else None,
    })


@analytics_bp.route("/api/analytics/summary")
@limiter.limit(ANALYTICS_LIMIT)
@require_analytics_auth
def api_analytics_summary():
    """Usage rollup. Operator-only — see require_analytics_auth."""
    try:
        days = min(max(int(request.args.get("days", 30)), 1), 365)
    except ValueError:
        days = 30
    # Flush first so the numbers include the session that is looking at them.
    flush(force=True)
    return jsonify(db.get_traffic_summary(days))
