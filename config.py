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
TIMER_PASSWORD = os.environ.get("TIMER_PASSWORD") or secrets.token_urlsafe(32)

# ===== Backwards-compat aliases =====
# Older code imports `LAWN_*` and `MONITORED_CONSTELLATION_IDS`. Keep these
# working while we incrementally rename downstream callers.
LAWN_ALLIANCE_ID = PRIMARY_ALLIANCE_ID
LAWN_CONSTELLATION_IDS = PRIMARY_CONSTELLATION_IDS
MONITORED_CONSTELLATION_IDS = PRIMARY_CONSTELLATION_IDS
