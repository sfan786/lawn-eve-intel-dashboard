from concurrent.futures import ThreadPoolExecutor, wait
from flask import Blueprint, jsonify
from config import (
    REGION_ID, FRIENDLY_ALLIANCE_IDS, FRIENDLY_ALLIANCES, FRIENDLY_CORPORATIONS,
    FRIENDLY_STANDING_CORP_IDS, FRIENDLY_STANDING_CORP_NAMES, LAWN_ALLIANCE_ID,
)
import esi_client
from routes.system_state import state

hostile_bp = Blueprint("hostile", __name__)


@hostile_bp.route("/api/intel/active_hostiles")
def api_active_hostiles():
    system_names = {}
    for cdata in state.constellation_data.values():
        for sys_id, sys_info in cdata["systems"].items():
            system_names[sys_id] = sys_info["name"]
    for sys_id, info in state.neighbor_systems.items():
        system_names[sys_id] = info["name"]

    friendly_ids = set(FRIENDLY_ALLIANCE_IDS)
    friendly_alliance_names = {a.lower() for a in FRIENDLY_ALLIANCES}
    friendly_corp_names = {c.lower() for c in FRIENDLY_CORPORATIONS}
    friendly_corp_names |= {c.lower() for c in FRIENDLY_STANDING_CORP_NAMES}
    friendly_corp_ids = set(FRIENDLY_STANDING_CORP_IDS)

    raw_kills = esi_client.get_zkill_region(REGION_ID)
    entity_stats = {}

    # Prefetch killmails in parallel so the sequential loop below hits the cache
    refs = [
        (zk.get("killmail_id"), zk.get("zkb", {}).get("hash"))
        for zk in raw_kills[:30]
        if not zk.get("zkb", {}).get("npc")
    ]
    with ThreadPoolExecutor(max_workers=10) as pool:
        wait([pool.submit(esi_client.get_killmail, k, h) for k, h in refs if k and h])

    for zk in raw_kills[:30]:
        zkb = zk.get("zkb", {})
        if zkb.get("npc"):
            continue
        kill_id = zk.get("killmail_id")
        kill_hash = zkb.get("hash")
        if not kill_id or not kill_hash:
            continue

        try:
            km = esi_client.get_killmail(kill_id, kill_hash)
        except Exception:
            continue

        solar_system_id = km.get("solar_system_id")
        kill_time = km.get("killmail_time", "")
        sys_name = system_names.get(solar_system_id)
        if not sys_name:
            try:
                sys_name = esi_client.get_system_info(solar_system_id).get("name", str(solar_system_id))
            except Exception:
                sys_name = str(solar_system_id)

        in_primary = solar_system_id in state.primary_system_ids
        seen_this_kill = set()

        for att in km.get("attackers", []):
            if not att.get("character_id"):
                continue  # skip NPCs

            alliance_id = att.get("alliance_id")
            corp_id = att.get("corporation_id")

            if alliance_id and (alliance_id in friendly_ids or alliance_id == LAWN_ALLIANCE_ID):
                continue

            entity_id = entity_type = entity_name = None

            if alliance_id:
                try:
                    ainfo = esi_client.get_alliance_info(alliance_id)
                    aname = ainfo.get("name", "")
                    if aname.lower() in friendly_alliance_names:
                        continue
                    entity_id, entity_type, entity_name = alliance_id, "alliance", aname
                except Exception:
                    pass

            if entity_id is None and corp_id:
                if corp_id in friendly_corp_ids:
                    continue
                try:
                    cinfo = esi_client.get_corporation_info(corp_id)
                    cname = cinfo.get("name", "")
                    if cname.lower() in friendly_corp_names:
                        continue
                    entity_id, entity_type, entity_name = corp_id, "corporation", cname
                except Exception:
                    continue

            if not entity_id or not entity_name:
                continue

            key = (entity_id, entity_type)

            # One kill-participation increment per entity per killmail
            if key not in seen_this_kill:
                seen_this_kill.add(key)
                if key not in entity_stats:
                    entity_stats[key] = {
                        "id": entity_id,
                        "name": entity_name,
                        "type": entity_type,
                        "kill_count": 0,
                        "primary_kills": 0,
                        "systems": {},
                        "last_seen": "",
                        "last_seen_system": "",
                        "ship_types": {},
                        "pilots": set(),
                    }
                s = entity_stats[key]
                s["kill_count"] += 1
                if in_primary:
                    s["primary_kills"] += 1
                s["systems"][sys_name] = s["systems"].get(sys_name, 0) + 1
                if not s["last_seen"] or kill_time > s["last_seen"]:
                    s["last_seen"] = kill_time
                    s["last_seen_system"] = sys_name

            # Track ships and pilots per-attacker (not deduplicated per kill)
            s = entity_stats.get(key)
            if s:
                char_id = att.get("character_id")
                if char_id:
                    s["pilots"].add(char_id)
                ship_id = att.get("ship_type_id")
                if ship_id:
                    try:
                        ship_name = esi_client.get_type_name(ship_id)
                        if ship_name:
                            s["ship_types"][ship_name] = s["ship_types"].get(ship_name, 0) + 1
                    except Exception:
                        pass

    result = []
    for s in entity_stats.values():
        top_ships = sorted(s["ship_types"].items(), key=lambda x: x[1], reverse=True)[:5]
        top_systems = sorted(s["systems"].items(), key=lambda x: x[1], reverse=True)[:5]
        result.append({
            "id": s["id"],
            "name": s["name"],
            "type": s["type"],
            "kill_count": s["kill_count"],
            "primary_kills": s["primary_kills"],
            "systems": [{"name": n, "count": c} for n, c in top_systems],
            "last_seen": s["last_seen"],
            "last_seen_system": s["last_seen_system"],
            "ship_types": [{"name": n, "count": c} for n, c in top_ships],
            "pilot_count": len(s["pilots"]),
        })

    result.sort(key=lambda x: (x["primary_kills"], x["kill_count"]), reverse=True)
    return jsonify(result[:15])
