from flask import Blueprint, jsonify
from config import (
    ALLIANCE, REGION, DEPLOYMENT_ID,
    FRIENDLY_ALLIANCES, FRIENDLY_CORPORATIONS,
    UPGRADE_TYPES, SYSTEM_UPGRADES, PI_DATA,
    MAP_LAYOUT, MAP_LAYOUT_SUBWAY, MAP_CONNECTIONS,
    PRIMARY_SYSTEMS, BORDER_SYSTEMS,
)
from routes.system_state import state


config_bp = Blueprint("config", __name__)


@config_bp.route("/api/config")
def api_config():
    return jsonify({
        "deployment_id": DEPLOYMENT_ID,
        "alliance": ALLIANCE,
        "region": REGION,
        "constellations": {
            str(cid): {
                "name": data["name"],
                "constellation_id": cid,
                "region_id": data["region_id"],
                "system_ids": list(data["systems"].keys()),
                "systems": data["systems"],
                "is_primary": data.get("is_primary", False),
                "is_lawn": data.get("is_primary", False),  # legacy alias
            }
            for cid, data in state.constellation_data.items()
        },
        "neighbor_systems": {
            str(sys_id): info
            for sys_id, info in state.neighbor_systems.items()
        },
        "primary_constellation_ids": list(state.primary_constellation_ids_set),
        "lawn_constellation_ids": list(state.primary_constellation_ids_set),  # legacy alias
        "primary_systems": PRIMARY_SYSTEMS,
        "border_systems": BORDER_SYSTEMS,
        "friendly_alliances": FRIENDLY_ALLIANCES,
        "friendly_corporations": FRIENDLY_CORPORATIONS,
        "upgrade_types": UPGRADE_TYPES,
        "system_upgrades": SYSTEM_UPGRADES,
        "map_layout": MAP_LAYOUT,
        "map_layout_subway": MAP_LAYOUT_SUBWAY,
        "map_connections": MAP_CONNECTIONS,
    })


@config_bp.route("/api/pi_data")
def api_pi_data():
    return jsonify({
        "pi_data": PI_DATA,
    })


@config_bp.route("/api/status")
def api_status():
    region_systems = sum(len(c["systems"]) for c in state.constellation_data.values())
    primary_systems = len(state.primary_system_ids)
    neighbor_systems = len(state.neighbor_systems)
    return jsonify({
        "status": "online",
        "deployment_id": DEPLOYMENT_ID,
        "alliance": ALLIANCE,
        "region": REGION,
        "constellations_monitored": len(state.constellation_data),
        "systems_monitored": len(state.all_monitored_ids),
        "primary_systems": primary_systems,
        "region_systems": region_systems,
        "neighbor_systems": neighbor_systems,
        "constellation_names": [c["name"] for c in state.constellation_data.values()],
    })
