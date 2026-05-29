import time
from flask import Blueprint, jsonify, request
from mock.mock_data import MOCK_NEIGHBOR_INTEL, MOCK_REGIONAL_INTEL

mock_intel_bp = Blueprint("mock_intel", __name__)


@mock_intel_bp.route("/api/intel/neighbors")
def api_neighbor_intel():
    return jsonify(MOCK_NEIGHBOR_INTEL)


@mock_intel_bp.route("/api/intel/regional")
def api_regional_intel():
    return jsonify(MOCK_REGIONAL_INTEL)


@mock_intel_bp.route("/api/intel/sov_changes")
def api_sov_changes():
    return jsonify({"changes": [], "checked_at": time.time()})


MOCK_LOCAL_SCAN = [
    {"name": "Torchwood One",    "character_id": 90000001, "corporation_name": "Astrum Mechanica",       "alliance_name": "Get Off My Lawn",        "standing": "lawn"},
    {"name": "Gnome Defender",   "character_id": 90000002, "corporation_name": "Gnomeland Services",     "alliance_name": "Get Off My Lawn",        "standing": "lawn"},
    {"name": "Lawn HC Pilot",    "character_id": 90000003, "corporation_name": "LAWN HC",                "alliance_name": "Get Off My Lawn",        "standing": "lawn"},
    {"name": "BorderZone Hero",  "character_id": 90000004, "corporation_name": "BOZON Corp Alpha",       "alliance_name": "BorderZone",                   "standing": "friendly"},
    {"name": "Gnome Altie",      "character_id": 90000005, "corporation_name": "Gnomes von Zurich",      "alliance_name": "Gnomes Rising HoA",            "standing": "friendly"},
    {"name": "Skeleton Pilot",   "character_id": 90000009, "corporation_name": "MEAN Corp Alpha",        "alliance_name": "The Skeleton Crew",            "standing": "friendly"},
    {"name": "WOMP Deployer",    "character_id": 90000010, "corporation_name": "WOMP Logistics",         "alliance_name": "Weapons Of Mass Production.",        "standing": "friendly"},
    {"name": "EDENC Defender",   "character_id": 90000011, "corporation_name": "EDENC Corp Alpha",        "alliance_name": "EDENCOM DEFENSIVE INITIATIVE",       "standing": "friendly"},
    {"name": "RedPill Raider",   "character_id": 90000006, "corporation_name": "Pandemic Horde Inc.",    "alliance_name": "Pandemic Horde",         "standing": "unknown"},
    {"name": "SL0W Remnant",     "character_id": 90000007, "corporation_name": "Slow Corp",              "alliance_name": "SL0W CHILDREN AT PLAY",  "standing": "unknown"},
    {"name": "T.RD Scout",       "character_id": 90000008, "corporation_name": "Rejected Corp",          "alliance_name": "The Rejected.",          "standing": "unknown"},
    {"name": "ghost_pilot_x",    "character_id": None,     "corporation_name": None,                     "alliance_name": None,                     "standing": "unresolved"},
]


@mock_intel_bp.route("/api/local/scan", methods=["POST"])
def api_local_scan():
    return jsonify(MOCK_LOCAL_SCAN)


MOCK_RISK = {
    "90000001": {"tier": "lawn",           "label": "LAWN",          "kills": 0,   "losses": 0,  "danger": 0,  "gang_ratio": 0,  "solo_kills": 0, "isk_eff": 0,  "roles": []},
    "90000006": {"tier": "very_dangerous", "label": "VERY DANGEROUS","kills": 2341,"losses": 87, "danger": 91, "gang_ratio": 72, "solo_kills": 120,"isk_eff": 88, "roles": ["DREAD", "BLOPS"]},
    "90000007": {"tier": "dangerous",      "label": "DANGEROUS",     "kills": 412, "losses": 55, "danger": 63, "gang_ratio": 58, "solo_kills": 34, "isk_eff": 71, "roles": ["CARRIER"]},
    "90000008": {"tier": "moderate",       "label": "MODERATE",      "kills": 88,  "losses": 40, "danger": 38, "gang_ratio": 45, "solo_kills": 8,  "isk_eff": 56, "roles": []},
}


@mock_intel_bp.route("/api/chars/analyze", methods=["POST"])
def api_chars_analyze():
    char_ids = [str(cid) for cid in (request.json.get("char_ids") or [])]
    results = {}
    for cid in char_ids:
        results[cid] = MOCK_RISK.get(cid, {"tier": "newbie", "label": "NEWBIE", "kills": 4, "losses": 12, "danger": 8, "gang_ratio": 20, "solo_kills": 0, "isk_eff": 22, "roles": []})
    return jsonify(results)


MOCK_FLEET_RESULT = {
    "pilots": [
        {"name": "RedPill Raider",   "character_id": 90000006, "corporation_name": "Pandemic Horde Inc.",  "alliance_name": "Pandemic Horde",          "standing": "unknown",    "risk_tier": "very_dangerous", "risk_label": "VERY DANGEROUS", "kills": 2341, "losses": 87, "danger": 91, "isk_eff": 88, "roles": ["DREAD", "BLOPS"], "fleet_roles": []},
        {"name": "BOSS Capital1",    "character_id": 90000012, "corporation_name": "Brotherhood of Spacers","alliance_name": "Brotherhood of Spacers",  "standing": "unknown",    "risk_tier": "very_dangerous", "risk_label": "VERY DANGEROUS", "kills": 1850, "losses": 62, "danger": 85, "isk_eff": 82, "roles": ["FAX"],             "fleet_roles": ["LOGI"]},
        {"name": "BOSS Fleet FC",    "character_id": 90000013, "corporation_name": "Brotherhood of Spacers","alliance_name": "Brotherhood of Spacers",  "standing": "unknown",    "risk_tier": "dangerous",      "risk_label": "DANGEROUS",      "kills": 620,  "losses": 90, "danger": 68, "isk_eff": 74, "roles": ["BLOPS"],           "fleet_roles": ["BOOSTER", "HAC"]},
        {"name": "BOSS Logi",        "character_id": 90000014, "corporation_name": "Brotherhood of Spacers","alliance_name": "Brotherhood of Spacers",  "standing": "unknown",    "risk_tier": "moderate",       "risk_label": "MODERATE",       "kills": 110,  "losses": 45, "danger": 42, "isk_eff": 58, "roles": [],                  "fleet_roles": ["LOGI", "BC"]},
        {"name": "SL0W Remnant",     "character_id": 90000007, "corporation_name": "Slow Corp",            "alliance_name": "SL0W CHILDREN AT PLAY",   "standing": "unknown",    "risk_tier": "dangerous",      "risk_label": "DANGEROUS",      "kills": 412,  "losses": 55, "danger": 63, "isk_eff": 71, "roles": ["CARRIER"],         "fleet_roles": []},
        {"name": "SL0W Dictor",      "character_id": 90000015, "corporation_name": "Slow Corp",            "alliance_name": "SL0W CHILDREN AT PLAY",   "standing": "unknown",    "risk_tier": "moderate",       "risk_label": "MODERATE",       "kills": 88,   "losses": 40, "danger": 38, "isk_eff": 56, "roles": [],                  "fleet_roles": ["DICTOR"]},
        {"name": "BOSS Newbie",      "character_id": 90000016, "corporation_name": "Brotherhood of Spacers","alliance_name": "Brotherhood of Spacers",  "standing": "unknown",    "risk_tier": "newbie",         "risk_label": "NEWBIE",         "kills": 12,   "losses": 8,  "danger": 15, "isk_eff": 30, "roles": [],                  "fleet_roles": []},
        {"name": "BorderZone Hero",  "character_id": 90000004, "corporation_name": "BOZON Corp Alpha",     "alliance_name": "BorderZone",              "standing": "friendly",   "risk_tier": "moderate",       "risk_label": "MODERATE",       "kills": 95,   "losses": 30, "danger": 41, "isk_eff": 60, "roles": [],                  "fleet_roles": ["BC"]},
        {"name": "Torchwood One",    "character_id": 90000001, "corporation_name": "Astrum Mechanica",     "alliance_name": "Get Off My Lawn",         "standing": "lawn",       "risk_tier": "dangerous",      "risk_label": "DANGEROUS",      "kills": 380,  "losses": 70, "danger": 58, "isk_eff": 67, "roles": [],                  "fleet_roles": ["HAC"]},
        {"name": "ghost_pilot_x",    "character_id": None,     "corporation_name": None,                   "alliance_name": None,                      "standing": "unresolved", "risk_tier": "nodata",         "risk_label": "UNRESOLVED",     "kills": 0,    "losses": 0,  "danger": 0,  "isk_eff": 0,  "roles": [],                  "fleet_roles": []},
    ],
    "summary": {
        "total": 10, "unknown": 7, "friendly": 1, "lawn": 1, "unresolved": 1,
        "avg_danger": 64, "avg_kills": 776, "capitals": 3,
        "risk_distribution": {"very_dangerous": 2, "dangerous": 3, "moderate": 2, "newbie": 1},
        "role_counts": {"DREAD": 1, "FAX": 1, "CARRIER": 1, "BLOPS": 2},
        "fleet_role_counts": {"LOGI": 2, "BOOSTER": 1, "HAC": 2, "BC": 2, "DICTOR": 1},
        "top_alliances": [
            {"name": "Brotherhood of Spacers", "count": 4},
            {"name": "SL0W CHILDREN AT PLAY",  "count": 2},
            {"name": "Pandemic Horde",          "count": 1},
        ],
    },
}


@mock_intel_bp.route("/api/fleet/analyze", methods=["POST"])
def api_fleet_analyze():
    return jsonify(MOCK_FLEET_RESULT)
