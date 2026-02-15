"""
EVE Intel Dashboard - Flask Backend
Get Off My Lawn [LAWN] — Kalevala Expanse

Usage:
    pip install flask requests
    python app.py
    Open http://localhost:5000
"""

from flask import Flask, jsonify, request, send_from_directory
from config import (
    FLASK_HOST, FLASK_PORT, FLASK_DEBUG,
    LAWN_CONSTELLATION_IDS, FRIENDLY_ALLIANCES,
    FRIENDLY_CORPORATIONS, REGION_ID, NEIGHBOR_SYSTEM_NAMES,
    TIMER_PASSWORD, NEIGHBOR_ENTITIES
)
import esi_client
import db

app = Flask(__name__)

# ============ Data Structures (populated on startup) ============

# All TKE constellations (10 total, including LAWN's 2)
CONSTELLATION_DATA = {}

# Neighbor systems outside TKE {sys_id: {name, region_name, system_id, security_status}}
NEIGHBOR_SYSTEMS = {}

# Quick lookup sets
LAWN_CONSTELLATION_IDS_SET = set()
LAWN_SYSTEM_IDS = set()
ALL_MONITORED_IDS = set()  # All ~87 system IDs (TKE + neighbors)


def resolve_all_systems():
    """Load all TKE constellations + neighbor systems from ESI."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time as _time

    global CONSTELLATION_DATA, NEIGHBOR_SYSTEMS
    global LAWN_CONSTELLATION_IDS_SET, LAWN_SYSTEM_IDS, ALL_MONITORED_IDS

    t_start = _time.monotonic()
    LAWN_CONSTELLATION_IDS_SET = set(LAWN_CONSTELLATION_IDS)

    # 1. Get all constellation IDs for The Kalevala Expanse
    print(f"[*] Loading region {REGION_ID} (The Kalevala Expanse)...")
    try:
        region_info = esi_client.get_region_info(REGION_ID)
        tke_constellation_ids = region_info.get("constellations", [])
        print(f"  [+] Region has {len(tke_constellation_ids)} constellations")
    except Exception as e:
        print(f"  [!] Failed to load region info: {e}")
        print(f"  [*] Falling back to LAWN constellations only")
        tke_constellation_ids = LAWN_CONSTELLATION_IDS

    # 2. Fetch all constellation info in parallel
    print(f"[*] Resolving {len(tke_constellation_ids)} TKE constellations...")
    constellation_infos = {}  # cid -> info dict
    with ThreadPoolExecutor(max_workers=10) as pool:
        future_to_cid = {
            pool.submit(esi_client.get_constellation_info, cid): cid
            for cid in tke_constellation_ids
        }
        for future in as_completed(future_to_cid):
            cid = future_to_cid[future]
            try:
                constellation_infos[cid] = future.result()
            except Exception as e:
                print(f"  [!] Error loading constellation {cid}: {e}")

    # 3. Collect all system IDs, then fetch all system info in parallel
    all_system_ids = []
    for cid, info in constellation_infos.items():
        for sys_id in info.get("systems", []):
            all_system_ids.append((cid, sys_id))

    print(f"[*] Resolving {len(all_system_ids)} TKE systems...")
    system_infos = {}  # sys_id -> info dict
    with ThreadPoolExecutor(max_workers=20) as pool:
        future_to_sid = {
            pool.submit(esi_client.get_system_info, sys_id): sys_id
            for _, sys_id in all_system_ids
        }
        for future in as_completed(future_to_sid):
            sys_id = future_to_sid[future]
            try:
                system_infos[sys_id] = future.result()
            except Exception as e:
                print(f"  [!] Error loading system {sys_id}: {e}")

    # 4. Build CONSTELLATION_DATA from fetched results
    for cid, info in constellation_infos.items():
        systems = {}
        for sys_id in info.get("systems", []):
            if sys_id in system_infos:
                si = system_infos[sys_id]
                systems[sys_id] = {
                    "name": si.get("name", str(sys_id)),
                    "security_status": round(si.get("security_status", 0), 2),
                    "system_id": sys_id,
                }

        is_lawn = cid in LAWN_CONSTELLATION_IDS_SET
        CONSTELLATION_DATA[cid] = {
            "constellation_id": cid,
            "name": info.get("name", str(cid)),
            "region_id": info.get("region_id"),
            "systems": systems,
            "is_lawn": is_lawn,
        }
        tag = "LAWN" if is_lawn else "TKE"
        print(f"  [+] {info.get('name')} (ID: {cid}) -> {len(systems)} systems [{tag}]")

    # Build LAWN system ID set
    for cid, cdata in CONSTELLATION_DATA.items():
        if cdata.get("is_lawn"):
            LAWN_SYSTEM_IDS.update(cdata["systems"].keys())

    # 5. Resolve neighbor systems via POST /universe/ids/
    print(f"[*] Resolving {len(NEIGHBOR_SYSTEM_NAMES)} neighbor systems...")
    try:
        id_result = esi_client.post_universe_ids(NEIGHBOR_SYSTEM_NAMES)
        resolved_systems = id_result.get("systems", [])
        print(f"  [+] Resolved {len(resolved_systems)} / {len(NEIGHBOR_SYSTEM_NAMES)} names")

        # Fetch all neighbor system info in parallel
        neighbor_entries = {entry["id"]: entry["name"] for entry in resolved_systems}
        neighbor_sys_infos = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            future_to_sid = {
                pool.submit(esi_client.get_system_info, sid): sid
                for sid in neighbor_entries
            }
            for future in as_completed(future_to_sid):
                sid = future_to_sid[future]
                try:
                    neighbor_sys_infos[sid] = future.result()
                except Exception as e:
                    print(f"  [!] Error loading neighbor {neighbor_entries[sid]}: {e}")

        # Fetch unique constellation infos for region name resolution (parallel)
        neighbor_const_ids = set()
        for si in neighbor_sys_infos.values():
            cid = si.get("constellation_id")
            if cid:
                neighbor_const_ids.add(cid)

        neighbor_const_infos = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            future_to_cid = {
                pool.submit(esi_client.get_constellation_info, cid): cid
                for cid in neighbor_const_ids
            }
            for future in as_completed(future_to_cid):
                cid = future_to_cid[future]
                try:
                    neighbor_const_infos[cid] = future.result()
                except Exception:
                    pass

        # Fetch unique region infos (parallel)
        neighbor_region_ids = set()
        for ci in neighbor_const_infos.values():
            rid = ci.get("region_id")
            if rid:
                neighbor_region_ids.add(rid)

        neighbor_region_infos = {}
        with ThreadPoolExecutor(max_workers=10) as pool:
            future_to_rid = {
                pool.submit(esi_client.get_region_info, rid): rid
                for rid in neighbor_region_ids
            }
            for future in as_completed(future_to_rid):
                rid = future_to_rid[future]
                try:
                    neighbor_region_infos[rid] = future.result()
                except Exception:
                    pass

        # Assemble neighbor data
        for sys_id, sys_name in neighbor_entries.items():
            si = neighbor_sys_infos.get(sys_id)
            if not si:
                continue
            region_name = "Unknown"
            const_id = si.get("constellation_id")
            if const_id and const_id in neighbor_const_infos:
                rid = neighbor_const_infos[const_id].get("region_id")
                if rid and rid in neighbor_region_infos:
                    region_name = neighbor_region_infos[rid].get("name", "Unknown")

            NEIGHBOR_SYSTEMS[sys_id] = {
                "name": sys_name,
                "system_id": sys_id,
                "security_status": round(si.get("security_status", 0), 2),
                "region_name": region_name,
            }
    except Exception as e:
        print(f"  [!] Failed to resolve neighbor names: {e}")

    # Build ALL_MONITORED_IDS
    for cdata in CONSTELLATION_DATA.values():
        ALL_MONITORED_IDS.update(cdata["systems"].keys())
    ALL_MONITORED_IDS.update(NEIGHBOR_SYSTEMS.keys())

    tke_count = sum(len(c["systems"]) for c in CONSTELLATION_DATA.values())
    lawn_count = len(LAWN_SYSTEM_IDS)
    neighbor_count = len(NEIGHBOR_SYSTEMS)
    elapsed = _time.monotonic() - t_start
    print(f"[*] Total: {len(CONSTELLATION_DATA)} constellations, "
          f"{lawn_count} LAWN + {tke_count - lawn_count} TKE + {neighbor_count} neighbor "
          f"= {len(ALL_MONITORED_IDS)} systems ({elapsed:.1f}s)")


def _lookup_system_name(sys_id):
    """Look up system name from CONSTELLATION_DATA or NEIGHBOR_SYSTEMS."""
    for cdata in CONSTELLATION_DATA.values():
        if sys_id in cdata["systems"]:
            return cdata["systems"][sys_id]["name"]
    if sys_id in NEIGHBOR_SYSTEMS:
        return NEIGHBOR_SYSTEMS[sys_id]["name"]
    return ""


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
                "is_lawn": data.get("is_lawn", False),
            }
            for cid, data in CONSTELLATION_DATA.items()
        },
        "neighbor_systems": {
            str(sys_id): info
            for sys_id, info in NEIGHBOR_SYSTEMS.items()
        },
        "lawn_constellation_ids": list(LAWN_CONSTELLATION_IDS_SET),
        "friendly_alliances": FRIENDLY_ALLIANCES,
        "friendly_corporations": FRIENDLY_CORPORATIONS,
    })


@app.route("/api/sovereignty")
def api_sovereignty():
    """Get sovereignty data for all monitored systems."""
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

    # Filter to ALL monitored systems and resolve alliance names
    result = {}
    alliance_cache = {}
    corp_cache = {}

    for entry in sov_map:
        sys_id = entry.get("system_id")
        if sys_id in ALL_MONITORED_IDS:
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

    # Snapshot ADM values to database
    adm_batch = []
    for sys_id, sys_data in result.items():
        sys_name = _lookup_system_name(sys_id)
        adm_batch.append((sys_id, sys_name, sys_data["adm"], sys_data.get("alliance_name")))
    db.snapshot_adm_batch(adm_batch)

    return jsonify(result)


@app.route("/api/activity")
def api_activity():
    """Get kill and jump activity for all monitored systems."""
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
    for sys_id in ALL_MONITORED_IDS:
        kills = kills_by_system.get(sys_id, {})
        jumps = jumps_by_system.get(sys_id, {})

        result[sys_id] = {
            "system_id": sys_id,
            "ship_kills": kills.get("ship_kills", 0),
            "pod_kills": kills.get("pod_kills", 0),
            "npc_kills": kills.get("npc_kills", 0),
            "jumps": jumps.get("ship_jumps", 0),
        }

    # Snapshot activity data to database
    activity_batch = []
    for sys_id, sys_data in result.items():
        activity_batch.append((
            sys_id, sys_data["ship_kills"], sys_data["pod_kills"],
            sys_data["npc_kills"], sys_data["jumps"],
        ))
    db.snapshot_activity_batch(activity_batch)

    return jsonify(result)


@app.route("/api/campaigns")
def api_campaigns():
    """Get active sovereignty campaigns across all TKE constellations."""
    # Build system name lookup from ALL sources
    system_names = {}
    all_constellation_ids = set()
    for const_id, cdata in CONSTELLATION_DATA.items():
        all_constellation_ids.add(const_id)
        for sys_id, sys_info in cdata["systems"].items():
            system_names[sys_id] = sys_info["name"]
    for sys_id, info in NEIGHBOR_SYSTEMS.items():
        system_names[sys_id] = info["name"]

    # Fetch campaigns and structures
    campaigns = esi_client.get_sovereignty_campaigns()
    structures = esi_client.get_sovereignty_structures()
    structure_by_id = {s["structure_id"]: s for s in structures}

    # Filter to ALL TKE constellations (not just LAWN)
    enriched = []
    for campaign in campaigns:
        if campaign.get("constellation_id") not in all_constellation_ids:
            continue

        sys_id = campaign.get("solar_system_id")
        struct_id = campaign.get("structure_id")
        struct_data = structure_by_id.get(struct_id, {})

        is_lawn = sys_id in LAWN_SYSTEM_IDS

        enriched_campaign = {
            **campaign,
            "system_name": system_names.get(sys_id, f"System {sys_id}"),
            "vulnerable_start_time": struct_data.get("vulnerable_start_time"),
            "vulnerable_end_time": struct_data.get("vulnerable_end_time"),
            "structure_type_id": struct_data.get("structure_type_id"),
            "is_lawn": is_lawn,
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
    # Build LAWN system ID set for in_lawn flag
    system_names = {}
    for cdata in CONSTELLATION_DATA.values():
        for sys_id, sys_info in cdata["systems"].items():
            system_names[sys_id] = sys_info["name"]
    for sys_id, info in NEIGHBOR_SYSTEMS.items():
        system_names[sys_id] = info["name"]

    # Fetch recent kills from zKillboard for the whole region
    raw_kills = esi_client.get_zkill_region(REGION_ID)

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
            "in_lawn": solar_system_id in LAWN_SYSTEM_IDS,
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


@app.route("/api/history/adm")
def api_history_adm():
    """Get ADM history for all monitored systems."""
    hours = request.args.get("hours", 168, type=int)
    hours = min(hours, 720)  # Cap at 30 days
    history = db.get_adm_history(hours=hours)
    return jsonify(history)


@app.route("/api/status")
def api_status():
    """Health check / status endpoint."""
    tke_systems = sum(len(c["systems"]) for c in CONSTELLATION_DATA.values())
    lawn_systems = len(LAWN_SYSTEM_IDS)
    neighbor_systems = len(NEIGHBOR_SYSTEMS)
    return jsonify({
        "status": "online",
        "constellations_monitored": len(CONSTELLATION_DATA),
        "systems_monitored": len(ALL_MONITORED_IDS),
        "lawn_systems": lawn_systems,
        "tke_systems": tke_systems,
        "neighbor_systems": neighbor_systems,
        "constellation_names": [c["name"] for c in CONSTELLATION_DATA.values()],
    })


# ============ Custom Timers ============

@app.route("/api/timers", methods=["GET"])
def api_get_timers():
    """Get active custom timers."""
    timers = db.get_active_timers()
    return jsonify(timers)


@app.route("/api/auth/check", methods=["POST"])
def api_check_auth():
    """Verify timer password."""
    password = request.json.get("password")
    if password == TIMER_PASSWORD:
        return jsonify({"status": "ok"})
    return jsonify({"error": "Invalid password"}), 401


@app.route("/api/timers", methods=["POST"])
def api_add_timer():
    """Add a new custom timer."""
    # Check Auth
    auth_header = request.headers.get("X-Timer-Auth")
    if auth_header != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    if not all(k in data for k in ("system_name", "structure_type", "owner", "event_type", "timestamp")):
        return jsonify({"error": "Missing fields"}), 400
    
    db.add_timer(
        data["system_name"],
        data["structure_type"],
        data["owner"],
        data["event_type"],
        data["timestamp"],
        data.get("notes")
    )
    return jsonify({"status": "ok"})


@app.route("/api/timers/<int:timer_id>", methods=["DELETE"])
def api_delete_timer(timer_id):
    """Delete a custom timer."""
    # Check Auth
    auth_header = request.headers.get("X-Timer-Auth")
    if auth_header != TIMER_PASSWORD:
        return jsonify({"error": "Unauthorized"}), 401

    db.delete_timer(timer_id)
    return jsonify({"status": "ok"})


@app.route("/api/history/activity/heatmap")
def api_activity_heatmap():
    """Get aggregated activity heatmap data."""
    days = request.args.get("days", 7, type=int)
    hours = days * 24
    heatmap = db.get_activity_heatmap_data(hours=hours)
    return jsonify(heatmap)


@app.route("/api/intel/neighbors")
def api_neighbor_intel():
    """Analyze neighbor entities (threat profiling)."""
    results = []
    
    for entity in NEIGHBOR_ENTITIES:
        eid = entity["id"]
        etype = entity["type"]
        name = entity["name"]
        
        # 1. Fetch zKill data
        if etype == "alliance":
            kills = esi_client.get_zkill_alliance(eid)
        else:
            kills = esi_client.get_zkill_corporation(eid)
            
        # 2. Analyze
        ship_counts = {}
        hourly_activity = {h: 0 for h in range(24)}
        total_kills = len(kills)
        
        # Limit to last 50 to avoid slow loading
        recent_kills = kills[:50]
        
        for k in recent_kills:
            # zKill returns { killmail_id, zkb: { hash, ... } }
            # We need full details from ESI
            km_id = k.get("killmail_id")
            km_hash = k.get("zkb", {}).get("hash")
            
            if not km_id or not km_hash:
                continue
                
            full_kill = esi_client.get_killmail(km_id, km_hash)
            if not full_kill:
                continue
            
            # Timezone (killmail_time is ISO8601, e.g. "2023-10-27T12:00:00Z")
            try:
                # Simple string parsing for speed (YYYY-MM-DDThh:mm:ssZ)
                hour = int(full_kill["killmail_time"][11:13])
                hourly_activity[hour] += 1
            except:
                pass
            
            # Ship types (we look for attackers from this entity)
            for attacker in full_kill.get("attackers", []):
                # Check if this attacker belongs to the target entity
                if (etype == "alliance" and attacker.get("alliance_id") == eid) or \
                   (etype == "corporation" and attacker.get("corporation_id") == eid):
                    
                    ship_type = attacker.get("ship_type_id")
                    if ship_type:
                        ship_counts[ship_type] = ship_counts.get(ship_type, 0) + 1
        
        # Resolve ship names for top 5
        top_ships = sorted(ship_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        resolved_top_ships = []
        for tid, count in top_ships:
            resolved_top_ships.append({
                "name": esi_client.get_type_name(tid),
                "count": count
            })
            
        # Calculate Threat Score (very basic)
        # 0-10: Low, 11-50: Medium, 50+: High
        score_val = total_kills
        if score_val > 50: threat_level = "High"
        elif score_val > 10: threat_level = "Medium"
        else: threat_level = "Low"

        results.append({
            "id": eid,
            "name": name,
            "type": etype,
            "threat_level": threat_level,
            "total_kills_24h": total_kills, # zKill usually gives recent 200, assume recent
            "top_ships": resolved_top_ships,
            "activity_heatmap": [hourly_activity[h] for h in range(24)]
        })
        
    return jsonify(results)


# ============ Startup ============

# Load all systems at module import time (works with gunicorn and Flask dev server).
# In debug mode, Werkzeug's reloader will cause this to run twice — but with
# parallel fetches the second load hits the ESI cache and is near-instant.
resolve_all_systems()
db.init()

if __name__ == "__main__":
    lawn_names = [c['name'] for c in CONSTELLATION_DATA.values() if c.get('is_lawn')]
    print(f"\n[*] Dashboard starting at http://localhost:{FLASK_PORT}")
    print(f"[*] LAWN Intel Dashboard - Kalevala Expanse")
    print(f"[*] LAWN constellations: {', '.join(lawn_names)}")
    print(f"[*] Monitoring {len(ALL_MONITORED_IDS)} systems total\n")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
