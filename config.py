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
    "Get Off My Lawn",        # LAWN (150097440)
    "BorderZone",             # BOZON (99012845) — allies
    "Gnomes Rising HoA",      # GNOME (99013982) — LAWN alt/highsec alliance
]

FRIENDLY_CORPORATIONS = [
    # LAWN member corporations (as of Feb 2026)
    "Astrum Mechanica",
    "DarkMatterEnterprises",
    "Derp Company",
    "Dormir no da ISK",
    "Gnome Tactical Foundations and Orientation",
    "Gnomeland Services",
    "Gnomes von Zurich",
    "Gnomestead Structures",
    "LAWN HC",
    "Moo-Tang Clan",
    "Obsidian Engineering",
    "Undersized Armada",
]

# ===== SOVEREIGNTY UPGRADES =====
# iHub/Sov Hub upgrades installed in LAWN systems.
# Manually maintained — ESI doesn't expose upgrade fittings without SSO auth.
# Categories: military (ratting anomalies), industry (mining), strategic (exploration/infra)

UPGRADE_TYPES = {
    "mTD": {"name": "Minor Threat Detection", "category": "military"},
    "MTD": {"name": "Major Threat Detection", "category": "military"},
    "PA":  {"name": "Prospecting Array",      "category": "industry"},
    "PA_Trit": {"name": "Prospecting Array (Tritanium)", "category": "industry"},
    "PA_Mex":  {"name": "Prospecting Array (Mexallon)",  "category": "industry"},
    "PA_Pyer": {"name": "Prospecting Array (Pyerite)",   "category": "industry"},
    "PA_Iso":  {"name": "Prospecting Array (Isogen)",    "category": "industry"},
    "PA_Nocx": {"name": "Prospecting Array (Nocxium)",   "category": "industry"},
    "PA_Zyd":  {"name": "Prospecting Array (Zydrine)",   "category": "industry"},
    "ED":  {"name": "Exploration Detector", "category": "strategic"},
    "PMD": {"name": "Power Monitoring",     "category": "strategic"},
    "SCF": {"name": "Supercap Facility",    "category": "strategic"}
}

# Per-system upgrades: system_name -> list of {"type": abbrev, "level": int}
SYSTEM_UPGRADES = {
    # 6-CBBM Constellation
    "1-KCSA": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 3}],
    "F48K-D": [{"type": "MTD", "level": 2}],
    "JT2I-7": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 2}],
    "N-JK02": [{"type": "ED", "level": 3}],
    "UDVW-O": [{"type": "ED", "level": 1}],
    "UJXC-B": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 3}, {"type": "ED", "level": 1}],
    "XTJ-5Q": [{"type": "MTD", "level": 1}, {"type": "ED", "level": 1}],
    # 2Q-8WA Constellation
    "5-VFC6": [{"type": "mTD", "level": 3}, {"type": "MTD", "level": 3}, {"type": "PA_Trit", "level": 1}, {"type": "PA_Mex", "level": 1}],
    "86L-9F": [{"type": "PA_Trit", "level": 1}, {"type": "PA_Mex", "level": 1}, {"type": "PA_Zyd", "level": 1}],
    "BZ-BCK": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 2}],
    "FB5U-I": [{"type": "mTD", "level": 2}, {"type": "MTD", "level": 3}],
    "IUU3-L": [{"type": "MTD", "level": 1}],
    "J-OAH2": [{"type": "mTD", "level": 1}, {"type": "PA_Pyer", "level": 2}, {"type": "PA_Iso", "level": 2}, {"type": "PA_Nocx", "level": 1}],
    "O5-YNW": [{"type": "mTD", "level": 1}, {"type": "MTD", "level": 3}],
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
# ===== PLANETARY INTERACTION DATA =====
# Fetched static data for PI planets in LAWN space.
PI_DATA = {
    "1-KCSA": [{"planet_id": 40179067, "name": "1-KCSA I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179068, "name": "1-KCSA II", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179070, "name": "1-KCSA III", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179072, "name": "1-KCSA IV", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179074, "name": "1-KCSA V", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179085, "name": "1-KCSA VI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179106, "name": "1-KCSA VII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179115, "name": "1-KCSA VIII", "type_id": 13, "type": "Planet (Gas)"}],
    "F48K-D": [{"planet_id": 40179301, "name": "F48K-D I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179302, "name": "F48K-D II", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179304, "name": "F48K-D III", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179306, "name": "F48K-D IV", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179310, "name": "F48K-D V", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179313, "name": "F48K-D VI", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179316, "name": "F48K-D VII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179343, "name": "F48K-D VIII", "type_id": 11, "type": "Planet (Temperate)"}],
    "JT2I-7": [{"planet_id": 40178925, "name": "JT2I-7 I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40178926, "name": "JT2I-7 II", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40178928, "name": "JT2I-7 III", "type_id": 2014, "type": "Planet (Oceanic)"}, {"planet_id": 40178930, "name": "JT2I-7 IV", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40178935, "name": "JT2I-7 V", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40178939, "name": "JT2I-7 VI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40178959, "name": "JT2I-7 VII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40178984, "name": "JT2I-7 VIII", "type_id": 12, "type": "Planet (Ice)"}],
    "N-JK02": [{"planet_id": 40178858, "name": "N-JK02 I", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40178859, "name": "N-JK02 II", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40178860, "name": "N-JK02 III", "type_id": 2063, "type": "Planet (Plasma)"}, {"planet_id": 40178862, "name": "N-JK02 IV", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40178864, "name": "N-JK02 V", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40178866, "name": "N-JK02 VI", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40178868, "name": "N-JK02 VII", "type_id": 2017, "type": "Planet (Storm)"}, {"planet_id": 40178871, "name": "N-JK02 VIII", "type_id": 2063, "type": "Planet (Plasma)"}, {"planet_id": 40178873, "name": "N-JK02 IX", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40178885, "name": "N-JK02 X", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40178916, "name": "N-JK02 XI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40178921, "name": "N-JK02 XII", "type_id": 12, "type": "Planet (Ice)"}],
    "UDVW-O": [{"planet_id": 40179229, "name": "UDVW-O I", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40179231, "name": "UDVW-O II", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179234, "name": "UDVW-O III", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179239, "name": "UDVW-O IV", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179259, "name": "UDVW-O V", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179286, "name": "UDVW-O VI", "type_id": 12, "type": "Planet (Ice)"}],
    "UJXC-B": [{"planet_id": 40179144, "name": "UJXC-B I", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40179146, "name": "UJXC-B II", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179148, "name": "UJXC-B III", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179150, "name": "UJXC-B IV", "type_id": 2017, "type": "Planet (Storm)"}, {"planet_id": 40179153, "name": "UJXC-B V", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179155, "name": "UJXC-B VI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179176, "name": "UJXC-B VII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179194, "name": "UJXC-B VIII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179222, "name": "UJXC-B IX", "type_id": 12, "type": "Planet (Ice)"}],
    "XTJ-5Q": [{"planet_id": 40179019, "name": "XTJ-5Q I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179020, "name": "XTJ-5Q II", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40179023, "name": "XTJ-5Q III", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179025, "name": "XTJ-5Q IV", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40179028, "name": "XTJ-5Q V", "type_id": 2014, "type": "Planet (Oceanic)"}, {"planet_id": 40179031, "name": "XTJ-5Q VI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179036, "name": "XTJ-5Q VII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179043, "name": "XTJ-5Q VIII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40179063, "name": "XTJ-5Q IX", "type_id": 2014, "type": "Planet (Oceanic)"}],
    "5-VFC6": [{"planet_id": 40182860, "name": "5-VFC6 I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182862, "name": "5-VFC6 II", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182864, "name": "5-VFC6 III", "type_id": 2014, "type": "Planet (Oceanic)"}, {"planet_id": 40182867, "name": "5-VFC6 IV", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40182870, "name": "5-VFC6 V", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182872, "name": "5-VFC6 VI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182895, "name": "5-VFC6 VII", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182899, "name": "5-VFC6 VIII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182922, "name": "5-VFC6 IX", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182940, "name": "5-VFC6 X", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182968, "name": "5-VFC6 XI", "type_id": 2017, "type": "Planet (Storm)"}, {"planet_id": 40182971, "name": "5-VFC6 XII", "type_id": 2014, "type": "Planet (Oceanic)"}],
    "86L-9F": [{"planet_id": 40183070, "name": "86L-9F I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183071, "name": "86L-9F II", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40183073, "name": "86L-9F III", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183074, "name": "86L-9F IV", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183075, "name": "86L-9F V", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40183077, "name": "86L-9F VI", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183079, "name": "86L-9F VII", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40183081, "name": "86L-9F VIII", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40183084, "name": "86L-9F IX", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40183090, "name": "86L-9F X", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183095, "name": "86L-9F XI", "type_id": 13, "type": "Planet (Gas)"}],
    "BZ-BCK": [{"planet_id": 40182738, "name": "BZ-BCK I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182740, "name": "BZ-BCK II", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40182742, "name": "BZ-BCK III", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40182743, "name": "BZ-BCK IV", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182762, "name": "BZ-BCK V", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182792, "name": "BZ-BCK VI", "type_id": 12, "type": "Planet (Ice)"}, {"planet_id": 40182813, "name": "BZ-BCK VII", "type_id": 12, "type": "Planet (Ice)"}],
    "FB5U-I": [{"planet_id": 40182682, "name": "FB5U-I I", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40182683, "name": "FB5U-I II", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182684, "name": "FB5U-I III", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40182687, "name": "FB5U-I IV", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182690, "name": "FB5U-I V", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182703, "name": "FB5U-I VI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182723, "name": "FB5U-I VII", "type_id": 13, "type": "Planet (Gas)"}],
    "IUU3-L": [{"planet_id": 40183102, "name": "IUU3-L I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183104, "name": "IUU3-L II", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40183122, "name": "IUU3-L III", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40183160, "name": "IUU3-L IV", "type_id": 12, "type": "Planet (Ice)"}, {"planet_id": 40183182, "name": "IUU3-L V", "type_id": 12, "type": "Planet (Ice)"}],
    "J-OAH2": [{"planet_id": 40183199, "name": "J-OAH2 I", "type_id": 2063, "type": "Planet (Plasma)"}, {"planet_id": 40183201, "name": "J-OAH2 II", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40183202, "name": "J-OAH2 III", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183204, "name": "J-OAH2 IV", "type_id": 2015, "type": "Planet (Lava)"}, {"planet_id": 40183205, "name": "J-OAH2 V", "type_id": 2063, "type": "Planet (Plasma)"}, {"planet_id": 40183206, "name": "J-OAH2 VI", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40183210, "name": "J-OAH2 VII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40183231, "name": "J-OAH2 VIII", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40183266, "name": "J-OAH2 IX", "type_id": 13, "type": "Planet (Gas)"}],
    "O5-YNW": [{"planet_id": 40182977, "name": "O5-YNW I", "type_id": 2016, "type": "Planet (Barren)"}, {"planet_id": 40182979, "name": "O5-YNW II", "type_id": 2017, "type": "Planet (Storm)"}, {"planet_id": 40182981, "name": "O5-YNW III", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40182983, "name": "O5-YNW IV", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40182993, "name": "O5-YNW V", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40183015, "name": "O5-YNW VI", "type_id": 13, "type": "Planet (Gas)"}, {"planet_id": 40183045, "name": "O5-YNW VII", "type_id": 12, "type": "Planet (Ice)"}, {"planet_id": 40183067, "name": "O5-YNW VIII", "type_id": 2014, "type": "Planet (Oceanic)"}],
    "S-LHPJ": [{"planet_id": 40183300, "name": "S-LHPJ I", "type_id": 2014, "type": "Planet (Oceanic)"}, {"planet_id": 40183301, "name": "S-LHPJ II", "type_id": 2014, "type": "Planet (Oceanic)"}, {"planet_id": 40183303, "name": "S-LHPJ III", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40183304, "name": "S-LHPJ IV", "type_id": 11, "type": "Planet (Temperate)"}, {"planet_id": 40183308, "name": "S-LHPJ V", "type_id": 2017, "type": "Planet (Storm)"}, {"planet_id": 40183312, "name": "S-LHPJ VI", "type_id": 13, "type": "Planet (Gas)"}]
}
