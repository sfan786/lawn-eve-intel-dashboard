"""
Demo mode - Run the dashboard with mock data for UI testing.
Usage: python demo.py
"""

from flask import Flask, jsonify, send_from_directory

app = Flask(__name__)

# Mock constellation data based on real Kalevala Expanse systems
MOCK_CONFIG = {
    "constellations": {
        "20000490": {
            "name": "6-CBBM",
            "constellation_id": 20000490,
            "region_id": 10000034,
            "system_ids": [30003384, 30003385, 30003386, 30003387, 30003388, 30003389, 30003390],
            "systems": {
                "30003384": {"name": "1-KCSA", "security_status": -0.18, "system_id": 30003384},
                "30003385": {"name": "UDVW-O", "security_status": -0.08, "system_id": 30003385},
                "30003386": {"name": "UJXC-B", "security_status": -0.12, "system_id": 30003386},
                "30003387": {"name": "F48K-D", "security_status": -0.15, "system_id": 30003387},
                "30003388": {"name": "JT2I-7", "security_status": -0.22, "system_id": 30003388},
                "30003389": {"name": "XTJ-5Q", "security_status": -0.35, "system_id": 30003389},
                "30003390": {"name": "N-JK02", "security_status": -0.28, "system_id": 30003390},
            }
        },
        "20000491": {
            "name": "2Q-8WA",
            "constellation_id": 20000491,
            "region_id": 10000034,
            "system_ids": [30003391, 30003392, 30003393, 30003394, 30003395, 30003396, 30003397, 30003398],
            "systems": {
                "30003391": {"name": "FB5U-I", "security_status": -0.32, "system_id": 30003391},
                "30003392": {"name": "BZ-BCK", "security_status": -0.68, "system_id": 30003392},
                "30003393": {"name": "J-OAH2", "security_status": -0.78, "system_id": 30003393},
                "30003394": {"name": "O5-YNW", "security_status": -0.95, "system_id": 30003394},
                "30003395": {"name": "86L-9F", "security_status": -0.96, "system_id": 30003395},
                "30003396": {"name": "5-VFC6", "security_status": -0.41, "system_id": 30003396},
                "30003397": {"name": "IUU3-L", "security_status": -0.99, "system_id": 30003397},
                "30003398": {"name": "S-LHPJ", "security_status": -1.00, "system_id": 30003398},
            }
        }
    },
    "friendly_alliances": ["Get Off My Lawn"],
    "friendly_corporations": ["Astrum Mechanica"],
    "gate_connections": [
        ["UDVW-O", "UJXC-B"],
        ["UJXC-B", "F48K-D"],
        ["F48K-D", "1-KCSA"],
        ["1-KCSA", "XTJ-5Q"],
        ["XTJ-5Q", "JT2I-7"],
        ["XTJ-5Q", "N-JK02"],
        ["FB5U-I", "BZ-BCK"],
        ["BZ-BCK", "J-OAH2"],
        ["BZ-BCK", "O5-YNW"],
        ["O5-YNW", "86L-9F"],
        ["O5-YNW", "5-VFC6"],
        ["86L-9F", "IUU3-L"],
        ["IUU3-L", "S-LHPJ"],
        ["F48K-D", "FB5U-I"]
    ],
    "neighbor_systems": [
        # Southern border (SL0W remnants - all at ADM 4)
        {"name": "LE-67X", "holder": "SL0W CHILDREN AT PLAY", "adm": 4, "connects_to": "XTJ-5Q"},
        {"name": "L-TLFU", "holder": "SL0W CHILDREN AT PLAY", "adm": 4, "connects_to": "LE-67X"},
        {"name": "BM-VYZ", "holder": "T.RD", "adm": 0, "connects_to": "LE-67X"},
        {"name": "EPCD-D", "holder": "T.RD", "adm": 0, "connects_to": "L-TLFU"},
        {"name": "L-GY1B", "holder": "SL0W CHILDREN AT PLAY", "adm": 4, "connects_to": "N-JK02"},
        {"name": "MN9P-A", "holder": "SL0W CHILDREN AT PLAY", "adm": 4, "connects_to": "L-GY1B"},
        # Etherium Reach gate
        {"name": "AID-9T", "holder": None, "adm": None, "connects_to": "N-JK02", "note": "Etherium Reach"},
        # Eastern border (SL0W remnants)
        {"name": "6V-D0E", "holder": "SL0W CHILDREN AT PLAY", "adm": 4, "connects_to": "S-LHPJ"},
        {"name": "LS3-HP", "holder": "SL0W CHILDREN AT PLAY", "adm": 4, "connects_to": "6V-D0E"},
        {"name": "QX-4HO", "holder": "SL0W CHILDREN AT PLAY", "adm": 4, "connects_to": "LS3-HP"},
        # Northern border (Vale of the Silent - regional gate)
        {"name": "LS-JEP", "holder": None, "adm": None, "connects_to": "UDVW-O", "note": "Vale of the Silent"},
        {"name": "A3-RQ3", "holder": None, "adm": None, "connects_to": "UJXC-B", "note": "Vale of the Silent"}
    ]
}

MOCK_SOVEREIGNTY = {
    # 6-CBBM (7 systems) — all LAWN, brand new claims (ADM 1-2, still grinding)
    "30003384": {"system_id": 30003384, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 2},   # 1-KCSA
    "30003385": {"system_id": 30003385, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 1},   # UDVW-O
    "30003386": {"system_id": 30003386, "alliance_name": "Get Off My Lawn", "corporation_name": "LAWN Logistics", "is_friendly": True, "adm": 1},     # UJXC-B
    "30003387": {"system_id": 30003387, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 2},   # F48K-D
    "30003388": {"system_id": 30003388, "alliance_name": "Get Off My Lawn", "corporation_name": "LAWN Logistics", "is_friendly": True, "adm": 1},     # JT2I-7
    "30003389": {"system_id": 30003389, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 2},   # XTJ-5Q
    "30003390": {"system_id": 30003390, "alliance_name": "Get Off My Lawn", "corporation_name": "LAWN Logistics", "is_friendly": True, "adm": 1},     # N-JK02
    # 2Q-8WA (8 systems) — all LAWN, brand new claims (ADM 1-2, still grinding)
    # Note: SL0W remnant neighbors (LE-67X, L-GY1B, 6V-D0E) have ADM 4
    "30003391": {"system_id": 30003391, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 2},   # FB5U-I
    "30003392": {"system_id": 30003392, "alliance_name": "Get Off My Lawn", "corporation_name": "LAWN Logistics", "is_friendly": True, "adm": 2},     # BZ-BCK
    "30003393": {"system_id": 30003393, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 1},   # J-OAH2
    "30003394": {"system_id": 30003394, "alliance_name": "Get Off My Lawn", "corporation_name": "LAWN Logistics", "is_friendly": True, "adm": 2},     # O5-YNW
    "30003395": {"system_id": 30003395, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 1},   # 86L-9F
    "30003396": {"system_id": 30003396, "alliance_name": "Get Off My Lawn", "corporation_name": "LAWN Logistics", "is_friendly": True, "adm": 1},     # 5-VFC6
    "30003397": {"system_id": 30003397, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 1},   # IUU3-L
    "30003398": {"system_id": 30003398, "alliance_name": "Get Off My Lawn", "corporation_name": "Astrum Mechanica", "is_friendly": True, "adm": 1},   # S-LHPJ
}

MOCK_ACTIVITY = {
    # Newly claimed space — ADMs still building, roaming hostiles from SL0W remnant borders
    # 6-CBBM
    "30003384": {"system_id": 30003384, "ship_kills": 2, "pod_kills": 0, "npc_kills": 420, "jumps": 38},   # 1-KCSA
    "30003385": {"system_id": 30003385, "ship_kills": 0, "pod_kills": 0, "npc_kills": 185, "jumps": 12},   # UDVW-O
    "30003386": {"system_id": 30003386, "ship_kills": 0, "pod_kills": 0, "npc_kills": 230, "jumps": 15},   # UJXC-B
    "30003387": {"system_id": 30003387, "ship_kills": 1, "pod_kills": 0, "npc_kills": 310, "jumps": 48},   # F48K-D (cross-const gate)
    "30003388": {"system_id": 30003388, "ship_kills": 0, "pod_kills": 0, "npc_kills": 95, "jumps": 7},     # JT2I-7
    "30003389": {"system_id": 30003389, "ship_kills": 5, "pod_kills": 2, "npc_kills": 540, "jumps": 67},   # XTJ-5Q (border w/ SL0W)
    "30003390": {"system_id": 30003390, "ship_kills": 3, "pod_kills": 1, "npc_kills": 370, "jumps": 52},   # N-JK02 (border w/ SL0W + Eth.Reach)
    # 2Q-8WA
    "30003391": {"system_id": 30003391, "ship_kills": 0, "pod_kills": 0, "npc_kills": 480, "jumps": 22},   # FB5U-I
    "30003392": {"system_id": 30003392, "ship_kills": 1, "pod_kills": 0, "npc_kills": 650, "jumps": 31},   # BZ-BCK (hub)
    "30003393": {"system_id": 30003393, "ship_kills": 0, "pod_kills": 0, "npc_kills": 390, "jumps": 14},   # J-OAH2
    "30003394": {"system_id": 30003394, "ship_kills": 0, "pod_kills": 0, "npc_kills": 720, "jumps": 18},   # O5-YNW
    "30003395": {"system_id": 30003395, "ship_kills": 0, "pod_kills": 0, "npc_kills": 260, "jumps": 9},    # 86L-9F
    "30003396": {"system_id": 30003396, "ship_kills": 0, "pod_kills": 0, "npc_kills": 150, "jumps": 8},    # 5-VFC6
    "30003397": {"system_id": 30003397, "ship_kills": 0, "pod_kills": 0, "npc_kills": 340, "jumps": 11},   # IUU3-L
    "30003398": {"system_id": 30003398, "ship_kills": 2, "pod_kills": 1, "npc_kills": 510, "jumps": 35},   # S-LHPJ (border w/ SL0W)
}

# No active campaigns — space is secured for now
MOCK_CAMPAIGNS = []

# Mock kill feed — realistic mix of LAWN and regional kills
from datetime import datetime, timedelta, timezone
def _mock_time(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")

MOCK_KILL_FEED = [
    {
        "killmail_id": 119800001,
        "time": _mock_time(8),
        "system_id": 30003389,
        "system_name": "XTJ-5Q",
        "in_lawn": True,
        "victim": {
            "character_name": "xXDarkSlayerXx",
            "corporation_name": "Pandemic Horde Inc.",
            "alliance_name": "Pandemic Horde",
            "ship_type": "Sabre",
            "ship_type_id": 22456,
        },
        "attacker_count": 3,
        "final_blow": {
            "character_name": "LAWN Defender",
            "corporation_name": "Astrum Mechanica",
            "alliance_name": "Get Off My Lawn",
            "ship_type": "Stiletto",
        },
        "total_value": 85000000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800002,
        "time": _mock_time(15),
        "system_id": 30003390,
        "system_name": "N-JK02",
        "in_lawn": True,
        "victim": {
            "character_name": "Scout McScoutface",
            "corporation_name": "Signal Cartel",
            "alliance_name": "EvE-Scout Enclave",
            "ship_type": "Astero",
            "ship_type_id": 33468,
        },
        "attacker_count": 1,
        "final_blow": {
            "character_name": "Gate Camper",
            "corporation_name": "Astrum Mechanica",
            "alliance_name": "Get Off My Lawn",
            "ship_type": "Loki",
        },
        "total_value": 210000000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800003,
        "time": _mock_time(32),
        "system_id": 30003392,
        "system_name": "BZ-BCK",
        "in_lawn": True,
        "victim": {
            "character_name": "",
            "corporation_name": "",
            "alliance_name": "",
            "ship_type": "Guristas Hideaway",
            "ship_type_id": 0,
        },
        "attacker_count": 1,
        "final_blow": {
            "character_name": "Ratting Alt",
            "corporation_name": "Astrum Mechanica",
            "alliance_name": "Get Off My Lawn",
            "ship_type": "Ishtar",
        },
        "total_value": 0,
        "is_npc": True,
    },
    {
        "killmail_id": 119800004,
        "time": _mock_time(47),
        "system_id": 30003398,
        "system_name": "S-LHPJ",
        "in_lawn": True,
        "victim": {
            "character_name": "LAWN Member",
            "corporation_name": "Astrum Mechanica",
            "alliance_name": "Get Off My Lawn",
            "ship_type": "Vexor Navy Issue",
            "ship_type_id": 29337,
        },
        "attacker_count": 7,
        "final_blow": {
            "character_name": "Bombers Bar FC",
            "corporation_name": "VOLTA",
            "alliance_name": "Dock Workers",
            "ship_type": "Nemesis",
        },
        "total_value": 142000000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800005,
        "time": _mock_time(63),
        "system_id": 30004500,
        "system_name": "LE-67X",
        "in_lawn": False,
        "victim": {
            "character_name": "SL0W Ratter",
            "corporation_name": "SL0W Corp",
            "alliance_name": "SL0W CHILDREN AT PLAY",
            "ship_type": "Dominix",
            "ship_type_id": 645,
        },
        "attacker_count": 5,
        "final_blow": {
            "character_name": "Hostile Roamer",
            "corporation_name": "Fraternity.",
            "alliance_name": "Winter Coalition",
            "ship_type": "Cerberus",
        },
        "total_value": 320000000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800006,
        "time": _mock_time(88),
        "system_id": 30003384,
        "system_name": "1-KCSA",
        "in_lawn": True,
        "victim": {
            "character_name": "Wandering Pilot",
            "corporation_name": "Brave Newbies Inc.",
            "alliance_name": "Brave Collective",
            "ship_type": "Capsule",
            "ship_type_id": 670,
        },
        "attacker_count": 1,
        "final_blow": {
            "character_name": "Home Defense",
            "corporation_name": "Astrum Mechanica",
            "alliance_name": "Get Off My Lawn",
            "ship_type": "Sabre",
        },
        "total_value": 800000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800007,
        "time": _mock_time(112),
        "system_id": 30004501,
        "system_name": "L-GY1B",
        "in_lawn": False,
        "victim": {
            "character_name": "Hauler Alt",
            "corporation_name": "Red Frog Freight",
            "alliance_name": "",
            "ship_type": "Bestower",
            "ship_type_id": 1944,
        },
        "attacker_count": 2,
        "final_blow": {
            "character_name": "Pirate Lord",
            "corporation_name": "The Rejected",
            "alliance_name": "T.RD",
            "ship_type": "Tornado",
        },
        "total_value": 1850000000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800008,
        "time": _mock_time(145),
        "system_id": 30003387,
        "system_name": "F48K-D",
        "in_lawn": True,
        "victim": {
            "character_name": "LAWN Miner",
            "corporation_name": "LAWN Logistics",
            "alliance_name": "Get Off My Lawn",
            "ship_type": "Retriever",
            "ship_type_id": 17478,
        },
        "attacker_count": 3,
        "final_blow": {
            "character_name": "Cloaky Camper",
            "corporation_name": "Pandemic Legion",
            "alliance_name": "Pandemic Legion",
            "ship_type": "Stratios",
        },
        "total_value": 45000000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800009,
        "time": _mock_time(180),
        "system_id": 30003385,
        "system_name": "UDVW-O",
        "in_lawn": True,
        "victim": {
            "character_name": "Vale Roamer",
            "corporation_name": "Northern Coalition.",
            "alliance_name": "Northern Coalition.",
            "ship_type": "Jackdaw",
            "ship_type_id": 37483,
        },
        "attacker_count": 12,
        "final_blow": {
            "character_name": "LAWN FC",
            "corporation_name": "Astrum Mechanica",
            "alliance_name": "Get Off My Lawn",
            "ship_type": "Muninn",
        },
        "total_value": 98000000,
        "is_npc": False,
    },
    {
        "killmail_id": 119800010,
        "time": _mock_time(210),
        "system_id": 30004502,
        "system_name": "74-DRC",
        "in_lawn": False,
        "victim": {
            "character_name": "AFK Cloaker",
            "corporation_name": "Hard Knocks Citizens",
            "alliance_name": "Hard Knocks Inc.",
            "ship_type": "Tengu",
            "ship_type_id": 29984,
        },
        "attacker_count": 4,
        "final_blow": {
            "character_name": "Local Response",
            "corporation_name": "SL0W Corp",
            "alliance_name": "SL0W CHILDREN AT PLAY",
            "ship_type": "Eagle",
        },
        "total_value": 520000000,
        "is_npc": False,
    },
]


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/config")
def api_config():
    return jsonify(MOCK_CONFIG)


@app.route("/api/sovereignty")
def api_sovereignty():
    return jsonify(MOCK_SOVEREIGNTY)


@app.route("/api/activity")
def api_activity():
    return jsonify(MOCK_ACTIVITY)


@app.route("/api/campaigns")
def api_campaigns():
    return jsonify(MOCK_CAMPAIGNS)


@app.route("/api/zkill/feed")
def api_zkill_feed():
    return jsonify(MOCK_KILL_FEED)


@app.route("/api/zkill/<int:system_id>")
def api_zkill(system_id):
    return jsonify([])


@app.route("/api/status")
def api_status():
    return jsonify({"status": "demo_mode", "constellations_monitored": 2, "systems_monitored": 14})


if __name__ == "__main__":
    print("\n[*] ═══ DEMO MODE ═══")
    print("[*] Running with mock data — no ESI connection needed")
    print("[*] Open http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
