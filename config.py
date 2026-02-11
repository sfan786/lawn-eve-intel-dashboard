"""
EVE Intel Dashboard Configuration
Get Off My Lawn [LAWN] — Kalevala Expanse

Configure your monitored constellations and other settings here.
"""

# ESI Base URL
ESI_BASE = "https://esi.evetech.net/latest"
ESI_DATASOURCE = "tranquility"

# Cache TTL in seconds
CACHE_TTL = {
    "sovereignty": 300,      # 5 min - sov changes slowly
    "sovereignty_structures": 300,  # 5 min - ADM levels
    "system_kills": 300,     # 5 min
    "system_jumps": 300,     # 5 min
    "constellation_info": 86400,  # 24h - static data
    "system_info": 86400,         # 24h - static data
    "zkill": 120,                 # 2 min - kills change fast
}

# ===== CONFIGURE YOUR CONSTELLATIONS HERE =====
# LAWN holds both constellations in Kalevala Expanse (region 10000034):
#   6-CBBM (constellation ID: 20000414)
#   2Q-8WA (constellation ID: 20000423)
# SL0W CHILDREN AT PLAY collapsed and retreated to highsec.
# Their remnant sov in neighboring constellations may attract
# other groups looking to claim it.

# Use constellation IDs directly - ESI search doesn't work well with names
MONITORED_CONSTELLATION_IDS = [
    20000414,  # 6-CBBM
    20000423,  # 2Q-8WA
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
