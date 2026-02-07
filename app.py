"""
EVE Intel Dashboard - Flask Backend
Astrum Mechanica / Get Off My Lawn
Kalevala Expanse Constellation Monitor

Usage:
    pip install flask requests
    python app.py
    Open http://localhost:5000
"""

from flask import Flask, jsonify, send_from_directory
from config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    MONITORED_CONSTELLATION_IDS, FRIENDLY_ALLIANCES,
    FRIENDLY_CORPORATIONS
)
import esi_client

app = Flask(__name__)

# Resolved constellation data (populated on startup)
CONSTELLATION_DATA = {}


def resolve_constellations():
    """Load constellation data from ESI using constellation IDs."""
    global CONSTELLATION_DATA
    print("[*] Loading monitored constellations...")

    for cid in MONITORED_CONSTELLATION_IDS:
        try:
            info = esi_client.get_constellation_info(cid)
            systems = {}
            for sys_id in info.get("systems", []):
                sys_info = esi_client.get_system_info(sys_id)
                systems[sys_id] = {
                    "name": sys_info.get("name", str(sys_id)),
                    "security_status": round(sys_info.get("security_status", 0), 2),
                    "system_id": sys_id,
                }

            CONSTELLATION_DATA[cid] = {
                "constellation_id": cid,
                "name": info.get("name", str(cid)),
                "region_id": info.get("region_id"),
                "systems": systems,
            }
            print(f"  [+] {info.get('name')} (ID: {cid}) -> {len(systems)} systems")
        except Exception as e:
            print(f"  [!] Error loading constellation {cid}: {e}")

    print(f"[*] Monitoring {len(CONSTELLATION_DATA)} constellations, "
          f"{sum(len(c['systems']) for c in CONSTELLATION_DATA.values())} systems total")


# ============ API Routes ============

@app.route("/")
def index():
    """Serve the React SPA."""
    return send_from_directory("static", "index.html")


@app.route("/api/config")
def api_config():
    """Return dashboard configuration."""
    return jsonify({
        "constellations": {
            str(cid): {
                "name": data["name"],
                "constellation_id": cid,
                "region_id": data["region_id"],
                "system_ids": list(data["systems"].keys()),
                "systems": data["systems"],
            }
            for cid, data in CONSTELLATION_DATA.items()
        },
        "friendly_alliances": FRIENDLY_ALLIANCES,
        "friendly_corporations": FRIENDLY_CORPORATIONS,
    })


@app.route("/api/sovereignty")
def api_sovereignty():
    """Get sovereignty data for monitored systems."""
    all_system_ids = set()
    for cdata in CONSTELLATION_DATA.values():
        all_system_ids.update(cdata["systems"].keys())
    
    sov_map = esi_client.get_sovereignty_map()
    
    # Filter to our systems and resolve alliance names
    result = {}
    alliance_cache = {}
    corp_cache = {}
    
    for entry in sov_map:
        sys_id = entry.get("system_id")
        if sys_id in all_system_ids:
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
            }
    
    return jsonify(result)


@app.route("/api/activity")
def api_activity():
    """Get kill and jump activity for monitored systems."""
    all_system_ids = set()
    for cdata in CONSTELLATION_DATA.values():
        all_system_ids.update(cdata["systems"].keys())
    
    kills_data = esi_client.get_system_kills()
    jumps_data = esi_client.get_system_jumps()
    
    # Index by system_id
    kills_by_system = {
        entry["system_id"]: entry for entry in kills_data
    }
    jumps_by_system = {
        entry["system_id"]: entry for entry in jumps_data
    }
    
    result = {}
    for sys_id in all_system_ids:
        kills = kills_by_system.get(sys_id, {})
        jumps = jumps_by_system.get(sys_id, {})
        
        result[sys_id] = {
            "system_id": sys_id,
            "ship_kills": kills.get("ship_kills", 0),
            "pod_kills": kills.get("pod_kills", 0),
            "npc_kills": kills.get("npc_kills", 0),
            "jumps": jumps.get("ship_jumps", 0),
        }
    
    return jsonify(result)


@app.route("/api/campaigns")
def api_campaigns():
    """Get active sovereignty campaigns in our systems."""
    all_system_ids = set()
    for cdata in CONSTELLATION_DATA.values():
        all_system_ids.update(cdata["systems"].keys())
    
    campaigns = esi_client.get_sovereignty_campaigns()
    
    # Filter to our constellation IDs
    our_constellation_ids = set(CONSTELLATION_DATA.keys())
    relevant = []
    
    for campaign in campaigns:
        if campaign.get("constellation_id") in our_constellation_ids:
            relevant.append(campaign)
    
    return jsonify(relevant)


@app.route("/api/zkill/<int:system_id>")
def api_zkill(system_id):
    """Get recent zKillboard data for a specific system."""
    kills = esi_client.get_zkill_system(system_id)
    return jsonify(kills[:20])  # Limit to 20 most recent


@app.route("/api/status")
def api_status():
    """Health check / status endpoint."""
    total_systems = sum(len(c["systems"]) for c in CONSTELLATION_DATA.values())
    return jsonify({
        "status": "online",
        "constellations_monitored": len(CONSTELLATION_DATA),
        "systems_monitored": total_systems,
        "constellation_names": [c["name"] for c in CONSTELLATION_DATA.values()],
    })


# ============ Startup ============

if __name__ == "__main__":
    resolve_constellations()
    print(f"\n[*] Dashboard starting at http://localhost:{FLASK_PORT}")
    print(f"[*] Astrum Mechanica Intel Dashboard - Kalevala Expanse")
    print(f"[*] Monitoring: {', '.join(c['name'] for c in CONSTELLATION_DATA.values())}\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
