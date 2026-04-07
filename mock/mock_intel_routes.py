from flask import Blueprint, jsonify, request
from mock.mock_data import MOCK_NEIGHBOR_INTEL

mock_intel_bp = Blueprint("mock_intel", __name__)


@mock_intel_bp.route("/api/intel/neighbors")
def api_neighbor_intel():
    return jsonify(MOCK_NEIGHBOR_INTEL)


MOCK_LOCAL_SCAN = [
    {"name": "Torchwood One",    "character_id": 90000001, "corporation_name": "Astrum Mechanica",       "alliance_name": "Get Off My Lawn",        "standing": "lawn"},
    {"name": "Gnome Defender",   "character_id": 90000002, "corporation_name": "Gnomeland Services",     "alliance_name": "Get Off My Lawn",        "standing": "lawn"},
    {"name": "Lawn HC Pilot",    "character_id": 90000003, "corporation_name": "LAWN HC",                "alliance_name": "Get Off My Lawn",        "standing": "lawn"},
    {"name": "BorderZone Hero",  "character_id": 90000004, "corporation_name": "BOZON Corp Alpha",       "alliance_name": "BorderZone",                   "standing": "friendly"},
    {"name": "Gnome Altie",      "character_id": 90000005, "corporation_name": "Gnomes von Zurich",      "alliance_name": "Gnomes Rising HoA",            "standing": "friendly"},
    {"name": "Skeleton Pilot",   "character_id": 90000009, "corporation_name": "MEAN Corp Alpha",        "alliance_name": "The Skeleton Crew",            "standing": "friendly"},
    {"name": "WOMP Deployer",    "character_id": 90000010, "corporation_name": "WOMP Logistics",         "alliance_name": "Weapons Of Mass Production.",  "standing": "friendly"},
    {"name": "RedPill Raider",   "character_id": 90000006, "corporation_name": "Pandemic Horde Inc.",    "alliance_name": "Pandemic Horde",         "standing": "unknown"},
    {"name": "SL0W Remnant",     "character_id": 90000007, "corporation_name": "Slow Corp",              "alliance_name": "SL0W CHILDREN AT PLAY",  "standing": "unknown"},
    {"name": "T.RD Scout",       "character_id": 90000008, "corporation_name": "Rejected Corp",          "alliance_name": "The Rejected.",          "standing": "unknown"},
    {"name": "ghost_pilot_x",    "character_id": None,     "corporation_name": None,                     "alliance_name": None,                     "standing": "unresolved"},
]


@mock_intel_bp.route("/api/local/scan", methods=["POST"])
def api_local_scan():
    return jsonify(MOCK_LOCAL_SCAN)
