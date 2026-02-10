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

    # Get ADM and vulnerability window data from sovereignty structures
    adm_by_system = {}
    vuln_by_system = {}
    try:
        sov_structures = esi_client.get_sovereignty_structures()
        for struct in sov_structures:
            # Support both old iHub (32458) and new Sov Hub (32876)
            if struct.get("structure_type_id") in [32458, 32876]:
                sys_id = struct.get("solar_system_id")
                adm = struct.get("vulnerability_occupancy_level", 0)
                adm_by_system[sys_id] = adm

                # Extract vulnerability windows
                vuln_start = struct.get("vulnerable_start_time")
                vuln_end = struct.get("vulnerable_end_time")
                if vuln_start and vuln_end:
                    vuln_by_system[sys_id] = {
                        "vulnerable_start_time": vuln_start,
                        "vulnerable_end_time": vuln_end
                    }
    except Exception as e:
        print(f"[!] Failed to fetch sovereignty structures: {e}")

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
                "adm": adm_by_system.get(sys_id, 0),
            }

            # Add vulnerability windows if available
            if sys_id in vuln_by_system:
                result[sys_id].update(vuln_by_system[sys_id])
    
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
    """Get active sovereignty campaigns with enriched data."""
    # Build system name lookup
    system_names = {}
    our_constellation_ids = set()
    for const_id, cdata in CONSTELLATION_DATA.items():
        our_constellation_ids.add(const_id)
        for sys_id, sys_info in cdata["systems"].items():
            system_names[sys_id] = sys_info["name"]

    # Fetch campaigns and structures
    campaigns = esi_client.get_sovereignty_campaigns()
    structures = esi_client.get_sovereignty_structures()
    structure_by_id = {s["structure_id"]: s for s in structures}

    # Filter and enrich
    enriched = []
    for campaign in campaigns:
        if campaign.get("constellation_id") not in our_constellation_ids:
            continue

        sys_id = campaign.get("solar_system_id")
        struct_id = campaign.get("structure_id")
        struct_data = structure_by_id.get(struct_id, {})

        enriched_campaign = {
            **campaign,
            "system_name": system_names.get(sys_id, f"System {sys_id}"),
            "vulnerable_start_time": struct_data.get("vulnerable_start_time"),
            "vulnerable_end_time": struct_data.get("vulnerable_end_time"),
            "structure_type_id": struct_data.get("structure_type_id"),
        }
        enriched.append(enriched_campaign)

    return jsonify(enriched)


@app.route("/api/zkill/<int:system_id>")
def api_zkill(system_id):
    """Get recent zKillboard data for a specific system."""
    kills = esi_client.get_zkill_system(system_id)
    return jsonify(kills[:20])  # Limit to 20 most recent


@app.route("/api/zkill/feed")
def api_zkill_feed():
    """Get enriched kill feed for the region."""
    all_system_ids = set()
    system_names = {}
    for cdata in CONSTELLATION_DATA.values():
        for sys_id, sys_info in cdata["systems"].items():
            all_system_ids.add(sys_id)
            system_names[sys_id] = sys_info["name"]

    # Fetch recent kills from zKillboard for the whole region
    region_id = None
    for cdata in CONSTELLATION_DATA.values():
        region_id = cdata.get("region_id")
        if region_id:
            break

    if not region_id:
        return jsonify([])

    raw_kills = esi_client.get_zkill_region(region_id)

    # Enrich up to 20 kills with ESI killmail data
    feed = []
    for zk in raw_kills[:30]:  # fetch a few extra in case some fail
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

        # Resolve system name
        sys_name = system_names.get(solar_system_id)
        if not sys_name:
            try:
                sys_info = esi_client.get_system_info(solar_system_id)
                sys_name = sys_info.get("name", str(solar_system_id))
            except Exception:
                sys_name = str(solar_system_id)

        # Resolve victim ship type
        victim_ship = ""
        if victim.get("ship_type_id"):
            victim_ship = esi_client.get_type_name(victim["ship_type_id"])

        # Resolve victim name
        victim_name = ""
        if victim.get("character_id"):
            victim_name = esi_client.get_character_name(victim["character_id"])

        # Resolve victim corp/alliance
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

        # Final blow attacker
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

        feed.append({
            "killmail_id": kill_id,
            "time": km.get("killmail_time", ""),
            "system_id": solar_system_id,
            "system_name": sys_name,
            "in_lawn": solar_system_id in all_system_ids,
            "victim": {
                "character_name": victim_name,
                "corporation_name": victim_corp,
                "alliance_name": victim_alliance,
                "ship_type": victim_ship,
                "ship_type_id": victim.get("ship_type_id"),
            },
            "attacker_count": len(attackers),
            "final_blow": final_blow,
            "total_value": zkb.get("totalValue", 0),
            "is_npc": zkb.get("npc", False),
        })

    return jsonify(feed)


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

# Load constellation data at module import time (works with gunicorn)
resolve_constellations()

if __name__ == "__main__":
    print(f"\n[*] Dashboard starting at http://localhost:{FLASK_PORT}")
    print(f"[*] Astrum Mechanica Intel Dashboard - Kalevala Expanse")
    print(f"[*] Monitoring: {', '.join(c['name'] for c in CONSTELLATION_DATA.values())}\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
