from flask import Blueprint, jsonify
from config import (
    FRIENDLY_ALLIANCES, FRIENDLY_CORPORATIONS,
    UPGRADE_TYPES, SYSTEM_UPGRADES, PI_DATA
)
from routes.system_state import state


config_bp = Blueprint("config", __name__)


@config_bp.route("/api/config")
def api_config():
    return jsonify({
        "constellations": {
            str(cid): {
                "name": data["name"],
                "constellation_id": cid,
                "region_id": data["region_id"],
                "system_ids": list(data["systems"].keys()),
                "systems": data["systems"],
                "is_lawn": data.get("is_lawn", False),
            }
            for cid, data in state.constellation_data.items()
        },
        "neighbor_systems": {
            str(sys_id): info
            for sys_id, info in state.neighbor_systems.items()
        },
        "lawn_constellation_ids": list(state.lawn_constellation_ids_set),
        "friendly_alliances": FRIENDLY_ALLIANCES,
        "friendly_corporations": FRIENDLY_CORPORATIONS,
        "upgrade_types": UPGRADE_TYPES,
        "system_upgrades": SYSTEM_UPGRADES,
    })


@config_bp.route("/api/pi_data")
def api_pi_data():
    return jsonify({
        "pi_data": PI_DATA,
    })


@config_bp.route("/api/status")
def api_status():
    tke_systems = sum(len(c["systems"]) for c in state.constellation_data.values())
    lawn_systems = len(state.lawn_system_ids)
    neighbor_systems = len(state.neighbor_systems)
    return jsonify({
        "status": "online",
        "constellations_monitored": len(state.constellation_data),
        "systems_monitored": len(state.all_monitored_ids),
        "lawn_systems": lawn_systems,
        "tke_systems": tke_systems,
        "neighbor_systems": neighbor_systems,
        "constellation_names": [c["name"] for c in state.constellation_data.values()],
    })
