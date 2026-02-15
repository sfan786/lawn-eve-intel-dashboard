"""
EVE Intel Dashboard Configuration
Get Off My Lawn [LAWN] — Kalevala Expanse

Configure your monitored constellations and other settings here.
"""

import os

# ESI Base URL
ESI_BASE = "https://esi.evetech.net/latest"
ESI_DATASOURCE = "tranquility"

# The Kalevala Expanse region ID (10 constellations, 69 systems)
REGION_ID = 10000034

# Cache TTL in seconds
CACHE_TTL = {
    "sovereignty": 300,      # 5 min - sov changes slowly
    "sovereignty_structures": 300,  # 5 min - ADM levels
    "system_kills": 300,     # 5 min
    "system_jumps": 300,     # 5 min
    "constellation_info": 86400,  # 24h - static data
    "system_info": 86400,         # 24h - static data
    "region_info": 86400,         # 24h - static data
    "zkill": 120,                 # 2 min - kills change fast
}

# ===== LAWN CONSTELLATIONS =====
# LAWN holds both constellations in Kalevala Expanse (region 10000034):
#   6-CBBM (constellation ID: 20000414)
#   2Q-8WA (constellation ID: 20000423)
LAWN_CONSTELLATION_IDS = [
    20000414,  # 6-CBBM
    20000423,  # 2Q-8WA
]
MONITORED_CONSTELLATION_IDS = LAWN_CONSTELLATION_IDS  # backward compat alias

# ===== NEIGHBOR SYSTEMS (outside TKE) =====
# 18 systems in adjacent regions connected by regional gates to TKE systems.
# Resolved at startup via POST /universe/ids/ to get system IDs.
NEIGHBOR_SYSTEM_NAMES = [
    # Vale of the Silent (4)
    "PX5-LR", "A3-RQ3", "9-GBPD", "LS-JEP",
    # Geminate (7)
    "9-KWXC", "HJO-84", "P-E9GN", "4D9-66", "L-TOFR", "Q-TBHW", "9P4O-F",
    # Etherium Reach (4)
    "AID-9T", "TZ-74M", "FB-MPY", "J7M-3W",
    # Malpais (3)
    "V3P-AZ", "7-YHRX", "Z-EKCY",
]

# Your alliance info (for highlighting friendly vs hostile)
FRIENDLY_ALLIANCES = [
    "Get Off My Lawn",
]

FRIENDLY_CORPORATIONS = [
    "Astrum Mechanica",
]

# ===== SOVEREIGNTY UPGRADES =====
# iHub/Sov Hub upgrades installed in LAWN systems.
# Manually maintained — ESI doesn't expose upgrade fittings without SSO auth.
# Categories: military (ratting anomalies), industry (mining), strategic (exploration/infra)

UPGRADE_TYPES = {
    "mTD": {"name": "Minor Threat Detection", "category": "military"},
    "MTD": {"name": "Major Threat Detection", "category": "military"},
    "PA":  {"name": "Prospecting Array",      "category": "industry"},
    "ED":  {"name": "Exploration Detector", "category": "strategic"},
    "PMD": {"name": "Power Monitoring",     "category": "strategic"},
    "SCF": {"name": "Supercap Facility",    "category": "strategic"}
}

# Per-system upgrades: system_name -> list of {"type": abbrev, "level": int}
SYSTEM_UPGRADES = {
    # 6-CBBM Constellation
    "1-KCSA": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 3}],
    "F48K-D": [{"type": "MTD", "level": 2}],
    "JT2I-7": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 2}, {"type": "PMD", "level": 2}],
    "N-JK02": [{"type": "ED", "level": 3}],
    "UDVW-O": [{"type": "ED", "level": 1}],
    "UJXC-B": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 3}, {"type": "ED", "level": 1}],
    "XTJ-5Q": [{"type": "MTD", "level": 1}, {"type": "ED", "level": 1}],
    # 2Q-8WA Constellation
    "5-VFC6": [{"type": "mTD", "level": 3}, {"type": "MTD", "level": 3}, {"type": "PA", "level": 1}],
    "86L-9F": [{"type": "PA", "level": 2}],
    "BZ-BCK": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 2}],
    "FB5U-I": [{"type": "mTD", "level": 2}, {"type": "MTD", "level": 3}],
    "IUU3-L": [{"type": "MTD", "level": 1}],
    "J-OAH2": [{"type": "mTD", "level": 1}, {"type": "PA", "level": 1}, {"type": "PA", "level": 2}, {"type": "PA", "level": 3}, {"type": "ED", "level": 1}, {"type": "PMD", "level": 3}],
    "O5-YNW": [{"type": "MTD", "level": 3}],
    "S-LHPJ": [{"type": "MTD", "level": 3}],
}
# Neighbor entities to track for "Threat Profiling"
NEIGHBOR_ENTITIES = [
    {"name": "Deepwater Hooligans", "id": 99009927, "type": "alliance"},
    {"name": "PUT THE FRIES IN THE BAG", "id": 99014518, "type": "alliance"},
    {"name": "The Rejected.", "id": 99014523, "type": "alliance"},
]

# zKillboard settings
ZKILL_BASE = "https://zkillboard.com/api"
ZKILL_RECENT_HOURS = 24  # How far back to pull kills

# Flask settings
FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# Timerboard Authentication
TIMER_PASSWORD = os.environ.get("TIMER_PASSWORD", "REDACTED")
