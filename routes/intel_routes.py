from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, jsonify, request
from config import NEIGHBOR_ENTITIES, LAWN_ALLIANCE_ID, FRIENDLY_ALLIANCE_IDS, FRIENDLY_CORPORATIONS
import esi_client

intel_bp = Blueprint("intel", __name__)


@intel_bp.route("/api/intel/neighbors")
def api_neighbor_intel():
    results = []

    for entity in NEIGHBOR_ENTITIES:
        eid = entity["id"]
        etype = entity["type"]
        name = entity["name"]

        if etype == "alliance":
            kills = esi_client.get_zkill_alliance(eid)
        else:
            kills = esi_client.get_zkill_corporation(eid)

        ship_counts = {}
        hourly_activity = {h: 0 for h in range(24)}
        total_kills = len(kills)
        recent_kills = kills[:50]

        with ThreadPoolExecutor(max_workers=20) as pool:
            future_to_kill = {
                pool.submit(esi_client.get_killmail, k.get("killmail_id"), k.get("zkb", {}).get("hash")): k
                for k in recent_kills
                if k.get("killmail_id") and k.get("zkb", {}).get("hash")
            }
            for future in as_completed(future_to_kill):
                try:
                    full_kill = future.result()
                    if not full_kill:
                        continue
                    victim = full_kill.get("victim", {})
                    ship_type_id = victim.get("ship_type_id")
                    if ship_type_id:
                        ship_name = esi_client.get_type_name(ship_type_id)
                        ship_counts[ship_name] = ship_counts.get(ship_name, 0) + 1
                    kill_time_str = full_kill.get("killmail_time")
                    if kill_time_str:
                        try:
                            hour = int(kill_time_str[11:13])
                            hourly_activity[hour] += 1
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Error processing killmail: {e}")

        top_ships = sorted(ship_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        resolved_top_ships = [
            {"name": esi_client.get_type_name(tid), "count": count}
            for tid, count in top_ships
        ]

        score_val = total_kills
        if score_val > 50:
            threat_level = "High"
        elif score_val > 10:
            threat_level = "Medium"
        else:
            threat_level = "Low"

        results.append({
            "id": eid,
            "name": name,
            "type": etype,
            "threat_level": threat_level,
            "total_kills_24h": total_kills,
            "top_ships": resolved_top_ships,
            "activity_heatmap": [hourly_activity[h] for h in range(24)],
        })

    return jsonify(results)


@intel_bp.route("/api/local/scan", methods=["POST"])
def api_local_scan():
    names = request.json.get("names", [])[:100]
    if not names:
        return jsonify([])

    # 1. Bulk resolve names → character IDs
    try:
        resolved = esi_client.post_universe_ids(names)
    except Exception as e:
        return jsonify({"error": f"ESI name resolution failed: {e}"}), 502

    char_map = {c["name"]: c["id"] for c in resolved.get("characters", [])}
    name_set = set(names)
    unresolved = [n for n in name_set if n not in char_map]

    # 2. Bulk get affiliations
    char_ids = list(char_map.values())
    affil_by_id = {}
    if char_ids:
        try:
            affiliations = esi_client.bulk_character_affiliations(char_ids)
            for a in affiliations:
                affil_by_id[a["character_id"]] = a
        except Exception as e:
            print(f"Affiliation lookup failed: {e}")

    # 3. Build results
    results = []

    for name, char_id in char_map.items():
        affil = affil_by_id.get(char_id, {})
        corp_id = affil.get("corporation_id")
        alliance_id = affil.get("alliance_id")

        corp_name = None
        alliance_name = None
        if corp_id:
            try:
                corp_name = esi_client.get_corporation_info(corp_id).get("name")
            except Exception:
                pass
        if alliance_id:
            try:
                alliance_name = esi_client.get_alliance_info(alliance_id).get("name")
            except Exception:
                pass

        # Classify standing — alliance first, corp name as fallback
        if alliance_id == LAWN_ALLIANCE_ID:
            standing = "lawn"
        elif corp_name in FRIENDLY_CORPORATIONS:
            standing = "lawn"  # LAWN member corp, possibly without alliance tag set
        elif alliance_id in FRIENDLY_ALLIANCE_IDS:
            standing = "friendly"
        else:
            standing = "unknown"

        results.append({
            "name": name,
            "character_id": char_id,
            "corporation_name": corp_name,
            "alliance_name": alliance_name,
            "standing": standing,
        })

    for name in unresolved:
        results.append({
            "name": name,
            "character_id": None,
            "corporation_name": None,
            "alliance_name": None,
            "standing": "unresolved",
        })

    # Sort: unknown first, then friendly, then lawn, then unresolved
    order = {"unknown": 0, "friendly": 1, "lawn": 2, "unresolved": 3}
    results.sort(key=lambda r: order.get(r["standing"], 99))

    return jsonify(results)
