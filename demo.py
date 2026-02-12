"""
Demo mode - Run the dashboard with mock data for UI testing.
Usage: python demo.py
"""

from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request, send_from_directory

app = Flask(__name__)

# ============ System ID assignments (matching MAP_LAYOUT in index.html) ============
# LAWN systems keep their original IDs; TKE + neighbors use sequential mock IDs

# LAWN 6-CBBM
_LAWN_6CBBM = {
    "1-KCSA": 30003384, "UDVW-O": 30003385, "UJXC-B": 30003386,
    "F48K-D": 30003387, "JT2I-7": 30003388, "XTJ-5Q": 30003389, "N-JK02": 30003390,
}
# LAWN 2Q-8WA
_LAWN_2Q8WA = {
    "FB5U-I": 30003391, "BZ-BCK": 30003392, "J-OAH2": 30003393,
    "O5-YNW": 30003394, "86L-9F": 30003395, "5-VFC6": 30003396,
    "IUU3-L": 30003397, "S-LHPJ": 30003398,
}
# S4S-SD (7 systems)
_S4S_SD = {
    "LE-67X": 30003400, "L-GY1B": 30003401, "74-DRC": 30003402,
    "0S1-GI": 30003403, "M3-H2Y": 30003404, "O31W-6": 30003405, "B1UE-J": 30003406,
}
# 3NA-Z1 (7 systems)
_3NA_Z1 = {
    "EPCD-D": 30003410, "L-TLFU": 30003411, "BM-VYZ": 30003412,
    "MN9P-A": 30003413, "RAI-0E": 30003414, "TA9T-P": 30003415, "Q-GICU": 30003416,
}
# 78-6RI (6 systems)
_78_6RI = {
    "6V-D0E": 30003420, "LS3-HP": 30003421, "QX-4HO": 30003422,
    "BVRQ-O": 30003423, "SH6X-F": 30003424, "FBH-JN": 30003425,
}
# U-HSM3 (8 systems)
_U_HSM3 = {
    "HPV-RJ": 30003430, "C3J0-O": 30003431, "WNM-V0": 30003432,
    "6FS-CZ": 30003433, "H7S-5I": 30003434, "GSO-SR": 30003435,
    "G-KCFT": 30003436, "B3ZU-H": 30003437,
}
# 2O-VY7 (6 systems)
_2O_VY7 = {
    "A-YB15": 30003440, "SG-3HY": 30003441, "QZX-L9": 30003442,
    "D-6PKO": 30003443, "AU2V-J": 30003444, "SY-0AM": 30003445,
}
# 8UD2-J (7 systems)
_8UD2_J = {
    "G4-QU6": 30003450, "V2-GZS": 30003451, "42G-OB": 30003452,
    "1S-SU1": 30003453, "LEM-I1": 30003454, "HD-HOZ": 30003455, "ND-GL4": 30003456,
}
# XPG-HE (6 systems)
_XPG_HE = {
    "K95-9I": 30003460, "M-75WN": 30003461, "9-0QB7": 30003462,
    "PNFW-O": 30003463, "K76A-3": 30003464, "HVGR-R": 30003465,
}
# P-B2NE (7 systems)
_P_B2NE = {
    "R1O-GN": 30003470, "RQOO-U": 30003471, "I2D3-5": 30003472,
    "BGMZ-0": 30003473, "GQ-7SP": 30003474, "FZX-PU": 30003475, "O9K-FT": 30003476,
}

# Neighbor systems
_NEIGHBORS = {
    # Vale of the Silent
    "PX5-LR": 30003500, "A3-RQ3": 30003501, "9-GBPD": 30003502, "LS-JEP": 30003503,
    # Geminate
    "9-KWXC": 30003510, "HJO-84": 30003511, "P-E9GN": 30003512,
    "4D9-66": 30003513, "L-TOFR": 30003514, "Q-TBHW": 30003515, "9P4O-F": 30003516,
    # Etherium Reach
    "AID-9T": 30003520, "TZ-74M": 30003521, "FB-MPY": 30003522, "J7M-3W": 30003523,
    # Malpais
    "V3P-AZ": 30003530, "7-YHRX": 30003531, "Z-EKCY": 30003532,
}

LAWN_CONSTELLATION_IDS = [20000490, 20000491]


def _make_systems(name_id_map, base_sec=-0.5):
    """Build systems dict from name->id mapping."""
    systems = {}
    for i, (name, sid) in enumerate(name_id_map.items()):
        sec = round(base_sec - (i * 0.08) % 0.5, 2)
        systems[str(sid)] = {"name": name, "security_status": sec, "system_id": sid}
    return systems


# ============ Mock Config ============
MOCK_CONFIG = {
    "constellations": {
        "20000490": {
            "name": "6-CBBM", "constellation_id": 20000490, "region_id": 10000034,
            "system_ids": list(_LAWN_6CBBM.values()),
            "systems": _make_systems(_LAWN_6CBBM, -0.08),
            "is_lawn": True,
        },
        "20000491": {
            "name": "2Q-8WA", "constellation_id": 20000491, "region_id": 10000034,
            "system_ids": list(_LAWN_2Q8WA.values()),
            "systems": _make_systems(_LAWN_2Q8WA, -0.32),
            "is_lawn": True,
        },
        "20000492": {
            "name": "S4S-SD", "constellation_id": 20000492, "region_id": 10000034,
            "system_ids": list(_S4S_SD.values()),
            "systems": _make_systems(_S4S_SD, -0.25),
            "is_lawn": False,
        },
        "20000493": {
            "name": "3NA-Z1", "constellation_id": 20000493, "region_id": 10000034,
            "system_ids": list(_3NA_Z1.values()),
            "systems": _make_systems(_3NA_Z1, -0.30),
            "is_lawn": False,
        },
        "20000494": {
            "name": "78-6RI", "constellation_id": 20000494, "region_id": 10000034,
            "system_ids": list(_78_6RI.values()),
            "systems": _make_systems(_78_6RI, -0.45),
            "is_lawn": False,
        },
        "20000495": {
            "name": "U-HSM3", "constellation_id": 20000495, "region_id": 10000034,
            "system_ids": list(_U_HSM3.values()),
            "systems": _make_systems(_U_HSM3, -0.55),
            "is_lawn": False,
        },
        "20000496": {
            "name": "2O-VY7", "constellation_id": 20000496, "region_id": 10000034,
            "system_ids": list(_2O_VY7.values()),
            "systems": _make_systems(_2O_VY7, -0.60),
            "is_lawn": False,
        },
        "20000497": {
            "name": "8UD2-J", "constellation_id": 20000497, "region_id": 10000034,
            "system_ids": list(_8UD2_J.values()),
            "systems": _make_systems(_8UD2_J, -0.35),
            "is_lawn": False,
        },
        "20000498": {
            "name": "XPG-HE", "constellation_id": 20000498, "region_id": 10000034,
            "system_ids": list(_XPG_HE.values()),
            "systems": _make_systems(_XPG_HE, -0.40),
            "is_lawn": False,
        },
        "20000499": {
            "name": "P-B2NE", "constellation_id": 20000499, "region_id": 10000034,
            "system_ids": list(_P_B2NE.values()),
            "systems": _make_systems(_P_B2NE, -0.50),
            "is_lawn": False,
        },
    },
    "neighbor_systems": {
        str(sid): {
            "name": name, "system_id": sid, "security_status": -0.4,
            "region_name": (
                "Vale of the Silent" if name in ["PX5-LR", "A3-RQ3", "9-GBPD", "LS-JEP"] else
                "Geminate" if name in ["9-KWXC", "HJO-84", "P-E9GN", "4D9-66", "L-TOFR", "Q-TBHW", "9P4O-F"] else
                "Etherium Reach" if name in ["AID-9T", "TZ-74M", "FB-MPY", "J7M-3W"] else
                "Malpais"
            ),
        }
        for name, sid in _NEIGHBORS.items()
    },
    "lawn_constellation_ids": LAWN_CONSTELLATION_IDS,
    "friendly_alliances": ["Get Off My Lawn"],
    "friendly_corporations": ["Astrum Mechanica"],
}


# ============ Sovereignty Data ============
# Sov holders per constellation, matching CLAUDE.md game situation

def _build_sovereignty():
    sov = {}

    # LAWN systems — all LAWN, brand new claims (realistic decimal ADMs)
    lawn_adms = {
        "1-KCSA": 2.5, "UDVW-O": 1.6, "UJXC-B": 1.2, "F48K-D": 2.1,
        "JT2I-7": 1.4, "XTJ-5Q": 1.9, "N-JK02": 1.3,
        "FB5U-I": 2.3, "BZ-BCK": 1.8, "J-OAH2": 1.1, "O5-YNW": 2.7,
        "86L-9F": 1.5, "5-VFC6": 1.7, "IUU3-L": 1.4, "S-LHPJ": 2.0,
    }
    lawn_corps = ["Astrum Mechanica", "LAWN Logistics"]
    for i, (name, sid) in enumerate({**_LAWN_6CBBM, **_LAWN_2Q8WA}.items()):
        sov[str(sid)] = {
            "system_id": sid, "alliance_name": "Get Off My Lawn",
            "corporation_name": lawn_corps[i % 2], "is_friendly": True,
            "adm": lawn_adms.get(name, 1.5),
        }

    # S4S-SD — SL0W remnant sov (ADM 4), except contested L-GY1B
    for name, sid in _S4S_SD.items():
        sov[str(sid)] = {
            "system_id": sid, "alliance_name": "SL0W CHILDREN AT PLAY",
            "corporation_name": "SL0W Corp", "is_friendly": False,
            "adm": 4.0,
        }
    # L-GY1B is the gateway — lower ADM, being contested
    sov[str(_S4S_SD["L-GY1B"])]["adm"] = 3.2

    # 3NA-Z1 — mix: EPCD-D and L-TLFU are T.RD (ADM 0-1), rest SL0W remnant
    trd_systems = {"EPCD-D", "L-TLFU"}
    for name, sid in _3NA_Z1.items():
        if name in trd_systems:
            sov[str(sid)] = {
                "system_id": sid, "alliance_name": "T.RD",
                "corporation_name": "The Rejected", "is_friendly": False,
                "adm": 0.8 if name == "EPCD-D" else 0.5,
            }
        else:
            sov[str(sid)] = {
                "system_id": sid, "alliance_name": "SL0W CHILDREN AT PLAY",
                "corporation_name": "SL0W Corp", "is_friendly": False,
                "adm": 3.8,
            }

    # 78-6RI — SL0W remnant, slightly decayed
    for name, sid in _78_6RI.items():
        sov[str(sid)] = {
            "system_id": sid, "alliance_name": "SL0W CHILDREN AT PLAY",
            "corporation_name": "SL0W Corp", "is_friendly": False,
            "adm": 3.5,
        }

    # U-HSM3 — FRIES holds C3J0-O and B3ZU-H, rest unclaimed/SL0W
    fries_systems = {"C3J0-O", "B3ZU-H"}
    for name, sid in _U_HSM3.items():
        if name in fries_systems:
            sov[str(sid)] = {
                "system_id": sid, "alliance_name": "FRIES",
                "corporation_name": "FRIES Corp", "is_friendly": False,
                "adm": 3.0,
            }
        else:
            sov[str(sid)] = {
                "system_id": sid, "alliance_name": "SL0W CHILDREN AT PLAY",
                "corporation_name": "SL0W Corp", "is_friendly": False,
                "adm": 2.5,
            }

    # 2O-VY7 — BIGAB pocket (SG-3HY, QZX-L9, AU2V-J, SY-0AM), rest unclaimed
    bigab_systems = {"SG-3HY", "QZX-L9", "AU2V-J", "SY-0AM"}
    for name, sid in _2O_VY7.items():
        if name in bigab_systems:
            sov[str(sid)] = {
                "system_id": sid, "alliance_name": "BIGAB",
                "corporation_name": "BIGAB Holdings", "is_friendly": False,
                "adm": 2.0,
            }
        else:
            # Unclaimed — no sov entry (won't appear in sov data)
            pass

    # 8UD2-J — mostly empty, SL0W remnant decayed
    for name, sid in _8UD2_J.items():
        sov[str(sid)] = {
            "system_id": sid, "alliance_name": "SL0W CHILDREN AT PLAY",
            "corporation_name": "SL0W Corp", "is_friendly": False,
            "adm": 2.0,
        }

    # XPG-HE — unclaimed except K95-9I (T.RD outpost)
    sov[str(_XPG_HE["K95-9I"])] = {
        "system_id": _XPG_HE["K95-9I"], "alliance_name": "T.RD",
        "corporation_name": "The Rejected", "is_friendly": False, "adm": 0.3,
    }

    # P-B2NE — all unclaimed (no sov entries)

    # Neighbors — no sov entries (they're outside TKE, sov data for different regions)

    return sov


MOCK_SOVEREIGNTY = _build_sovereignty()


# ============ Activity Data ============

def _build_activity():
    activity = {}

    # LAWN — active ratting + some PVP on border systems
    lawn_activity = {
        "1-KCSA": (2, 0, 420, 38), "UDVW-O": (0, 0, 185, 12), "UJXC-B": (0, 0, 230, 15),
        "F48K-D": (1, 0, 310, 48), "JT2I-7": (0, 0, 95, 7), "XTJ-5Q": (5, 2, 540, 67),
        "N-JK02": (3, 1, 370, 52),
        "FB5U-I": (0, 0, 480, 22), "BZ-BCK": (1, 0, 650, 31), "J-OAH2": (0, 0, 390, 14),
        "O5-YNW": (0, 0, 720, 18), "86L-9F": (0, 0, 260, 9), "5-VFC6": (0, 0, 150, 8),
        "IUU3-L": (0, 0, 340, 11), "S-LHPJ": (2, 1, 510, 35),
    }
    for name, sid in {**_LAWN_6CBBM, **_LAWN_2Q8WA}.items():
        sk, pk, nk, j = lawn_activity.get(name, (0, 0, 0, 0))
        activity[str(sid)] = {"system_id": sid, "ship_kills": sk, "pod_kills": pk, "npc_kills": nk, "jumps": j}

    # S4S-SD — SL0W remnant: mostly dead, some transit
    s4s_act = {
        "LE-67X": (0, 0, 15, 3), "L-GY1B": (1, 0, 45, 28), "74-DRC": (0, 0, 30, 8),
        "0S1-GI": (0, 0, 20, 5), "M3-H2Y": (0, 0, 5, 2), "O31W-6": (0, 0, 10, 6),
        "B1UE-J": (0, 0, 8, 4),
    }
    for name, sid in _S4S_SD.items():
        sk, pk, nk, j = s4s_act.get(name, (0, 0, 0, 0))
        activity[str(sid)] = {"system_id": sid, "ship_kills": sk, "pod_kills": pk, "npc_kills": nk, "jumps": j}

    # 3NA-Z1 — T.RD systems: tiny activity; SL0W remnant: low
    for name, sid in _3NA_Z1.items():
        if name in {"EPCD-D", "L-TLFU"}:
            activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 12, "jumps": 2}
        else:
            activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 25, "jumps": 4}

    # 78-6RI — SL0W remnant, quiet
    for name, sid in _78_6RI.items():
        activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 18, "jumps": 3}

    # U-HSM3 — FRIES systems have moderate activity
    for name, sid in _U_HSM3.items():
        if name in {"C3J0-O", "B3ZU-H"}:
            activity[str(sid)] = {"system_id": sid, "ship_kills": 1, "pod_kills": 0, "npc_kills": 280, "jumps": 15}
        else:
            activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 35, "jumps": 5}

    # 2O-VY7 — BIGAB moderate activity
    for name, sid in _2O_VY7.items():
        if name in {"SG-3HY", "QZX-L9", "AU2V-J", "SY-0AM"}:
            activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 190, "jumps": 12}
        else:
            activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 0, "jumps": 1}

    # 8UD2-J — near-dead SL0W space
    for name, sid in _8UD2_J.items():
        activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 8, "jumps": 2}

    # XPG-HE — mostly empty
    for name, sid in _XPG_HE.items():
        activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 5, "jumps": 1}

    # P-B2NE — empty
    for name, sid in _P_B2NE.items():
        activity[str(sid)] = {"system_id": sid, "ship_kills": 0, "pod_kills": 0, "npc_kills": 0, "jumps": 0}

    # Neighbors — varied activity
    neighbor_act = {
        "LS-JEP": (2, 0, 40, 45), "A3-RQ3": (0, 0, 30, 20), "9-GBPD": (0, 0, 50, 15),
        "PX5-LR": (0, 0, 20, 10),
        "9-KWXC": (0, 0, 65, 8), "HJO-84": (0, 0, 45, 6), "P-E9GN": (1, 0, 80, 12),
        "4D9-66": (0, 0, 35, 5), "L-TOFR": (0, 0, 55, 9), "Q-TBHW": (0, 0, 25, 4),
        "9P4O-F": (0, 0, 30, 3),
        "AID-9T": (0, 0, 70, 18), "TZ-74M": (0, 0, 15, 3), "FB-MPY": (0, 0, 10, 2),
        "J7M-3W": (0, 0, 20, 4),
        "V3P-AZ": (1, 0, 120, 22), "7-YHRX": (0, 0, 95, 16), "Z-EKCY": (0, 0, 60, 8),
    }
    for name, sid in _NEIGHBORS.items():
        sk, pk, nk, j = neighbor_act.get(name, (0, 0, 0, 0))
        activity[str(sid)] = {"system_id": sid, "ship_kills": sk, "pod_kills": pk, "npc_kills": nk, "jumps": j}

    return activity


MOCK_ACTIVITY = _build_activity()


# ============ Mock Campaigns ============

def get_mock_campaigns():
    """Generate mock campaign data — including one non-LAWN regional campaign."""
    now = datetime.utcnow()

    # Real ESI: start_time is when nodes spawn. 
    # Scores default to 0.4/0.6 for Sov Hubs even when reinforced.
    
    # Reinforced structure (nodes in future)
    reffed_time = now + timedelta(hours=28) 
    
    # Active nodes (nodes spawned in the past)
    nodes_time = now - timedelta(hours=2)

    vuln_start = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if vuln_start < now:
        vuln_start += timedelta(days=1)
    vuln_end = vuln_start + timedelta(hours=6, minutes=30)

    return [
        {
            "campaign_id": 999001,
            "solar_system_id": 30003384,  # 1-KCSA
            "system_name": "1-KCSA",
            "constellation_id": 20000490,
            "event_type": "ihub_defense",
            "structure_id": 1051234567890,
            "structure_type_id": 32876,
            "start_time": reffed_time.isoformat() + "Z",
            "attackers_score": 0.4,
            "defender_score": 0.6,
            "vulnerable_start_time": vuln_start.isoformat() + "Z",
            "vulnerable_end_time": vuln_end.isoformat() + "Z",
            "is_lawn": True,
        },
        {
            "campaign_id": 999002,
            "solar_system_id": 30003387,  # F48K-D
            "system_name": "F48K-D",
            "constellation_id": 20000490,
            "event_type": "tcu_defense",
            "structure_id": 1051234567891,
            "structure_type_id": 32876,
            "start_time": nodes_time.isoformat() + "Z",
            "attackers_score": 0.35,
            "defender_score": 0.65,
            "vulnerable_start_time": vuln_start.isoformat() + "Z",
            "vulnerable_end_time": vuln_end.isoformat() + "Z",
            "is_lawn": True,
        },
        {
            "campaign_id": 999003,
            "solar_system_id": _S4S_SD["LE-67X"],  # LE-67X — non-LAWN regional campaign
            "system_name": "LE-67X",
            "constellation_id": 20000492,
            "event_type": "ihub_defense",
            "structure_id": 1051234567892,
            "structure_type_id": 32876,
            "start_time": (now - timedelta(hours=6)).isoformat() + "Z",
            "attackers_score": 0.0,
            "defender_score": 0.0,
            "vulnerable_start_time": vuln_start.isoformat() + "Z",
            "vulnerable_end_time": vuln_end.isoformat() + "Z",
            "is_lawn": False,
        },
    ]


# ============ Mock Kill Feed ============

def _mock_time(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")

MOCK_KILL_FEED = [
    {
        "killmail_id": 119800001, "time": _mock_time(8),
        "system_id": 30003389, "system_name": "XTJ-5Q", "in_lawn": True,
        "victim": {"character_name": "xXDarkSlayerXx", "corporation_name": "Pandemic Horde Inc.", "alliance_name": "Pandemic Horde", "ship_type": "Sabre", "ship_type_id": 22456},
        "attacker_count": 3,
        "final_blow": {"character_name": "LAWN Defender", "corporation_name": "Astrum Mechanica", "alliance_name": "Get Off My Lawn", "ship_type": "Stiletto"},
        "total_value": 85000000, "is_npc": False,
    },
    {
        "killmail_id": 119800002, "time": _mock_time(15),
        "system_id": 30003390, "system_name": "N-JK02", "in_lawn": True,
        "victim": {"character_name": "Scout McScoutface", "corporation_name": "Signal Cartel", "alliance_name": "EvE-Scout Enclave", "ship_type": "Astero", "ship_type_id": 33468},
        "attacker_count": 1,
        "final_blow": {"character_name": "Gate Camper", "corporation_name": "Astrum Mechanica", "alliance_name": "Get Off My Lawn", "ship_type": "Loki"},
        "total_value": 210000000, "is_npc": False,
    },
    {
        "killmail_id": 119800003, "time": _mock_time(32),
        "system_id": 30003392, "system_name": "BZ-BCK", "in_lawn": True,
        "victim": {"character_name": "", "corporation_name": "", "alliance_name": "", "ship_type": "Guristas Hideaway", "ship_type_id": 0},
        "attacker_count": 1,
        "final_blow": {"character_name": "Ratting Alt", "corporation_name": "Astrum Mechanica", "alliance_name": "Get Off My Lawn", "ship_type": "Ishtar"},
        "total_value": 0, "is_npc": True,
    },
    {
        "killmail_id": 119800004, "time": _mock_time(47),
        "system_id": 30003398, "system_name": "S-LHPJ", "in_lawn": True,
        "victim": {"character_name": "LAWN Member", "corporation_name": "Astrum Mechanica", "alliance_name": "Get Off My Lawn", "ship_type": "Vexor Navy Issue", "ship_type_id": 29337},
        "attacker_count": 7,
        "final_blow": {"character_name": "Bombers Bar FC", "corporation_name": "VOLTA", "alliance_name": "Dock Workers", "ship_type": "Nemesis"},
        "total_value": 142000000, "is_npc": False,
    },
    {
        "killmail_id": 119800005, "time": _mock_time(63),
        "system_id": _S4S_SD["LE-67X"], "system_name": "LE-67X", "in_lawn": False,
        "victim": {"character_name": "SL0W Ratter", "corporation_name": "SL0W Corp", "alliance_name": "SL0W CHILDREN AT PLAY", "ship_type": "Dominix", "ship_type_id": 645},
        "attacker_count": 5,
        "final_blow": {"character_name": "Hostile Roamer", "corporation_name": "Fraternity.", "alliance_name": "Winter Coalition", "ship_type": "Cerberus"},
        "total_value": 320000000, "is_npc": False,
    },
    {
        "killmail_id": 119800006, "time": _mock_time(88),
        "system_id": 30003384, "system_name": "1-KCSA", "in_lawn": True,
        "victim": {"character_name": "Wandering Pilot", "corporation_name": "Brave Newbies Inc.", "alliance_name": "Brave Collective", "ship_type": "Capsule", "ship_type_id": 670},
        "attacker_count": 1,
        "final_blow": {"character_name": "Home Defense", "corporation_name": "Astrum Mechanica", "alliance_name": "Get Off My Lawn", "ship_type": "Sabre"},
        "total_value": 800000, "is_npc": False,
    },
    {
        "killmail_id": 119800007, "time": _mock_time(112),
        "system_id": _S4S_SD["L-GY1B"], "system_name": "L-GY1B", "in_lawn": False,
        "victim": {"character_name": "Hauler Alt", "corporation_name": "Red Frog Freight", "alliance_name": "", "ship_type": "Bestower", "ship_type_id": 1944},
        "attacker_count": 2,
        "final_blow": {"character_name": "Pirate Lord", "corporation_name": "The Rejected", "alliance_name": "T.RD", "ship_type": "Tornado"},
        "total_value": 1850000000, "is_npc": False,
    },
    {
        "killmail_id": 119800008, "time": _mock_time(145),
        "system_id": 30003387, "system_name": "F48K-D", "in_lawn": True,
        "victim": {"character_name": "LAWN Miner", "corporation_name": "LAWN Logistics", "alliance_name": "Get Off My Lawn", "ship_type": "Retriever", "ship_type_id": 17478},
        "attacker_count": 3,
        "final_blow": {"character_name": "Cloaky Camper", "corporation_name": "Pandemic Legion", "alliance_name": "Pandemic Legion", "ship_type": "Stratios"},
        "total_value": 45000000, "is_npc": False,
    },
    {
        "killmail_id": 119800009, "time": _mock_time(180),
        "system_id": 30003385, "system_name": "UDVW-O", "in_lawn": True,
        "victim": {"character_name": "Vale Roamer", "corporation_name": "Northern Coalition.", "alliance_name": "Northern Coalition.", "ship_type": "Jackdaw", "ship_type_id": 37483},
        "attacker_count": 12,
        "final_blow": {"character_name": "LAWN FC", "corporation_name": "Astrum Mechanica", "alliance_name": "Get Off My Lawn", "ship_type": "Muninn"},
        "total_value": 98000000, "is_npc": False,
    },
    {
        "killmail_id": 119800010, "time": _mock_time(210),
        "system_id": _S4S_SD["74-DRC"], "system_name": "74-DRC", "in_lawn": False,
        "victim": {"character_name": "AFK Cloaker", "corporation_name": "Hard Knocks Citizens", "alliance_name": "Hard Knocks Inc.", "ship_type": "Tengu", "ship_type_id": 29984},
        "attacker_count": 4,
        "final_blow": {"character_name": "Local Response", "corporation_name": "SL0W Corp", "alliance_name": "SL0W CHILDREN AT PLAY", "ship_type": "Eagle"},
        "total_value": 520000000, "is_npc": False,
    },
]


# ============ ADM History ============

def _generate_mock_adm_history():
    """Generate 7 days of mock ADM history for LAWN systems only."""
    now = datetime.utcnow()
    history = {}

    # Only generate history for LAWN systems (matching frontend ADM Trends scope)
    lawn_systems = {**_LAWN_6CBBM, **_LAWN_2Q8WA}
    for name, sys_id in lawn_systems.items():
        sov_data = MOCK_SOVEREIGNTY.get(str(sys_id))
        if not sov_data:
            continue
        current_adm = sov_data["adm"]
        start_adm = max(0.3, current_adm - 1.8)
        points = []
        for hours_ago in range(168, -1, -4):
            t = now - timedelta(hours=hours_ago)
            progress = 1.0 - (hours_ago / 168.0)
            adm = start_adm + (current_adm - start_adm) * (progress ** 0.7)
            wobble = ((sys_id * 7 + hours_ago * 3) % 17 - 8) * 0.005
            adm = round(max(0.1, min(6.0, adm + wobble)), 2)
            points.append({"adm": adm, "timestamp": t.strftime("%Y-%m-%dT%H:%M:%SZ")})
        if points:
            points[-1]["adm"] = current_adm
        history[sys_id] = {"system_name": name, "history": points}

    return history


# ============ Sovereignty with vulnerability windows ============

def _enrich_sovereignty():
    """Add vulnerability windows to sovereignty data."""
    def get_vuln_duration(adm):
        if adm <= 0:
            return 18
        breakpoints = [(1.0, 18.0), (2.0, 10.0), (3.0, 6.0), (4.0, 4.0), (5.0, 3.0), (6.0, 2.0)]
        if adm >= 6.0:
            return 2.0
        for i in range(len(breakpoints) - 1):
            adm_low, hours_low = breakpoints[i]
            adm_high, hours_high = breakpoints[i + 1]
            if adm_low <= adm <= adm_high:
                ratio = (adm - adm_low) / (adm_high - adm_low)
                return hours_low + ratio * (hours_high - hours_low)
        return 18.0

    now = datetime.utcnow()
    base_vuln_start = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if base_vuln_start < now:
        base_vuln_start += timedelta(days=1)

    enriched_sov = {}
    for sys_id, sov_data in MOCK_SOVEREIGNTY.items():
        adm = sov_data.get("adm", 0)
        vuln_hours = get_vuln_duration(adm)
        vuln_end = base_vuln_start + timedelta(hours=vuln_hours)
        enriched_sov[sys_id] = {
            **sov_data,
            "vulnerable_start_time": base_vuln_start.isoformat() + "Z",
            "vulnerable_end_time": vuln_end.isoformat() + "Z",
        }
    return enriched_sov


# ============ Flask Routes ============

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/config")
def api_config():
    return jsonify(MOCK_CONFIG)


@app.route("/api/sovereignty")
def api_sovereignty():
    return jsonify(_enrich_sovereignty())


@app.route("/api/activity")
def api_activity():
    return jsonify(MOCK_ACTIVITY)


@app.route("/api/campaigns")
def api_campaigns():
    return jsonify(get_mock_campaigns())


@app.route("/api/history/adm")
def api_history_adm():
    return jsonify(_generate_mock_adm_history())


@app.route("/api/zkill/feed")
def api_zkill_feed():
    return jsonify(MOCK_KILL_FEED)


@app.route("/api/zkill/<int:system_id>")
def api_zkill(system_id):
    return jsonify([])


@app.route("/api/status")
def api_status():
    tke = sum(len(c["systems"]) for c in MOCK_CONFIG["constellations"].values())
    lawn = sum(len(c["systems"]) for c in MOCK_CONFIG["constellations"].values() if c.get("is_lawn"))
    neighbor = len(MOCK_CONFIG["neighbor_systems"])
    return jsonify({
        "status": "demo_mode",
        "constellations_monitored": len(MOCK_CONFIG["constellations"]),
        "systems_monitored": tke + neighbor,
        "lawn_systems": lawn,
        "tke_systems": tke,
        "neighbor_systems": neighbor,
    })


if __name__ == "__main__":
    print("\n[*] \u2550\u2550\u2550 DEMO MODE \u2550\u2550\u2550")
    print("[*] Running with mock data \u2014 no ESI connection needed")
    print(f"[*] {len(MOCK_CONFIG['constellations'])} constellations, "
          f"{sum(len(c['systems']) for c in MOCK_CONFIG['constellations'].values())} TKE + "
          f"{len(MOCK_CONFIG['neighbor_systems'])} neighbors")
    print("[*] Open http://localhost:5000\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
