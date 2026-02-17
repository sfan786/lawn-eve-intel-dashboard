from flask import Blueprint, jsonify
from config import FRIENDLY_ALLIANCES
import esi_client
import db
from routes.system_state import state

sov_bp = Blueprint("sov", __name__)


@sov_bp.route("/api/sovereignty")
def api_sovereignty():
    try:
        sov_map = esi_client.get_sovereignty_map()
    except Exception as e:
        print(f"[!] ESI sovereignty map unavailable: {e}")
        return jsonify({"error": "ESI unavailable"}), 503

    adm_by_system = {}
    vuln_by_system = {}
    try:
        sov_structures = esi_client.get_sovereignty_structures()
        for struct in sov_structures:
            if struct.get("structure_type_id") in [32458, 32876]:
                sys_id = struct.get("solar_system_id")
                adm = struct.get("vulnerability_occupancy_level", 0)
                adm_by_system[sys_id] = adm
                vuln_start = struct.get("vulnerable_start_time")
                vuln_end = struct.get("vulnerable_end_time")
                if vuln_start and vuln_end:
                    vuln_by_system[sys_id] = {
                        "vulnerable_start_time": vuln_start,
                        "vulnerable_end_time": vuln_end,
                    }
    except Exception as e:
        print(f"[!] Failed to fetch sovereignty structures: {e}")

    result = {}
    alliance_cache = {}
    corp_cache = {}

    for entry in sov_map:
        sys_id = entry.get("system_id")
        if sys_id in state.all_monitored_ids:
            alliance_id = entry.get("alliance_id")
            corp_id = entry.get("corporation_id")
            faction_id = entry.get("faction_id")

            alliance_name = None
            corp_name = None

            if alliance_id:
                if alliance_id not in alliance_cache:
                    try:
                        ainfo = esi_client.get_alliance_info(alliance_id)
                        alliance_cache[alliance_id] = ainfo.get("name", f"Alliance {alliance_id}")
                    except Exception:
                        alliance_cache[alliance_id] = f"Alliance {alliance_id}"
                alliance_name = alliance_cache[alliance_id]

            if corp_id:
                if corp_id not in corp_cache:
                    try:
                        cinfo = esi_client.get_corporation_info(corp_id)
                        corp_cache[corp_id] = cinfo.get("name", f"Corp {corp_id}")
                    except Exception:
                        corp_cache[corp_id] = f"Corp {corp_id}"
                corp_name = corp_cache[corp_id]

            is_friendly = alliance_name in FRIENDLY_ALLIANCES if alliance_name else False

            result[sys_id] = {
                "system_id": sys_id,
                "alliance_id": alliance_id,
                "alliance_name": alliance_name,
                "corporation_id": corp_id,
                "corporation_name": corp_name,
                "faction_id": faction_id,
                "is_friendly": is_friendly,
                "adm": adm_by_system.get(sys_id, 0),
            }
            if sys_id in vuln_by_system:
                result[sys_id].update(vuln_by_system[sys_id])

    adm_batch = []
    for sys_id, sys_data in result.items():
        sys_name = state.lookup_system_name(sys_id)
        adm_batch.append((sys_id, sys_name, sys_data["adm"], sys_data.get("alliance_name")))
    db.snapshot_adm_batch(adm_batch)

    return jsonify(result)


@sov_bp.route("/api/campaigns")
def api_campaigns():
    system_names = {}
    all_constellation_ids = set()
    for const_id, cdata in state.constellation_data.items():
        all_constellation_ids.add(const_id)
        for sys_id, sys_info in cdata["systems"].items():
            system_names[sys_id] = sys_info["name"]
    for sys_id, info in state.neighbor_systems.items():
        system_names[sys_id] = info["name"]

    try:
        campaigns = esi_client.get_sovereignty_campaigns()
        structures = esi_client.get_sovereignty_structures()
    except Exception as e:
        print(f"[!] ESI campaign data unavailable: {e}")
        return jsonify({"error": "ESI unavailable"}), 503

    structure_by_id = {s["structure_id"]: s for s in structures}

    enriched = []
    for campaign in campaigns:
        if campaign.get("constellation_id") not in all_constellation_ids:
            continue

        sys_id = campaign.get("solar_system_id")
        struct_id = campaign.get("structure_id")
        struct_data = structure_by_id.get(struct_id, {})
        is_lawn = sys_id in state.lawn_system_ids

        enriched.append({
            **campaign,
            "system_name": system_names.get(sys_id, f"System {sys_id}"),
            "vulnerable_start_time": struct_data.get("vulnerable_start_time"),
            "vulnerable_end_time": struct_data.get("vulnerable_end_time"),
            "structure_type_id": struct_data.get("structure_type_id"),
            "is_lawn": is_lawn,
        })

    return jsonify(enriched)
