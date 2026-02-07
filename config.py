"""
EVE Intel Dashboard Configuration
Astrum Mechanica / Get Off My Lawn - Kalevala Expanse

Configure your monitored constellations and other settings here.
"""

# ESI Base URL
ESI_BASE = "https://esi.evetech.net/latest"
ESI_DATASOURCE = "tranquility"

# Cache TTL in seconds
CACHE_TTL = {
    "sovereignty": 300,      # 5 min - sov changes slowly
    "system_kills": 300,     # 5 min
    "system_jumps": 300,     # 5 min
    "constellation_info": 86400,  # 24h - static data
    "system_info": 86400,         # 24h - static data
    "zkill": 120,                 # 2 min - kills change fast
}

# ===== CONFIGURE YOUR CONSTELLATIONS HERE =====
# Format: { "name": "CONSTELLATION-ID", "id": ESI_constellation_id }
# You can find constellation IDs via ESI:
#   GET /universe/constellations/ -> list of all IDs
#   GET /universe/constellations/{id}/ -> name + systems
#
# LAWN holds both constellations in Kalevala Expanse:
#   6-CBBM and 2Q-8WA
# SL0W CHILDREN AT PLAY collapsed and retreated to highsec.
# Their remnant sov in neighboring constellations may attract
# other groups looking to claim it.
# We'll resolve the ESI IDs dynamically on startup.

MONITORED_CONSTELLATION_NAMES = [
    "6-CBBM",
    "2Q-8WA",
]

# Your alliance info (for highlighting friendly vs hostile)
FRIENDLY_ALLIANCES = [
    "Get Off My Lawn",
]

FRIENDLY_CORPORATIONS = [
    "Astrum Mechanica",
]

# zKillboard settings
ZKILL_BASE = "https://zkillboard.com/api"
ZKILL_RECENT_HOURS = 24  # How far back to pull kills

# Flask settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = True
