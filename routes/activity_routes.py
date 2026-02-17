from flask import Blueprint, jsonify
import esi_client
import db
from routes.system_state import state

activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/api/activity")
def api_activity():
    try:
        kills_data = esi_client.get_system_kills()
        jumps_data = esi_client.get_system_jumps()
    except Exception as e:
        print(f"[!] ESI activity data unavailable: {e}")
        return jsonify({"error": "ESI unavailable"}), 503

    kills_by_system = {entry["system_id"]: entry for entry in kills_data}
    jumps_by_system = {entry["system_id"]: entry for entry in jumps_data}

    result = {}
    for sys_id in state.all_monitored_ids:
        kills = kills_by_system.get(sys_id, {})
        jumps = jumps_by_system.get(sys_id, {})
        result[sys_id] = {
            "system_id": sys_id,
            "ship_kills": kills.get("ship_kills", 0),
            "pod_kills": kills.get("pod_kills", 0),
            "npc_kills": kills.get("npc_kills", 0),
            "jumps": jumps.get("ship_jumps", 0),
        }

    activity_batch = [
        (sid, d["ship_kills"], d["pod_kills"], d["npc_kills"], d["jumps"])
        for sid, d in result.items()
    ]
    db.snapshot_activity_batch(activity_batch)

    return jsonify(result)
