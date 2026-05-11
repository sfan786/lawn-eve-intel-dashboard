from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, jsonify, request
from config import NEIGHBOR_ENTITIES, LAWN_ALLIANCE_ID, FRIENDLY_ALLIANCE_IDS, FRIENDLY_CORPORATIONS
from eve_constants import THREAT_SHIP_GROUPS
import esi_client
from routes.system_state import state

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
            {"name": name, "count": count}
            for name, count in top_ships
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


def _compute_risk_tier(stats: dict) -> dict:
    # zkill stats API top-level fields (all present but may be 0 for inactive chars)
    kills   = stats.get("shipsDestroyed", 0) or 0
    losses  = stats.get("shipsLost", 0) or 0
    danger  = stats.get("dangerRatio", 0) or 0
    gang    = stats.get("gangRatio", 0) or 0
    solo    = stats.get("soloKills", 0) or 0
    i_dest  = stats.get("iskDestroyed", 0) or 0
    i_lost  = stats.get("iskLost", 0) or 0

    # Fallback: some chars return activepvp.ships instead of shipsDestroyed
    if kills == 0:
        kills = (stats.get("activepvp") or {}).get("ships", {}).get("count", 0) or 0

    total_isk = i_dest + i_lost
    isk_eff = round(i_dest / total_isk * 100) if total_isk > 0 else 0

    if kills == 0 and losses == 0:
        tier, label = "nodata", "NO DATA"
    elif kills < 25:
        tier, label = "newbie", "NEWBIE"
    elif danger >= 75 or (danger >= 50 and kills >= 500):
        tier, label = "very_dangerous", "VERY DANGEROUS"
    elif danger >= 50 and kills >= 25:
        tier, label = "dangerous", "DANGEROUS"
    elif danger >= 25 or kills >= 100:
        tier, label = "moderate", "MODERATE"
    else:
        tier, label = "snuggly", "SNUGGLY"

    return {
        "tier": tier, "label": label,
        "kills": kills, "losses": losses,
        "danger": danger, "gang_ratio": gang,
        "solo_kills": solo, "isk_eff": isk_eff,
    }


def _detect_roles(groups: dict) -> list:
    """Detect capital/special-role ships from zkill stats groups dict.
    Each group entry has shipsDestroyed (helped kill that hull type) and
    shipsLost (character personally flew and lost that hull type).
    We only flag a role when shipsLost > 0 — i.e. the character has actually
    flown that hull, not merely been on killmails where one died.
    """
    roles = []
    for gid_str, gdata in (groups or {}).items():
        try:
            gid = int(gid_str)
            role = THREAT_SHIP_GROUPS.get(gid)
            if role and (gdata.get("shipsLost") or 0) > 0:
                roles.append(role)
        except (ValueError, TypeError):
            pass
    # Stable order: heaviest capitals first, then covert-cyno classes
    order = ["TITAN", "SUPER", "DREAD", "CARRIER", "FAX", "BLOPS", "RECON", "BOMBER", "T3C", "COVOPS"]
    return [r for r in order if r in roles]


@intel_bp.route("/api/chars/analyze", methods=["POST"])
def api_chars_analyze():
    char_ids = [int(cid) for cid in (request.json.get("char_ids") or [])[:25]]
    if not char_ids:
        return jsonify({})

    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        future_to_id = {pool.submit(esi_client.get_zkill_char_stats, cid): cid for cid in char_ids}
        for future in as_completed(future_to_id):
            cid = future_to_id[future]
            try:
                stats = future.result()
                risk = _compute_risk_tier(stats)
                risk["roles"] = _detect_roles(stats.get("groups", {}))
                results[str(cid)] = risk
            except Exception as e:
                print(f"Risk analyze error for {cid}: {e}")
                results[str(cid)] = {"tier": "nodata", "label": "NO DATA", "kills": 0, "losses": 0, "danger": 0, "gang_ratio": 0, "solo_kills": 0, "isk_eff": 0, "roles": []}

    return jsonify(results)


@intel_bp.route("/api/intel/regional")
def api_regional_intel():
    if not state.neighbor_systems:
        return jsonify({"regions": []})

    try:
        kills_data = esi_client.get_system_kills()
        jumps_data = esi_client.get_system_jumps()
    except Exception as e:
        return jsonify({"error": f"ESI unavailable: {e}"}), 503

    kills_by_system = {entry["system_id"]: entry for entry in kills_data}
    jumps_by_system = {entry["system_id"]: entry for entry in jumps_data}

    # Build per-region aggregates from neighbor systems
    regions = {}
    for sys_id, sys_info in state.neighbor_systems.items():
        region_name = sys_info.get("region_name", "Unknown")
        kills = kills_by_system.get(sys_id, {})
        ship_kills = kills.get("ship_kills", 0)
        pod_kills = kills.get("pod_kills", 0)
        npc_kills = kills.get("npc_kills", 0)
        jumps = jumps_by_system.get(sys_id, {}).get("ship_jumps", 0)

        if region_name not in regions:
            regions[region_name] = {"name": region_name, "systems": [], "total_kills": 0, "total_jumps": 0}

        # Per-system threat level
        if ship_kills >= 10 or jumps >= 50:
            sys_threat = "high"
        elif ship_kills >= 3 or jumps >= 20:
            sys_threat = "elevated"
        else:
            sys_threat = "quiet"

        regions[region_name]["systems"].append({
            "system_id": sys_id,
            "name": sys_info["name"],
            "ship_kills": ship_kills,
            "pod_kills": pod_kills,
            "npc_kills": npc_kills,
            "jumps": jumps,
            "threat": sys_threat,
        })
        regions[region_name]["total_kills"] += ship_kills
        regions[region_name]["total_jumps"] += jumps

    # Per-region threat level
    for r in regions.values():
        if r["total_kills"] >= 15 or r["total_jumps"] >= 80:
            r["threat"] = "high"
        elif r["total_kills"] >= 5 or r["total_jumps"] >= 30:
            r["threat"] = "elevated"
        else:
            r["threat"] = "quiet"
        # Sort systems by kills desc
        r["systems"].sort(key=lambda s: s["ship_kills"], reverse=True)

    # Sort regions: high first, then elevated, then quiet; alphabetical within tier
    tier_order = {"high": 0, "elevated": 1, "quiet": 2}
    sorted_regions = sorted(regions.values(), key=lambda r: (tier_order.get(r["threat"], 9), r["name"]))

    return jsonify({"regions": sorted_regions})
