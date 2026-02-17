from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, jsonify
from config import NEIGHBOR_ENTITIES
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
