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
from eve_constants import (
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

# ===== Backwards-compat aliases =====
# Older code imports `LAWN_*` and `MONITORED_CONSTELLATION_IDS`. Keep these
# working while we incrementally rename downstream callers.
LAWN_ALLIANCE_ID = PRIMARY_ALLIANCE_ID
LAWN_CONSTELLATION_IDS = PRIMARY_CONSTELLATION_IDS
MONITORED_CONSTELLATION_IDS = PRIMARY_CONSTELLATION_IDS
