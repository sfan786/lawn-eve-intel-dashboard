from flask import Blueprint, jsonify
from config import REGION_ID
import esi_client
from routes.system_state import state

zkill_bp = Blueprint("zkill", __name__)

# EVE ship group IDs for capital classification
_SUPER_GROUPS = {30, 659}        # Titan, Supercarrier
_CAPITAL_GROUPS = {485, 547, 1538}  # Dreadnought, Carrier, Force Auxiliary
_POD_GROUPS = {29}               # Capsule


def _ship_class(group_id: int) -> str:
    if group_id in _SUPER_GROUPS:
        return "super"
    if group_id in _CAPITAL_GROUPS:
        return "capital"
    if group_id in _POD_GROUPS:
        return "pod"
    return "subcap"


@zkill_bp.route("/api/zkill/<int:system_id>")
def api_zkill(system_id):
    kills = esi_client.get_zkill_system(system_id)
    return jsonify(kills[:20])


@zkill_bp.route("/api/zkill/feed")
def api_zkill_feed():
    system_names = {}
    for cdata in state.constellation_data.values():
        for sys_id, sys_info in cdata["systems"].items():
            system_names[sys_id] = sys_info["name"]
    for sys_id, info in state.neighbor_systems.items():
        system_names[sys_id] = info["name"]

    raw_kills = esi_client.get_zkill_region(REGION_ID)

    feed = []
    for zk in raw_kills[:30]:
        if len(feed) >= 20:
            break

        kill_id = zk.get("killmail_id")
        zkb = zk.get("zkb", {})
        kill_hash = zkb.get("hash")
        if not kill_id or not kill_hash:
            continue

        try:
            km = esi_client.get_killmail(kill_id, kill_hash)
        except Exception:
            continue

        solar_system_id = km.get("solar_system_id")
        victim = km.get("victim", {})
        attackers = km.get("attackers", [])

        sys_name = system_names.get(solar_system_id)
        if not sys_name:
            try:
                sys_info = esi_client.get_system_info(solar_system_id)
                sys_name = sys_info.get("name", str(solar_system_id))
            except Exception:
                sys_name = str(solar_system_id)

        victim_ship = ""
        victim_ship_class = "subcap"
        if victim.get("ship_type_id"):
            victim_ship = esi_client.get_type_name(victim["ship_type_id"])
            victim_ship_class = _ship_class(esi_client.get_type_group_id(victim["ship_type_id"]))

        victim_name = ""
        if victim.get("character_id"):
            victim_name = esi_client.get_character_name(victim["character_id"])

        victim_corp = ""
        victim_alliance = ""
        if victim.get("corporation_id"):
            try:
                cinfo = esi_client.get_corporation_info(victim["corporation_id"])
                victim_corp = cinfo.get("name", "")
            except Exception:
                pass
        if victim.get("alliance_id"):
            try:
                ainfo = esi_client.get_alliance_info(victim["alliance_id"])
                victim_alliance = ainfo.get("name", "")
            except Exception:
                pass

        final_blow = {}
        for att in attackers:
            if att.get("final_blow"):
                fb_ship = ""
                fb_name = ""
                fb_corp = ""
                fb_alliance = ""
                if att.get("ship_type_id"):
                    fb_ship = esi_client.get_type_name(att["ship_type_id"])
                if att.get("character_id"):
                    fb_name = esi_client.get_character_name(att["character_id"])
                if att.get("corporation_id"):
                    try:
                        cinfo = esi_client.get_corporation_info(att["corporation_id"])
                        fb_corp = cinfo.get("name", "")
                    except Exception:
                        pass
                if att.get("alliance_id"):
                    try:
                        ainfo = esi_client.get_alliance_info(att["alliance_id"])
                        fb_alliance = ainfo.get("name", "")
                    except Exception:
                        pass
                final_blow = {
                    "character_name": fb_name,
                    "corporation_name": fb_corp,
                    "alliance_name": fb_alliance,
                    "ship_type": fb_ship,
                }
                break

        fitted_value = zkb.get("fittedValue", 0)

        sorted_attackers = sorted(attackers, key=lambda a: a.get("damage_done", 0), reverse=True)
        top_attackers = []
        for att in sorted_attackers[:4]:
            char_id = att.get("character_id")
            ship_type_id = att.get("ship_type_id")
            if not char_id and not ship_type_id:
                continue
            att_name = ""
            att_ship = ""
            if char_id:
                att_name = esi_client.get_character_name(char_id)
            if ship_type_id:
                att_ship = esi_client.get_type_name(ship_type_id)
            top_attackers.append({
                "character_name": att_name,
                "ship_type": att_ship,
                "damage_done": att.get("damage_done", 0),
                "is_final_blow": att.get("final_blow", False),
            })

        feed.append({
            "killmail_id": kill_id,
            "time": km.get("killmail_time", ""),
            "system_id": solar_system_id,
            "system_name": sys_name,
            "in_primary": solar_system_id in state.primary_system_ids,
            "in_lawn": solar_system_id in state.primary_system_ids,  # legacy alias
            "victim": {
                "character_name": victim_name,
                "corporation_name": victim_corp,
                "alliance_name": victim_alliance,
                "ship_type": victim_ship,
                "ship_type_id": victim.get("ship_type_id"),
                "ship_class": victim_ship_class,
            },
            "attacker_count": len(attackers),
            "final_blow": final_blow,
            "total_value": zkb.get("totalValue", 0),
            "fitted_value": fitted_value,
            "top_attackers": top_attackers,
            "is_npc": zkb.get("npc", False),
        })

    return jsonify(feed)
