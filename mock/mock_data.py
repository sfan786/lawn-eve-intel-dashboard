"""
Mock data for demo mode.

Builds the demo payloads from the active deployment so demos always show the
right region, alliance, and constellation names. Activity/sov/ADM numbers are
synthesized deterministically per system_id so the demo looks the same on
every refresh — no random jitter that would mask UI regressions.

Switching deployments (DEPLOYMENT=lawn_perrigen → DEPLOYMENT=other) automatically
rebrands the mock without code changes.
"""

from datetime import datetime, timedelta, timezone

import config
from deployments import ACTIVE as DEPLOYMENT


_constellations_by_id = {}      # cid -> {name, system_ids}
_systems_by_name = {}           # name -> {system_id, constellation_id, security}
_systems_by_id = {}             # sid -> {name, constellation_id, security}

for cid, cdata in (
    {c["constellation_id"]: c for c in []}  # filled below
).items():
    pass

# Walk the deployment's MAP_LAYOUT to build a stable system list. We don't have
# real ESI system_ids here without ESI calls, so we mint deterministic ones from
# the layout key (hashed) — they only need to be unique inside the demo.
def _mint_id(name):
    h = 0
    for ch in name:
        h = (h * 31 + ord(ch)) & 0x7fffffff
    return 30000000 + (h % 9999999)


_const_to_systems = {}
for name, pos in DEPLOYMENT.MAP_LAYOUT.items():
    is_neighbor = pos.get("constellation") == "neighbor"
    cname = pos.get("constellation") or ""
    sid = _mint_id(name)
    _systems_by_name[name] = {
        "system_id": sid,
        "constellation_name": cname,
        "is_neighbor": is_neighbor,
        "is_primary": bool(pos.get("lawn")),
        "region_note": pos.get("note"),
        "security": -0.3 - (sid % 50) / 100.0,
    }
    _systems_by_id[sid] = _systems_by_name[name]
    if not is_neighbor:
        _const_to_systems.setdefault(cname, []).append(name)


# Build constellation entries. Real constellation IDs from the deployment for
# primary; minted IDs for the rest of the region.
_primary_const_names = set(getattr(DEPLOYMENT, "PRIMARY_CONSTELLATION_NAMES", []))
_primary_const_ids = list(DEPLOYMENT.PRIMARY_CONSTELLATION_IDS)

# Map primary constellation name → real constellation id (assumes parallel order
# of PRIMARY_CONSTELLATION_NAMES and PRIMARY_CONSTELLATION_IDS, which the
# bootstrap tool guarantees).
_primary_name_to_cid = dict(zip(
    getattr(DEPLOYMENT, "PRIMARY_CONSTELLATION_NAMES", []),
    DEPLOYMENT.PRIMARY_CONSTELLATION_IDS,
))


def _const_id(cname):
    if cname in _primary_name_to_cid:
        return _primary_name_to_cid[cname]
    # Synthesize an ID from the constellation name for non-primary constellations.
    return 21000000 + (_mint_id(cname) % 999999)


_constellation_objs = {}
for cname, sys_names in _const_to_systems.items():
    cid = _const_id(cname)
    is_primary = cname in _primary_const_names
    systems = {}
    for sn in sorted(sys_names):
        meta = _systems_by_name[sn]
        systems[str(meta["system_id"])] = {
            "name": sn,
            "security_status": round(meta["security"], 2),
            "system_id": meta["system_id"],
        }
    _constellation_objs[str(cid)] = {
        "name": cname,
        "constellation_id": cid,
        "region_id": DEPLOYMENT.REGION["id"],
        "system_ids": [s["system_id"] for s in systems.values()],
        "systems": systems,
        "is_primary": is_primary,
        "is_lawn": is_primary,  # legacy alias
    }


# Neighbour systems (extracted from MAP_LAYOUT entries with constellation="neighbor")
_neighbour_objs = {}
for name, meta in _systems_by_name.items():
    if not meta["is_neighbor"]:
        continue
    sid = meta["system_id"]
    _neighbour_objs[str(sid)] = {
        "name": name,
        "system_id": sid,
        "security_status": round(meta["security"], 2),
        "region_name": meta["region_note"] or "Unknown",
    }


MOCK_CONFIG = {
    "deployment_id": DEPLOYMENT.DEPLOYMENT_ID + "-demo",
    "alliance": DEPLOYMENT.ALLIANCE,
    "region": DEPLOYMENT.REGION,
    "constellations": _constellation_objs,
    "neighbor_systems": _neighbour_objs,
    "primary_constellation_ids": _primary_const_ids,
    "lawn_constellation_ids": _primary_const_ids,  # legacy alias
    "primary_systems": list(DEPLOYMENT.PRIMARY_SYSTEMS),
    "border_systems": list(DEPLOYMENT.BORDER_SYSTEMS),
    "friendly_alliances": list(DEPLOYMENT.FRIENDLY_ALLIANCES),
    "friendly_corporations": list(DEPLOYMENT.FRIENDLY_CORPORATIONS),
    "upgrade_types": config.UPGRADE_TYPES,
    "system_upgrades": DEPLOYMENT.SYSTEM_UPGRADES,
    "map_layout": DEPLOYMENT.MAP_LAYOUT,
    "map_layout_subway": DEPLOYMENT.MAP_LAYOUT_SUBWAY,
    "map_connections": DEPLOYMENT.MAP_CONNECTIONS,
}


# ============ Sovereignty (synthesized) ============

_PRIMARY_ALLIANCE_NAME = DEPLOYMENT.ALLIANCE["name"]
_PRIMARY_TICKER = DEPLOYMENT.ALLIANCE.get("ticker") or DEPLOYMENT.ALLIANCE.get("short_name") or "PRIMARY"
_FIRST_FRIENDLY_CORP = (DEPLOYMENT.FRIENDLY_CORPORATIONS or [_PRIMARY_TICKER])[0]
_HOSTILE_NAMES = [n.get("name") for n in DEPLOYMENT.NEIGHBOR_ENTITIES] or ["Hostile Alliance"]


def _build_sovereignty():
    """Synthesize per-system sov data. Primary systems are held by the active
    alliance with low ADM (so the dashboard's grinding warnings demo well);
    other region systems are sprinkled with the threat alliances from the
    deployment config; neighbours are unowned."""
    sov = {}
    primary_set = set(DEPLOYMENT.PRIMARY_SYSTEMS)

    for sid, meta in _systems_by_id.items():
        if meta["is_neighbor"]:
            continue
        name = next(n for n, m in _systems_by_name.items() if m["system_id"] == sid)
        if name in primary_set:
            adm = round(1.0 + (sid % 25) / 10.0, 1)  # 1.0..3.5
            sov[str(sid)] = {
                "system_id": sid,
                "alliance_name": _PRIMARY_ALLIANCE_NAME,
                "corporation_name": _FIRST_FRIENDLY_CORP,
                "is_friendly": True,
                "adm": adm,
            }
        else:
            holder = _HOSTILE_NAMES[sid % len(_HOSTILE_NAMES)]
            adm = round(2.0 + (sid % 35) / 10.0, 1)  # 2.0..5.5
            sov[str(sid)] = {
                "system_id": sid,
                "alliance_name": holder,
                "corporation_name": f"{holder} Corp",
                "is_friendly": False,
                "adm": adm,
            }
    return sov


MOCK_SOVEREIGNTY = _build_sovereignty()


def _get_vuln_duration(adm):
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


def build_enriched_sovereignty():
    now = datetime.utcnow()
    base_vuln_start = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if base_vuln_start < now:
        base_vuln_start += timedelta(days=1)

    enriched = {}
    for sys_id, sov_data in MOCK_SOVEREIGNTY.items():
        adm = sov_data.get("adm", 0)
        vuln_hours = _get_vuln_duration(adm)
        vuln_end = base_vuln_start + timedelta(hours=vuln_hours)
        enriched[sys_id] = {
            **sov_data,
            "vulnerable_start_time": base_vuln_start.isoformat() + "Z",
            "vulnerable_end_time": vuln_end.isoformat() + "Z",
        }
    return enriched


# ============ Activity (synthesized) ============

def _build_activity():
    activity = {}
    primary_set = set(DEPLOYMENT.PRIMARY_SYSTEMS)
    border_set = set(DEPLOYMENT.BORDER_SYSTEMS)

    for sid, meta in _systems_by_id.items():
        name = next(n for n, m in _systems_by_name.items() if m["system_id"] == sid)
        if meta["is_neighbor"]:
            ship_kills = (sid % 4 == 0) and 1 or 0
            npc_kills = sid % 90
            jumps = (sid % 20) + 2
        elif name in border_set:
            ship_kills = 1 + (sid % 5)
            npc_kills = (sid % 200) + 100
            jumps = (sid % 50) + 30
        elif name in primary_set:
            ship_kills = sid % 3
            npc_kills = (sid % 350) + 100
            jumps = (sid % 30) + 10
        else:
            ship_kills = 0
            npc_kills = sid % 50
            jumps = sid % 8
        activity[str(sid)] = {
            "system_id": sid,
            "ship_kills": ship_kills,
            "pod_kills": ship_kills // 3,
            "npc_kills": npc_kills,
            "jumps": jumps,
        }
    return activity


MOCK_ACTIVITY = _build_activity()


# ============ Campaigns ============

def get_mock_campaigns():
    """Two campaigns, one in each primary constellation, to exercise the alert
    panel. Falls back to single campaign in the first primary system when only
    one constellation is configured."""
    now = datetime.utcnow()
    reffed_time = now + timedelta(hours=28)
    nodes_time = now - timedelta(hours=2)
    vuln_start = now.replace(hour=16, minute=0, second=0, microsecond=0)
    if vuln_start < now:
        vuln_start += timedelta(days=1)
    vuln_end = vuln_start + timedelta(hours=6, minutes=30)

    primary_systems = list(DEPLOYMENT.PRIMARY_SYSTEMS)
    if not primary_systems:
        return []

    target = primary_systems[0]
    target_meta = _systems_by_name[target]
    target_cname = target_meta["constellation_name"]
    second = primary_systems[len(primary_systems) // 2] if len(primary_systems) > 1 else target
    second_meta = _systems_by_name[second]

    return [
        {
            "campaign_id": 999001,
            "solar_system_id": target_meta["system_id"],
            "system_name": target,
            "constellation_id": _const_id(target_cname),
            "event_type": "ihub_defense",
            "structure_id": 1051234567890,
            "structure_type_id": 32876,
            "start_time": reffed_time.isoformat() + "Z",
            "attackers_score": 0.4, "defender_score": 0.6,
            "vulnerable_start_time": vuln_start.isoformat() + "Z",
            "vulnerable_end_time": vuln_end.isoformat() + "Z",
            "is_primary": True,
            "is_lawn": True,
        },
        {
            "campaign_id": 999002,
            "solar_system_id": second_meta["system_id"],
            "system_name": second,
            "constellation_id": _const_id(second_meta["constellation_name"]),
            "event_type": "tcu_defense",
            "structure_id": 1051234567891,
            "structure_type_id": 32876,
            "start_time": nodes_time.isoformat() + "Z",
            "attackers_score": 0.35, "defender_score": 0.65,
            "vulnerable_start_time": vuln_start.isoformat() + "Z",
            "vulnerable_end_time": vuln_end.isoformat() + "Z",
            "is_primary": True,
            "is_lawn": True,
        },
    ]


# ============ Kill Feed ============

def _mock_time(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_kill_feed():
    """Six representative kills across the active deployment's primary systems
    plus one neighbour kill for variety. Enough to demo the kill-feed UI."""
    primary = list(DEPLOYMENT.PRIMARY_SYSTEMS)
    if not primary:
        return []
    border = list(DEPLOYMENT.BORDER_SYSTEMS) or primary[:1]
    hostile = _HOSTILE_NAMES[0]

    def sys(name):
        meta = _systems_by_name.get(name)
        if not meta:
            meta = _systems_by_name[primary[0]]
        return meta["system_id"], name

    # Pick canonical demo systems with safe fallbacks
    s_border0, n_border0 = sys(border[0])
    s_p1, n_p1 = sys(primary[len(primary) // 3])
    s_p2, n_p2 = sys(primary[len(primary) // 2])
    s_p3, n_p3 = sys(primary[(len(primary) * 2) // 3])
    s_p4, n_p4 = sys(primary[-1])

    return [
        {
            "killmail_id": 119800001, "time": _mock_time(8),
            "system_id": s_border0, "system_name": n_border0,
            "in_primary": True, "in_lawn": True,
            "victim": {"character_name": "Hostile Scout", "corporation_name": "Pandemic Horde Inc.", "alliance_name": "Pandemic Horde", "ship_type": "Sabre", "ship_type_id": 22456, "ship_class": "subcap"},
            "attacker_count": 3,
            "final_blow": {"character_name": f"{_PRIMARY_TICKER} Defender", "corporation_name": _FIRST_FRIENDLY_CORP, "alliance_name": _PRIMARY_ALLIANCE_NAME, "ship_type": "Stiletto"},
            "total_value": 85000000, "fitted_value": 64000000, "is_npc": False,
            "top_attackers": [
                {"character_name": f"{_PRIMARY_TICKER} Defender", "ship_type": "Stiletto", "damage_done": 5420, "is_final_blow": True},
                {"character_name": "Tackle Alt", "ship_type": "Malediction", "damage_done": 3180, "is_final_blow": False},
            ],
        },
        {
            "killmail_id": 119800002, "time": _mock_time(15),
            "system_id": s_p1, "system_name": n_p1,
            "in_primary": True, "in_lawn": True,
            "victim": {"character_name": "Wandering Pilot", "corporation_name": "Brave Newbies Inc.", "alliance_name": "Brave Collective", "ship_type": "Astero", "ship_type_id": 33468, "ship_class": "subcap"},
            "attacker_count": 1,
            "final_blow": {"character_name": "Gate Camper", "corporation_name": _FIRST_FRIENDLY_CORP, "alliance_name": _PRIMARY_ALLIANCE_NAME, "ship_type": "Loki"},
            "total_value": 210000000, "fitted_value": 165000000, "is_npc": False,
            "top_attackers": [
                {"character_name": "Gate Camper", "ship_type": "Loki", "damage_done": 8840, "is_final_blow": True},
            ],
        },
        {
            "killmail_id": 119800003, "time": _mock_time(32),
            "system_id": s_p2, "system_name": n_p2,
            "in_primary": True, "in_lawn": True,
            "victim": {"character_name": "", "corporation_name": "", "alliance_name": "", "ship_type": "Guristas Hideaway", "ship_type_id": 0, "ship_class": "subcap"},
            "attacker_count": 1,
            "final_blow": {"character_name": "Ratting Alt", "corporation_name": _FIRST_FRIENDLY_CORP, "alliance_name": _PRIMARY_ALLIANCE_NAME, "ship_type": "Ishtar"},
            "total_value": 0, "fitted_value": 0, "is_npc": True,
            "top_attackers": [
                {"character_name": "Ratting Alt", "ship_type": "Ishtar", "damage_done": 15000, "is_final_blow": True},
            ],
        },
        {
            "killmail_id": 119800004, "time": _mock_time(47),
            "system_id": s_p3, "system_name": n_p3,
            "in_primary": True, "in_lawn": True,
            "victim": {"character_name": f"{_PRIMARY_TICKER} Member", "corporation_name": _FIRST_FRIENDLY_CORP, "alliance_name": _PRIMARY_ALLIANCE_NAME, "ship_type": "Vexor Navy Issue", "ship_type_id": 29337, "ship_class": "subcap"},
            "attacker_count": 7,
            "final_blow": {"character_name": "Bombers Bar FC", "corporation_name": "VOLTA", "alliance_name": "Dock Workers", "ship_type": "Nemesis"},
            "total_value": 142000000, "fitted_value": 105000000, "is_npc": False,
            "top_attackers": [
                {"character_name": "Bombers Bar FC", "ship_type": "Nemesis", "damage_done": 9800, "is_final_blow": True},
                {"character_name": "Stealth Pilot", "ship_type": "Purifier", "damage_done": 7600, "is_final_blow": False},
            ],
        },
        {
            "killmail_id": 119800005, "time": _mock_time(112),
            "system_id": s_p4, "system_name": n_p4,
            "in_primary": True, "in_lawn": True,
            "victim": {"character_name": "Hauler Alt", "corporation_name": "Red Frog Freight", "alliance_name": "", "ship_type": "Bestower", "ship_type_id": 1944, "ship_class": "subcap"},
            "attacker_count": 2,
            "final_blow": {"character_name": "Pirate Lord", "corporation_name": "Pirate Inc", "alliance_name": hostile, "ship_type": "Tornado"},
            "total_value": 1850000000, "fitted_value": 1580000000, "is_npc": False,
            "top_attackers": [
                {"character_name": "Pirate Lord", "ship_type": "Tornado", "damage_done": 22100, "is_final_blow": True},
            ],
        },
        {
            "killmail_id": 119800006, "time": _mock_time(255),
            "system_id": s_p1, "system_name": n_p1,
            "in_primary": True, "in_lawn": True,
            "victim": {"character_name": "Hostile Capital Pilot", "corporation_name": "Hostile Corp", "alliance_name": hostile, "ship_type": "Naglfar", "ship_type_id": 19720, "ship_class": "capital"},
            "attacker_count": 38,
            "final_blow": {"character_name": f"{_PRIMARY_TICKER} FC", "corporation_name": _FIRST_FRIENDLY_CORP, "alliance_name": _PRIMARY_ALLIANCE_NAME, "ship_type": "Revelation"},
            "total_value": 8200000000, "fitted_value": 6240000000, "is_npc": False,
            "top_attackers": [
                {"character_name": f"{_PRIMARY_TICKER} FC", "ship_type": "Revelation", "damage_done": 142000, "is_final_blow": True},
                {"character_name": "Dread Pilot Alpha", "ship_type": "Phoenix", "damage_done": 118000, "is_final_blow": False},
            ],
        },
    ]


MOCK_KILL_FEED = _build_kill_feed()


# ============ ADM History ============

def generate_mock_adm_history():
    """7-day per-system trend that ramps up gently with a small wobble. Used by
    the ADM trends sparklines so the demo has something to plot."""
    now = datetime.utcnow()
    history = {}
    for name in DEPLOYMENT.PRIMARY_SYSTEMS:
        meta = _systems_by_name.get(name)
        if not meta:
            continue
        sid = meta["system_id"]
        sov_data = MOCK_SOVEREIGNTY.get(str(sid))
        if not sov_data:
            continue
        current_adm = sov_data["adm"]
        start_adm = max(0.3, current_adm - 1.8)
        points = []
        for hours_ago in range(168, -1, -4):
            t = now - timedelta(hours=hours_ago)
            progress = 1.0 - (hours_ago / 168.0)
            adm = start_adm + (current_adm - start_adm) * (progress ** 0.7)
            wobble = ((sid * 7 + hours_ago * 3) % 17 - 8) * 0.005
            adm = round(max(0.1, min(6.0, adm + wobble)), 2)
            points.append({"adm": adm, "timestamp": t.strftime("%Y-%m-%dT%H:%M:%SZ")})
        if points:
            points[-1]["adm"] = current_adm
        history[sid] = {"system_name": name, "history": points}
    return history


# ============ Neighbor Intel (mock) ============

def _build_neighbor_intel():
    """One entry per NEIGHBOR_ENTITIES in the deployment, with deterministic
    threat levels and a token activity heatmap."""
    intel = []
    samples = [
        {"threat_level": "Medium", "kills": 23, "ships": [("Sabre", 8), ("Muninn", 5), ("Loki", 4), ("Stiletto", 3)],
         "heatmap": [0, 0, 1, 2, 1, 0, 0, 0, 1, 3, 4, 5, 4, 3, 2, 1, 2, 3, 4, 5, 4, 3, 2, 1]},
        {"threat_level": "Low", "kills": 7, "ships": [("Ishtar", 3), ("Drake", 2), ("Vexor Navy Issue", 2)],
         "heatmap": [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2, 2, 1, 1, 0, 0, 0, 1, 2, 2, 1, 0, 0, 0]},
        {"threat_level": "Low", "kills": 4, "ships": [("Tornado", 2), ("Stratios", 2)],
         "heatmap": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0]},
    ]
    for i, ent in enumerate(DEPLOYMENT.NEIGHBOR_ENTITIES):
        sample = samples[i % len(samples)]
        intel.append({
            "id": ent["id"],
            "name": ent["name"],
            "type": ent.get("type", "alliance"),
            "threat_level": sample["threat_level"],
            "total_kills_24h": sample["kills"],
            "top_ships": [{"name": n, "count": c} for n, c in sample["ships"]],
            "activity_heatmap": sample["heatmap"],
        })
    return intel


MOCK_NEIGHBOR_INTEL = _build_neighbor_intel()


# ============ Regional Intel (mock) ============

def _build_regional_intel():
    """Simulate hourly ESI kills/jumps for the neighbor systems grouped by region."""
    region_samples = {
        "Malpais":        {"threat": "high",     "sys_data": [("DYS-CG", 12, 1, 80, 55), ("HD-JVQ", 5, 1, 20, 22), ("IF-KD1", 1, 0, 45, 8)]},
        "Etherium Reach": {"threat": "elevated",  "sys_data": [("9S-GPT", 3, 0, 30, 18)]},
        "Oasa":           {"threat": "elevated",  "sys_data": [("EU-WFW", 2, 1, 15, 14), ("L-EUY2", 0, 0, 90, 5)]},
        "The Spire":      {"threat": "quiet",     "sys_data": [("MTGF-2", 0, 0, 12, 3), ("O8W-5O", 1, 0, 8, 6)]},
        "Outer Passage":  {"threat": "quiet",     "sys_data": [("OTJ9-E", 0, 0, 5, 2)]},
        "Venal":          {"threat": "quiet",     "sys_data": [("QE2-FS", 0, 0, 3, 1), ("QZ1-OH", 0, 0, 7, 2)]},
    }

    def sys_threat(ship_kills, jumps):
        if ship_kills >= 10 or jumps >= 50:
            return "high"
        if ship_kills >= 3 or jumps >= 20:
            return "elevated"
        return "quiet"

    tier_order = {"high": 0, "elevated": 1, "quiet": 2}
    regions = []
    for region_name, info in region_samples.items():
        systems = []
        total_kills = 0
        total_jumps = 0
        for name, sk, pk, npc, jmp in info["sys_data"]:
            systems.append({
                "system_id": 0,
                "name": name,
                "ship_kills": sk,
                "pod_kills": pk,
                "npc_kills": npc,
                "jumps": jmp,
                "threat": sys_threat(sk, jmp),
            })
            total_kills += sk
            total_jumps += jmp
        systems.sort(key=lambda s: s["ship_kills"], reverse=True)
        regions.append({
            "name": region_name,
            "threat": info["threat"],
            "total_kills": total_kills,
            "total_jumps": total_jumps,
            "systems": systems,
        })

    regions.sort(key=lambda r: (tier_order.get(r["threat"], 9), r["name"]))
    return {"regions": regions}


MOCK_REGIONAL_INTEL = _build_regional_intel()
