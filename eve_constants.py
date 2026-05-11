"""
Game-wide constants. Not deployment-specific — these values are universal across
EVE Online and the dashboard's HTTP plumbing, so they don't belong in a per-alliance
config. Imported directly by esi_client and (for backwards compat) re-exported
from config.py.
"""

# ===== ESI / zKill HTTP =====
ESI_BASE = "https://esi.evetech.net/latest"
ESI_DATASOURCE = "tranquility"
ZKILL_BASE = "https://zkillboard.com/api"
ZKILL_RECENT_HOURS = 24

CACHE_TTL = {
    "sovereignty": 300,                # 5 min — sov changes slowly
    "sovereignty_structures": 300,     # 5 min — ADM levels
    "system_kills": 300,               # 5 min
    "system_jumps": 300,               # 5 min
    "constellation_info": 86400,       # 24h — static
    "system_info": 86400,              # 24h — static
    "region_info": 86400,              # 24h — static
    "zkill": 120,                      # 2 min — kills change fast
    "zkill_stats": 3600,               # 1h — char kill stats don't change fast
    "entity_info": 3600,               # 1h — alliance/corp/character names
}

# ===== EVE planet types — used by PI data labelling =====
PLANET_TYPE_NAMES = {
    11: "Planet (Temperate)",
    12: "Planet (Ice)",
    13: "Planet (Gas)",
    2014: "Planet (Oceanic)",
    2015: "Planet (Lava)",
    2016: "Planet (Barren)",
    2017: "Planet (Storm)",
    2063: "Planet (Plasma)",
}

# ===== Threat ship groups (used for capital/dropper role detection via zkill stats) =====
# Keys are EVE ship group IDs (verified via ESI /universe/types/{id}/)
THREAT_SHIP_GROUPS = {
    30:   "TITAN",
    659:  "SUPER",
    485:  "DREAD",
    547:  "CARRIER",
    1538: "FAX",
    898:  "BLOPS",   # Black Ops BS — covert cyno + jump bridge
    833:  "RECON",   # Force Recon Ships (Arazu/Pilgrim/Rapier/Falcon) — covert cyno
    834:  "BOMBER",  # Stealth Bombers — covert cyno
    830:  "COVOPS",  # Covert Ops frigates (Anathema/Buzzard/Cheetah/Helios) — covert cyno
    963:  "T3C",     # Strategic Cruisers (Tengu/Legion/Proteus/Loki) — covert cyno subsystem
}

# ===== Sovereignty upgrades =====
# iHub/Sov Hub upgrade catalog. Universal across EVE — same upgrades exist
# regardless of which alliance/region a deployment monitors. Per-alliance
# choices about which upgrades are installed live in the deployment's
# SYSTEM_UPGRADES dict.
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
    "SCF": {"name": "Supercap Facility",    "category": "strategic"},
}
