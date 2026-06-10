import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Blueprint, jsonify, request
from config import NEIGHBOR_ENTITIES, LAWN_ALLIANCE_ID, FRIENDLY_ALLIANCE_IDS, FRIENDLY_CORPORATIONS
from eve_constants import THREAT_SHIP_GROUPS, FLEET_ROLE_GROUPS
import db
import esi_client
from routes.system_state import state

intel_bp = Blueprint("intel", __name__)

# Endpoint-level cache for the slow neighbor intel endpoint
_neighbors_cache = {"data": None, "ts": 0}
NEIGHBORS_CACHE_TTL = 900  # 15 minutes

_EXCLUDED_ALLIANCE_IDS = None  # lazily built from config


def _get_excluded_ids():
    global _EXCLUDED_ALLIANCE_IDS
    if _EXCLUDED_ALLIANCE_IDS is None:
        _EXCLUDED_ALLIANCE_IDS = set(FRIENDLY_ALLIANCE_IDS) | {LAWN_ALLIANCE_ID}
    return _EXCLUDED_ALLIANCE_IDS


def _format_isk(value):
    if value >= 1e12:
        return f"{value/1e12:.1f}T"
    if value >= 1e9:
        return f"{value/1e9:.1f}B"
    if value >= 1e6:
        return f"{value/1e6:.1f}M"
    return f"{value/1e3:.0f}K"


def _peak_tz(hourly):
    """Return a label for the 6-hour UTC window with highest kill activity."""
    best = max(range(24), key=lambda h: sum(hourly.get((h + i) % 24, 0) for i in range(6)))
    end = (best + 6) % 24
    return f"{best:02d}:00–{end:02d}:00 UTC"


def _build_pinned_profile(entity, pinned_set):
    """Build a full threat profile for a manually configured (pinned) entity."""
    eid = entity["id"]
    etype = entity["type"]
    name = entity["name"]

    if etype == "alliance":
        kills = esi_client.get_zkill_alliance(eid)
    else:
        kills = esi_client.get_zkill_corporation(eid)

    total_kills = len(kills)
    recent_kills = kills[:25]
    total_isk = sum(k.get("zkb", {}).get("totalValue", 0) for k in kills[:100])

    doctrine_counts = {}   # ship_type_id -> count
    hourly_activity = {h: 0 for h in range(24)}
    neighbor_region_hits = {}  # region_name -> count

    neighbor_ids = set(state.neighbor_systems.keys())

    with ThreadPoolExecutor(max_workers=20) as pool:
        futures = {
            pool.submit(esi_client.get_killmail, k.get("killmail_id"), k.get("zkb", {}).get("hash")): k
            for k in recent_kills
            if k.get("killmail_id") and k.get("zkb", {}).get("hash")
        }
        for future in as_completed(futures):
            try:
                full_kill = future.result()
                if not full_kill:
                    continue

                # Doctrine: ships this entity FLEW (attacker side)
                for attacker in full_kill.get("attackers", []):
                    if etype == "alliance" and attacker.get("alliance_id") == eid:
                        st = attacker.get("ship_type_id")
                        if st:
                            doctrine_counts[st] = doctrine_counts.get(st, 0) + 1
                    elif etype == "corporation" and attacker.get("corporation_id") == eid:
                        st = attacker.get("ship_type_id")
                        if st:
                            doctrine_counts[st] = doctrine_counts.get(st, 0) + 1

                # Time zone heatmap
                kill_time = full_kill.get("killmail_time", "")
                if kill_time:
                    try:
                        hourly_activity[int(kill_time[11:13])] += 1
                    except Exception:
                        pass

                # Activity in our neighbor space
                sys_id = full_kill.get("solar_system_id")
                if sys_id and sys_id in neighbor_ids:
                    region = state.neighbor_systems[sys_id].get("region_name", "Unknown")
                    neighbor_region_hits[region] = neighbor_region_hits.get(region, 0) + 1

            except Exception as e:
                print(f"[!] Killmail error for {name}: {e}")

    # Resolve top 5 doctrine ships and detect capital roles
    top_type_ids = sorted(doctrine_counts, key=doctrine_counts.get, reverse=True)[:5]
    top_ships = []
    capital_roles = []
    seen_roles = set()
    for tid in top_type_ids:
        ship_name = esi_client.get_type_name(tid)
        top_ships.append({"name": ship_name, "count": doctrine_counts[tid]})
        try:
            gid = esi_client.get_type_group_id(tid)
            role = THREAT_SHIP_GROUPS.get(gid)
            if role and role not in seen_roles:
                capital_roles.append(role)
                seen_roles.add(role)
        except Exception:
            pass

    # Composite threat level: capitals always elevate to Medium or High
    has_capitals = bool(capital_roles)
    if total_kills > 50 or (total_kills > 20 and has_capitals):
        threat_level = "High"
    elif total_kills > 10 or has_capitals:
        threat_level = "Medium"
    else:
        threat_level = "Low"

    neighbor_regions = sorted(neighbor_region_hits, key=neighbor_region_hits.get, reverse=True)

    return {
        "id": eid,
        "name": name,
        "type": etype,
        "pinned": True,
        "threat_level": threat_level,
        "total_kills": total_kills,
        "isk_destroyed": total_isk,
        "isk_label": _format_isk(total_isk),
        "top_ships": top_ships,
        "capital_roles": capital_roles,
        "activity_heatmap": [hourly_activity[h] for h in range(24)],
        "peak_tz": _peak_tz(hourly_activity),
        "neighbor_regions": neighbor_regions,
    }


def _detect_regional_threats(pinned_ids):
    """Auto-detect active alliances from recent kills in neighbor systems."""
    if not state.neighbor_systems:
        return []

    try:
        kills_data = esi_client.get_system_kills()
    except Exception:
        return []

    kills_by_system = {e["system_id"]: e.get("ship_kills", 0) for e in kills_data}

    # Top 5 active neighbor systems
    active = sorted(
        [(sid, kills_by_system.get(sid, 0)) for sid in state.neighbor_systems],
        key=lambda x: x[1], reverse=True
    )
    top_systems = [sid for sid, k in active if k > 0][:5]

    if not top_systems:
        return []

    # Fetch zkill data for those systems
    all_kill_refs = []
    for sys_id in top_systems:
        try:
            refs = esi_client.get_zkill_system(sys_id)
            all_kill_refs.extend(refs[:20])
        except Exception:
            pass

    if not all_kill_refs:
        return []

    # Deduplicate and limit total killmail fetches
    seen_ids = set()
    unique_refs = []
    for ref in all_kill_refs:
        kid = ref.get("killmail_id")
        if kid and kid not in seen_ids:
            seen_ids.add(kid)
            unique_refs.append(ref)
    unique_refs = unique_refs[:20]

    excluded = _get_excluded_ids() | pinned_ids
    entity_kills = {}   # alliance_id -> count
    entity_ships = {}   # alliance_id -> {ship_type_id: count}

    with ThreadPoolExecutor(max_workers=10) as pool:
        futures = {
            pool.submit(esi_client.get_killmail, r.get("killmail_id"), r.get("zkb", {}).get("hash")): r
            for r in unique_refs
            if r.get("killmail_id") and r.get("zkb", {}).get("hash")
        }
        for future in as_completed(futures):
            try:
                full_kill = future.result()
                if not full_kill:
                    continue
                for attacker in full_kill.get("attackers", []):
                    aid = attacker.get("alliance_id")
                    if not aid or aid in excluded:
                        continue
                    entity_kills[aid] = entity_kills.get(aid, 0) + 1
                    st = attacker.get("ship_type_id")
                    if st:
                        entity_ships.setdefault(aid, {})
                        entity_ships[aid][st] = entity_ships[aid].get(st, 0) + 1
            except Exception:
                pass

    # Build profiles for top 6 auto-detected entities
    top_entities = sorted(entity_kills, key=entity_kills.get, reverse=True)[:6]
    results = []
    for aid in top_entities:
        try:
            info = esi_client.get_alliance_info(aid)
            aname = info.get("name", f"Alliance {aid}")
        except Exception:
            aname = f"Alliance {aid}"

        ship_counts = entity_ships.get(aid, {})
        top_type_ids = sorted(ship_counts, key=ship_counts.get, reverse=True)[:3]
        top_ships = []
        capital_roles = []
        seen_roles = set()
        for tid in top_type_ids:
            top_ships.append({"name": esi_client.get_type_name(tid), "count": ship_counts[tid]})
            try:
                gid = esi_client.get_type_group_id(tid)
                role = THREAT_SHIP_GROUPS.get(gid)
                if role and role not in seen_roles:
                    capital_roles.append(role)
                    seen_roles.add(role)
            except Exception:
                pass

        results.append({
            "id": aid,
            "name": aname,
            "type": "alliance",
            "pinned": False,
            "kills_in_neighbor_space": entity_kills[aid],
            "top_ships": top_ships,
            "capital_roles": capital_roles,
        })

    return results


@intel_bp.route("/api/intel/neighbors")
def api_neighbor_intel():
    if time.time() - _neighbors_cache["ts"] < NEIGHBORS_CACHE_TTL and _neighbors_cache["data"]:
        return jsonify(_neighbors_cache["data"])

    pinned_results = []
    pinned_ids = set(e["id"] for e in NEIGHBOR_ENTITIES)

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(_build_pinned_profile, entity, pinned_ids): entity for entity in NEIGHBOR_ENTITIES}
        for future in as_completed(futures):
            try:
                pinned_results.append(future.result())
            except Exception as e:
                entity = futures[future]
                print(f"[!] Failed to build profile for {entity['name']}: {e}")

    pinned_results.sort(key=lambda r: {"High": 0, "Medium": 1, "Low": 2}.get(r["threat_level"], 3))

    detected_results = _detect_regional_threats(pinned_ids)

    result = {"pinned": pinned_results, "detected": detected_results}
    _neighbors_cache["data"] = result
    _neighbors_cache["ts"] = time.time()
    return jsonify(result)


def _get_names_list(payload, key="names", limit=100):
    """Extract a validated list of non-empty strings from a JSON payload."""
    if not isinstance(payload, dict):
        return None
    names = payload.get(key, [])
    if not isinstance(names, list):
        return None
    return [n for n in names if isinstance(n, str) and n.strip()][:limit]


@intel_bp.route("/api/local/scan", methods=["POST"])
def api_local_scan():
    names = _get_names_list(request.json)
    if names is None:
        return jsonify({"error": "names must be a list of strings"}), 400
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
    payload = request.json if isinstance(request.json, dict) else {}
    raw_ids = payload.get("char_ids") or []
    if not isinstance(raw_ids, list):
        return jsonify({"error": "char_ids must be a list of integers"}), 400
    try:
        char_ids = [int(cid) for cid in raw_ids[:25]]
    except (ValueError, TypeError):
        return jsonify({"error": "char_ids must be a list of integers"}), 400
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


def _detect_fleet_roles(groups: dict) -> list:
    """Detect subcap fleet roles from zkill stats groups (shipsLost > 0 = actually flown)."""
    roles = []
    seen = set()
    for gid_str, gdata in (groups or {}).items():
        try:
            gid = int(gid_str)
            role = FLEET_ROLE_GROUPS.get(gid)
            if role and role not in seen and (gdata.get("shipsLost") or 0) > 0:
                roles.append(role)
                seen.add(role)
        except (ValueError, TypeError):
            pass
    return roles


@intel_bp.route("/api/fleet/analyze", methods=["POST"])
def api_fleet_analyze():
    names = _get_names_list(request.json)
    if names is None:
        return jsonify({"error": "names must be a list of strings"}), 400
    if not names:
        return jsonify({"pilots": [], "summary": {}})

    # 1. Resolve names → char IDs
    try:
        resolved = esi_client.post_universe_ids(names)
    except Exception as e:
        return jsonify({"error": f"ESI name resolution failed: {e}"}), 502

    char_map = {c["name"]: c["id"] for c in resolved.get("characters", [])}
    unresolved_names = [n for n in names if n not in char_map]

    # 2. Bulk affiliations
    char_ids = list(char_map.values())
    affil_by_id = {}
    if char_ids:
        try:
            for a in esi_client.bulk_character_affiliations(char_ids):
                affil_by_id[a["character_id"]] = a
        except Exception:
            pass

    # 3. Resolve corp/alliance names (deduplicated fetches)
    corp_name_cache = {}
    alliance_name_cache = {}
    corp_ids = {a["corporation_id"] for a in affil_by_id.values() if a.get("corporation_id")}
    alliance_ids_set = {a["alliance_id"] for a in affil_by_id.values() if a.get("alliance_id")}

    with ThreadPoolExecutor(max_workers=10) as pool:
        corp_futures = {pool.submit(esi_client.get_corporation_info, cid): cid for cid in corp_ids}
        alliance_futures = {pool.submit(esi_client.get_alliance_info, aid): aid for aid in alliance_ids_set}
        for f in as_completed(corp_futures):
            cid = corp_futures[f]
            try:
                corp_name_cache[cid] = f.result().get("name")
            except Exception:
                corp_name_cache[cid] = None
        for f in as_completed(alliance_futures):
            aid = alliance_futures[f]
            try:
                alliance_name_cache[aid] = f.result().get("name")
            except Exception:
                alliance_name_cache[aid] = None
    # 4. Fetch zkill stats for risk + role analysis
    zkill_stats = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        future_to_id = {pool.submit(esi_client.get_zkill_char_stats, cid): cid for cid in char_ids}
        for f in as_completed(future_to_id):
            cid = future_to_id[f]
            try:
                zkill_stats[cid] = f.result()
            except Exception:
                zkill_stats[cid] = {}

    # 5. Build per-pilot results
    pilots = []
    alliance_counts = {}

    for name, char_id in char_map.items():
        affil = affil_by_id.get(char_id, {})
        corp_id = affil.get("corporation_id")
        alliance_id = affil.get("alliance_id")
        corp_name = corp_name_cache.get(corp_id) if corp_id else None
        alliance_name = alliance_name_cache.get(alliance_id) if alliance_id else None

        if alliance_id == LAWN_ALLIANCE_ID:
            standing = "lawn"
        elif corp_name in FRIENDLY_CORPORATIONS:
            standing = "lawn"
        elif alliance_id in FRIENDLY_ALLIANCE_IDS:
            standing = "friendly"
        else:
            standing = "unknown"

        stats = zkill_stats.get(char_id, {})
        risk = _compute_risk_tier(stats)
        groups = stats.get("groups", {})
        capital_roles = _detect_roles(groups)
        fleet_roles = _detect_fleet_roles(groups)

        # Track alliance breakdown (unknown/hostile only)
        if standing == "unknown" and alliance_name:
            alliance_counts[alliance_name] = alliance_counts.get(alliance_name, 0) + 1

        pilots.append({
            "name": name,
            "character_id": char_id,
            "corporation_name": corp_name,
            "alliance_name": alliance_name,
            "standing": standing,
            "risk_tier": risk["tier"],
            "risk_label": risk["label"],
            "kills": risk["kills"],
            "losses": risk["losses"],
            "danger": risk["danger"],
            "isk_eff": risk["isk_eff"],
            "roles": capital_roles,
            "fleet_roles": fleet_roles,
        })

    for name in unresolved_names:
        pilots.append({
            "name": name,
            "character_id": None,
            "corporation_name": None,
            "alliance_name": None,
            "standing": "unresolved",
            "risk_tier": "nodata",
            "risk_label": "UNRESOLVED",
            "kills": 0,
            "losses": 0,
            "danger": 0,
            "isk_eff": 0,
            "roles": [],
            "fleet_roles": [],
        })

    # Sort: unknown first, then friendly/lawn, then unresolved; within standing sort by danger desc
    standing_order = {"unknown": 0, "friendly": 1, "lawn": 2, "unresolved": 3}
    pilots.sort(key=lambda p: (standing_order.get(p["standing"], 9), -p["danger"]))

    # 6. Build summary
    resolved_pilots = [p for p in pilots if p["character_id"]]
    unknown_pilots = [p for p in pilots if p["standing"] == "unknown"]

    risk_dist = {}
    for p in resolved_pilots:
        risk_dist[p["risk_tier"]] = risk_dist.get(p["risk_tier"], 0) + 1

    role_counts = {}
    fleet_role_counts = {}
    for p in resolved_pilots:
        for r in p["roles"]:
            role_counts[r] = role_counts.get(r, 0) + 1
        for r in p["fleet_roles"]:
            fleet_role_counts[r] = fleet_role_counts.get(r, 0) + 1

    danger_vals = [p["danger"] for p in unknown_pilots if p["risk_tier"] not in ("nodata", "newbie")]
    avg_danger = round(sum(danger_vals) / len(danger_vals)) if danger_vals else 0
    kill_vals = [p["kills"] for p in unknown_pilots if p["risk_tier"] not in ("nodata",)]
    avg_kills = round(sum(kill_vals) / len(kill_vals)) if kill_vals else 0

    capitals = sum(1 for p in pilots if any(r in ("TITAN", "SUPER", "DREAD", "CARRIER", "FAX") for r in p["roles"]))

    top_alliances = sorted(alliance_counts.items(), key=lambda x: x[1], reverse=True)[:8]

    summary = {
        "total": len(pilots),
        "unknown": sum(1 for p in pilots if p["standing"] == "unknown"),
        "friendly": sum(1 for p in pilots if p["standing"] == "friendly"),
        "lawn": sum(1 for p in pilots if p["standing"] == "lawn"),
        "unresolved": sum(1 for p in pilots if p["standing"] == "unresolved"),
        "avg_danger": avg_danger,
        "avg_kills": avg_kills,
        "capitals": capitals,
        "risk_distribution": risk_dist,
        "role_counts": role_counts,
        "fleet_role_counts": fleet_role_counts,
        "top_alliances": [{"name": n, "count": c} for n, c in top_alliances],
    }

    return jsonify({"pilots": pilots, "summary": summary})


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

    # Fetch 7-day baseline for spike detection
    baselines = db.get_activity_baseline(list(state.neighbor_systems.keys()))

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

        # Spike detection — only when we have enough history
        bl = baselines.get(sys_id, {})
        sample_n = bl.get("sample_count", 0)
        avg_k = bl.get("avg_kills", 0)
        avg_j = bl.get("avg_jumps", 0)
        if sample_n >= 3:
            spike_k = round(ship_kills / max(avg_k, 0.5), 1)
            spike_j = round(jumps / max(avg_j, 1.0), 1)
        else:
            spike_k = None
            spike_j = None

        regions[region_name]["systems"].append({
            "system_id": sys_id,
            "name": sys_info["name"],
            "ship_kills": ship_kills,
            "pod_kills": pod_kills,
            "npc_kills": npc_kills,
            "jumps": jumps,
            "threat": sys_threat,
            "avg_kills": avg_k,
            "avg_jumps": avg_j,
            "spike_kills": spike_k,
            "spike_jumps": spike_j,
        })
        regions[region_name]["total_kills"] += ship_kills
        regions[region_name]["total_jumps"] += jumps

    # Per-region threat level + max spike ratio
    for r in regions.values():
        if r["total_kills"] >= 15 or r["total_jumps"] >= 80:
            r["threat"] = "high"
        elif r["total_kills"] >= 5 or r["total_jumps"] >= 30:
            r["threat"] = "elevated"
        else:
            r["threat"] = "quiet"
        r["systems"].sort(key=lambda s: s["ship_kills"], reverse=True)
        spikes = [s["spike_kills"] for s in r["systems"] if s["spike_kills"] is not None]
        r["max_spike"] = max(spikes) if spikes else None

    # Sort regions: high first, then elevated, then quiet; alphabetical within tier
    tier_order = {"high": 0, "elevated": 1, "quiet": 2}
    sorted_regions = sorted(regions.values(), key=lambda r: (tier_order.get(r["threat"], 9), r["name"]))

    return jsonify({"regions": sorted_regions})


@intel_bp.route("/api/intel/sov_changes")
def api_sov_changes():
    if not state.neighbor_systems:
        return jsonify({"changes": [], "checked_at": time.time()})

    try:
        sov_data = esi_client.get_sovereignty_map()
    except Exception as e:
        return jsonify({"error": f"ESI unavailable: {e}"}), 503

    neighbor_ids = set(state.neighbor_systems.keys())
    current_sov = {}
    for entry in sov_data:
        sys_id = entry.get("system_id")
        if sys_id in neighbor_ids:
            current_sov[sys_id] = entry.get("alliance_id", 0)

    system_names = {sid: info["name"] for sid, info in state.neighbor_systems.items()}
    db.record_sov_changes(current_sov, system_names)

    return jsonify({
        "changes": db.get_recent_sov_changes(20),
        "checked_at": time.time(),
    })
