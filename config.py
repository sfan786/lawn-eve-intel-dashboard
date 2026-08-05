"""
Application config — thin re-exports from the active deployment module and
game-wide constants. Edit deployments/<name>.py to change alliance/region
data, or eve_constants.py for ESI plumbing.

Run with `DEPLOYMENT=other_deployment python app.py` to switch which deployment
is active. Defaults to lawn_perrigen.
"""

import os
import secrets

from deployments import ACTIVE as _D

# Re-exported for backwards compatibility: callers do `from config import
# UPGRADE_TYPES` etc. noqa: F401 marks them as deliberately "unused" here so
# the linter doesn't strip a module whose whole job is re-export.
from eve_constants import (  # noqa: F401
    CACHE_TTL,
    ESI_BASE,
    ESI_DATASOURCE,
    PLANET_TYPE_NAMES,
    UPGRADE_TYPES,
    ZKILL_BASE,
    ZKILL_RECENT_HOURS,
)

# ===== Deployment identity =====
DEPLOYMENT_ID = _D.DEPLOYMENT_ID
ALLIANCE = _D.ALLIANCE
REGION = _D.REGION
REGION_ID = REGION["id"]

# ===== Posture =====
# What the alliance's relationship to the monitored space actually is. This
# used to be implicit: PRIMARY_CONSTELLATION_IDS meant both "space we care
# about" and "space we own", so every ADM/grinding/upgrade surface assumed
# ownership. An alliance between homes still cares about intel but owns
# nothing, and conflating the two makes the dashboard quietly lie — the map
# paints the old home hostile-red and "Critical ADM" reads 0 precisely because
# there is no friendly sov left to be critical.
#
#   sovereign — we hold sov in PRIMARY_CONSTELLATION_IDS (the default; the
#               full map/ADM/grinding/upgrade stack is live)
#   guest     — we live in a host alliance's sov. We have a home to defend and
#               care about, so the map, campaigns, activity and regional intel
#               all stay — but the iHubs are not ours, so ADM/grinding/upgrades
#               stand down. The host's sov renders as host, not hostile.
#   rootless  — no home, no sov, no map. Only the deployment-neutral intel
#               tooling (D-scan, local scan, fleet comp, kill feed, timers)
POSTURE = getattr(_D, "POSTURE", "sovereign")
# Header subtitle. Deployments in flux can restate their situation here without
# touching JSX; falls back to the region name when empty.
POSTURE_LABEL = getattr(_D, "POSTURE_LABEL", "")

# Two independent questions, deliberately not one flag. "Do we own this space?"
# governs the ADM/grinding/upgrade stack; "do we have a home at all?" governs
# the map, system table, campaigns, activity and neighbour intel. A guest
# answers no to the first and yes to the second — collapsing them into a single
# boolean is what made the dashboard wrong for anything but a sov holder.
HOLDS_SOV = POSTURE == "sovereign"
HAS_AO = POSTURE in ("sovereign", "guest")

# Alliances whose sov we live under. Their systems classify as "host" rather
# than hostile, so a guest deployment's map doesn't paint its own home red.
# Ignored unless POSTURE == "guest". Hosts are not automatically friendly —
# list them in FRIENDLY_ALLIANCE_IDS too if standings say so.
HOST_ALLIANCE_IDS = set(getattr(_D, "HOST_ALLIANCE_IDS", None) or [])

# Regions the kill feed and hostile tracker may be pointed at. A sovereign
# deployment watches exactly its own region; a rootless one has no home to
# anchor to, so it watches several and the UI offers a picker. REGION stays
# populated either way (rootless deployments set it to their default watch
# region), so REGION_ID is never None and existing callers need no changes.
WATCHED_REGIONS = getattr(_D, "WATCHED_REGIONS", None) or [REGION]
WATCHED_REGION_IDS = {r["id"] for r in WATCHED_REGIONS if isinstance(r, dict) and r.get("id")}

# ===== Geography =====
PRIMARY_CONSTELLATION_IDS = _D.PRIMARY_CONSTELLATION_IDS
PRIMARY_CONSTELLATION_NAMES = getattr(_D, "PRIMARY_CONSTELLATION_NAMES", [])
NEIGHBOR_SYSTEM_NAMES = _D.NEIGHBOR_SYSTEM_NAMES
PRIMARY_SYSTEMS = _D.PRIMARY_SYSTEMS
BORDER_SYSTEMS = _D.BORDER_SYSTEMS

# ===== Standings =====
PRIMARY_ALLIANCE_ID = ALLIANCE["id"]
FRIENDLY_ALLIANCE_IDS = _D.FRIENDLY_ALLIANCE_IDS
FRIENDLY_ALLIANCES = _D.FRIENDLY_ALLIANCES
FRIENDLY_CORPORATIONS = _D.FRIENDLY_CORPORATIONS
# Standalone corps with positive standings (not LAWN member corps) — optional
# per deployment. Derived ID/name sets are what the routes consume.
FRIENDLY_STANDING_CORPORATIONS = getattr(_D, "FRIENDLY_STANDING_CORPORATIONS", []) or []
FRIENDLY_STANDING_CORP_IDS = {c["id"] for c in FRIENDLY_STANDING_CORPORATIONS if isinstance(c, dict) and "id" in c}
FRIENDLY_STANDING_CORP_NAMES = {c["name"] for c in FRIENDLY_STANDING_CORPORATIONS if isinstance(c, dict) and isinstance(c.get("name"), str)}
NEIGHBOR_ENTITIES = _D.NEIGHBOR_ENTITIES

# ===== Sov + map =====
SYSTEM_UPGRADES = _D.SYSTEM_UPGRADES
MAP_LAYOUT = _D.MAP_LAYOUT
MAP_LAYOUT_SUBWAY = _D.MAP_LAYOUT_SUBWAY
MAP_CONNECTIONS = _D.MAP_CONNECTIONS
PI_DATA = _D.PI_DATA

# ===== Flask =====
FLASK_HOST = "0.0.0.0"
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
# No usable default: if TIMER_PASSWORD is unset, fall back to a random
# per-process token so timer/structure writes are effectively disabled until
# an operator sets a real password. Never ship a known default — this repo is
# public, so any hardcoded value would be public too.
# .strip() so a whitespace-only value (e.g. "   ") can't bypass the random
# fallback and become a weak/accidental password.
TIMER_PASSWORD = (os.environ.get("TIMER_PASSWORD") or "").strip() or secrets.token_urlsafe(32)

# Signs the Flask session cookie that holds SSO identity. Random fallback keeps
# the app bootable, but prod MUST set a persistent value or every restart logs
# everyone out (and sessions can't be shared across gunicorn workers/restarts).
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)

# ===== EVE SSO =====
EVE_CLIENT_ID = (os.environ.get("EVE_CLIENT_ID") or "").strip()
EVE_CLIENT_SECRET = (os.environ.get("EVE_CLIENT_SECRET") or "").strip()
EVE_CALLBACK_URL = (os.environ.get("EVE_CALLBACK_URL") or "").strip()
# SSO is only wired up when all three are present; otherwise the app falls back
# to TIMER_PASSWORD-only auth (demo/local work with no EVE app registered).
SSO_ENABLED = bool(EVE_CLIENT_ID and EVE_CLIENT_SECRET and EVE_CALLBACK_URL)


def _parse_int_set(raw):
    """Parse a comma/space-separated env string into a set of ints."""
    out = set()
    for tok in (raw or "").replace(",", " ").split():
        try:
            out.add(int(tok))
        except ValueError:
            pass
    return out


# Who may perform writes after SSO login: anyone in the primary alliance, plus
# any extra alliances and an explicit character allowlist (for FCs/guests).
AUTH_ALLOWED_ALLIANCE_IDS = {PRIMARY_ALLIANCE_ID} | _parse_int_set(os.environ.get("AUTH_ALLOWED_ALLIANCE_IDS"))
AUTH_ALLOWED_CHARACTER_IDS = _parse_int_set(os.environ.get("AUTH_ALLOWED_CHARACTER_IDS"))

# ===== Reverse proxy =====
# How many proxy hops in front of the app may be trusted to have set
# X-Forwarded-For. 1 for the single nginx in nginx.conf; 0 when the app is
# exposed directly.
#
# This matters for rate limiting. With 0 hops Flask sees the proxy's own
# address as the client, so every user behind nginx shares ONE per-IP bucket:
# one noisy visitor throttles the intel endpoints for the whole alliance.
# With a non-zero value, ProxyFix rewrites remote_addr from the right-most
# trusted hop and the limits become genuinely per-user.
#
# Never set this higher than the number of proxies you actually control —
# every extra hop is one a client can forge to impersonate someone else.
def _parse_int(raw, default):
    try:
        return max(0, int(str(raw).strip()))
    except (TypeError, ValueError):
        return default


TRUSTED_PROXY_HOPS = _parse_int(os.environ.get("TRUSTED_PROXY_HOPS"), 0)

# ===== Analytics (operator-only) =====
# Deliberately NOT the write-auth credential. TIMER_PASSWORD is shared with the
# whole fleet for timers/entosis, and AUTH_ALLOWED_ALLIANCE_IDS covers every
# alliance member — either would let anyone in the alliance read usage stats.
# Access is an explicit character allowlist and/or a separate password.
ANALYTICS_PASSWORD = (os.environ.get("ANALYTICS_PASSWORD") or "").strip()
ANALYTICS_ALLOWED_CHARACTER_IDS = _parse_int_set(os.environ.get("ANALYTICS_ALLOWED_CHARACTER_IDS"))
# Closed by default: with neither set, traffic is still recorded but nobody can
# read it until an operator opts in. Never fall back to a fleet-wide credential.
ANALYTICS_AUTH_CONFIGURED = bool(ANALYTICS_PASSWORD or ANALYTICS_ALLOWED_CHARACTER_IDS)

# ===== Backwards-compat aliases =====
# Older code imports `LAWN_*` and `MONITORED_CONSTELLATION_IDS`. Keep these
# working while we incrementally rename downstream callers.
LAWN_ALLIANCE_ID = PRIMARY_ALLIANCE_ID
LAWN_CONSTELLATION_IDS = PRIMARY_CONSTELLATION_IDS
MONITORED_CONSTELLATION_IDS = PRIMARY_CONSTELLATION_IDS
