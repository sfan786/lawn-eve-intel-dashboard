from flask import Blueprint, jsonify

mock_hostile_bp = Blueprint("mock_hostile", __name__)

MOCK_ACTIVE_HOSTILES = [
    {
        "id": 99009927,
        "name": "Deepwater Hooligans",
        "type": "alliance",
        "kill_count": 8,
        "primary_kills": 5,
        "systems": [
            {"name": "J9A-BH", "count": 4},
            {"name": "5T-A3D", "count": 2},
            {"name": "6-1T6Z", "count": 1},
            {"name": "LW-YEW", "count": 1},
        ],
        "last_seen": "2026-05-09T14:32:00Z",
        "last_seen_system": "J9A-BH",
        "ship_types": [
            {"name": "Sabre", "count": 3},
            {"name": "Muninn", "count": 2},
            {"name": "Scimitar", "count": 2},
            {"name": "Loki", "count": 1},
        ],
        "pilot_count": 12,
    },
    {
        "id": 99014523,
        "name": "The Rejected.",
        "type": "alliance",
        "kill_count": 5,
        "primary_kills": 3,
        "systems": [
            {"name": "5ZU-VG", "count": 3},
            {"name": "LW-YEW", "count": 2},
        ],
        "last_seen": "2026-05-09T13:51:00Z",
        "last_seen_system": "5ZU-VG",
        "ship_types": [
            {"name": "Vedmak", "count": 4},
            {"name": "Zarmazd", "count": 2},
            {"name": "Kikimora", "count": 1},
        ],
        "pilot_count": 7,
    },
    {
        "id": 99014518,
        "name": "PUT THE FRIES IN THE BAG",
        "type": "alliance",
        "kill_count": 3,
        "primary_kills": 0,
        "systems": [
            {"name": "DYS-CG", "count": 2},
            {"name": "HD-JVQ", "count": 1},
        ],
        "last_seen": "2026-05-09T12:10:00Z",
        "last_seen_system": "DYS-CG",
        "ship_types": [
            {"name": "Stiletto", "count": 2},
            {"name": "Hurricane", "count": 1},
        ],
        "pilot_count": 4,
    },
    {
        "id": 98765432,
        "name": "Pandemic Horde Inc.",
        "type": "corporation",
        "kill_count": 2,
        "primary_kills": 0,
        "systems": [
            {"name": "EU-WFW", "count": 2},
        ],
        "last_seen": "2026-05-09T11:45:00Z",
        "last_seen_system": "EU-WFW",
        "ship_types": [
            {"name": "Stiletto", "count": 1},
            {"name": "Sabre", "count": 1},
        ],
        "pilot_count": 2,
    },
]


@mock_hostile_bp.route("/api/intel/active_hostiles")
def api_active_hostiles():
    return jsonify(MOCK_ACTIVE_HOSTILES)
