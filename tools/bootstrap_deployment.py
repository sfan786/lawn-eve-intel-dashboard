"""
Bootstrap a new deployment config from alliance + region + constellation names.

Resolves IDs from ESI, fetches every system in the region, walks the gate
graph to find adjacent neighbour systems, generates an auto-layout for the
SVG map, and snapshots planetary interaction data. Writes a Python module
to deployments/<name>.py that the dashboard can load via the DEPLOYMENT
env var.

Usage:
    python tools/bootstrap_deployment.py \\
        --name lawn-perrigen \\
        --alliance "Get Off My Lawn" \\
        --region "Perrigen Falls" \\
        --constellations "9BGY-6,WXB-RY"

Re-run any time to refresh the auto-generated sections (region geography,
PI data, gate connections). Hand-tuned MAP_LAYOUT positions and SYSTEM_UPGRADES
will be overwritten unless you pass --no-overwrite-layout.
"""

import argparse
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import esi_client
from eve_constants import PLANET_TYPE_NAMES


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def resolve_alliance(name):
    data = esi_client.post_universe_ids([name])
    matches = data.get("alliances") or []
    if not matches:
        raise SystemExit(f"Could not resolve alliance '{name}'")
    aid = matches[0]["id"]
    info = esi_client.get_alliance_info(aid)
    return {
        "id": aid,
        "name": info.get("name", name),
        "ticker": info.get("ticker", ""),
        "short_name": info.get("ticker", ""),
        "display_name": info.get("name", name).upper(),
    }


def resolve_region(name):
    data = esi_client.post_universe_ids([name])
    matches = data.get("regions") or []
    if not matches:
        raise SystemExit(f"Could not resolve region '{name}'")
    return {"id": matches[0]["id"], "name": matches[0]["name"]}


def resolve_constellations(names):
    data = esi_client.post_universe_ids(names)
    matches = data.get("constellations") or []
    found = {c["name"]: c["id"] for c in matches}
    missing = [n for n in names if n not in found]
    if missing:
        raise SystemExit(f"Could not resolve constellation(s): {missing}")
    return [(found[n], n) for n in names]


# ---------------------------------------------------------------------------
# Region fetch (constellations + systems + gates)
# ---------------------------------------------------------------------------

def fetch_region(region_id):
    """Returns (constellations, systems) where:
        constellations[cid] = {name, region_id, system_ids: [sid]}
        systems[sid] = {name, security_status, constellation_id, planets, stargates}
    """
    region = esi_client.get_region_info(region_id)
    cid_list = region.get("constellations", [])

    constellations = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(esi_client.get_constellation_info, cid): cid for cid in cid_list}
        for fut in as_completed(futs):
            ci = fut.result()
            constellations[ci["constellation_id"]] = {
                "name": ci["name"],
                "region_id": ci["region_id"],
                "system_ids": list(ci["systems"]),
            }

    sid_list = [sid for c in constellations.values() for sid in c["system_ids"]]
    systems = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(esi_client.get_system_info, sid): sid for sid in sid_list}
        for fut in as_completed(futs):
            si = fut.result()
            systems[si["system_id"]] = {
                "name": si["name"],
                "security_status": round(si.get("security_status", 0), 2),
                "constellation_id": si.get("constellation_id"),
                "planets": [p["planet_id"] for p in si.get("planets", [])],
                "stargates": list(si.get("stargates", [])),
            }
    return constellations, systems


def fetch_gate_destinations(systems):
    """Return {sid: [destination_sid, ...]} by walking each stargate."""
    gate_ids = [g for s in systems.values() for g in s["stargates"]]

    def fetch(gid):
        return gid, esi_client.esi_get(f"/universe/stargates/{gid}/")

    dest = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(fetch, gid): gid for gid in gate_ids}
        for fut in as_completed(futs):
            gid, gdata = fut.result()
            dest[gid] = gdata["destination"]["system_id"]

    edges = {sid: [] for sid in systems}
    for sid, sdata in systems.items():
        for gid in sdata["stargates"]:
            d = dest.get(gid)
            if d is not None:
                edges[sid].append(d)
    return edges


def fetch_neighbour_systems(neighbour_sids):
    """For each system outside the primary region, fetch system + region context."""
    if not neighbour_sids:
        return {}

    systems = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(esi_client.get_system_info, sid): sid for sid in neighbour_sids}
        for fut in as_completed(futs):
            si = fut.result()
            systems[si["system_id"]] = {
                "name": si["name"],
                "security_status": round(si.get("security_status", 0), 2),
                "constellation_id": si.get("constellation_id"),
            }

    cids = {s["constellation_id"] for s in systems.values() if s["constellation_id"]}
    constellations = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(esi_client.get_constellation_info, cid): cid for cid in cids}
        for fut in as_completed(futs):
            ci = fut.result()
            constellations[ci["constellation_id"]] = ci

    rids = {ci["region_id"] for ci in constellations.values()}
    region_names = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        futs = {pool.submit(esi_client.get_region_info, rid): rid for rid in rids}
        for fut in as_completed(futs):
            ri = fut.result()
            region_names[ri["region_id"]] = ri["name"]

    for s in systems.values():
        cid = s["constellation_id"]
        rid = constellations.get(cid, {}).get("region_id") if cid else None
        s["region_name"] = region_names.get(rid, "Unknown")
    return systems


def fetch_planet_data(systems, primary_sids):
    """Return {system_name: [{planet_id, name, type_id, type}]} for planets in primary systems."""
    jobs = []
    for sid in primary_sids:
        sname = systems[sid]["name"]
        for pid in systems[sid]["planets"]:
            jobs.append((sname, pid))

    def fetch(pid):
        return pid, esi_client.esi_get(f"/universe/planets/{pid}/")

    raw = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = {pool.submit(fetch, pid): pid for _, pid in jobs}
        for fut in as_completed(futs):
            pid, data = fut.result()
            raw[pid] = data

    pi = {}
    for sname, pid in sorted(jobs, key=lambda x: (x[0], x[1])):
        data = raw[pid]
        type_id = data.get("type_id")
        pi.setdefault(sname, []).append({
            "planet_id": pid,
            "name": data.get("name", f"Planet {pid}"),
            "type_id": type_id,
            "type": PLANET_TYPE_NAMES.get(type_id, f"Type {type_id}"),
        })
    return pi


# ---------------------------------------------------------------------------
# Connections + layout
# ---------------------------------------------------------------------------

def build_connections(systems, neighbour_sys, edges):
    """[(from_name, to_name, type)] across all displayed systems. Pairs deduped."""
    in_region = set(systems.keys())
    in_neighbour = set(neighbour_sys.keys())
    sid_name = {sid: s["name"] for sid, s in systems.items()}
    sid_name.update({sid: s["name"] for sid, s in neighbour_sys.items()})
    sid_const = {sid: s["constellation_id"] for sid, s in systems.items()}

    seen = set()
    out = []
    for sid, dests in edges.items():
        for dest in dests:
            if dest not in in_region and dest not in in_neighbour:
                continue
            key = tuple(sorted([sid, dest]))
            if key in seen:
                continue
            seen.add(key)

            a_in = sid in in_region
            b_in = dest in in_region
            if a_in and b_in:
                ctype = "internal" if sid_const[sid] == sid_const[dest] else "cross"
            elif a_in != b_in:
                ctype = "regional"
            else:
                ctype = "neighbor"
            out.append([sid_name[sid], sid_name[dest], ctype])
    out.sort(key=lambda x: (x[2], x[0], x[1]))
    return out


def auto_layout(constellations, systems, primary_cids, neighbour_sys):
    """Grid of constellation cells; systems in a circle within each cell.
    Neighbours grouped by region on canvas edges.

    Coordinates target the existing viewBox '-40 -20 1220 790'. Hand-tune in
    the generated module before going live — the auto-layout is only a starting
    point, not a final design.
    """
    primary_set = set(primary_cids)
    cids_sorted = sorted(
        constellations.keys(),
        key=lambda c: (c not in primary_set, constellations[c]["name"]),
    )

    canvas_w, canvas_h = 1100, 650
    n_cells = max(1, len(cids_sorted))
    cols = max(1, math.ceil(math.sqrt(n_cells)))
    rows = max(1, math.ceil(n_cells / cols))
    cell_w = canvas_w / cols
    cell_h = canvas_h / rows

    layout = {}
    for idx, cid in enumerate(cids_sorted):
        cdata = constellations[cid]
        is_primary = cid in primary_set
        col = idx % cols
        row = idx // cols
        cx = col * cell_w + cell_w / 2 + 80
        cy = row * cell_h + cell_h / 2 + 60

        sids = sorted(cdata["system_ids"], key=lambda s: systems[s]["name"])
        n = len(sids)
        radius = min(cell_w, cell_h) * 0.32
        if n <= 1:
            radius = 0
        for i, sid in enumerate(sids):
            if n > 1:
                angle = 2 * math.pi * i / n - math.pi / 2
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
            else:
                x, y = cx, cy
            entry = {
                "x": round(x),
                "y": round(y),
                "constellation": cdata["name"],
            }
            if is_primary:
                entry["lawn"] = True
            layout[systems[sid]["name"]] = entry

    # Neighbours by region — distribute around the canvas edges
    by_region = {}
    for s in neighbour_sys.values():
        by_region.setdefault(s["region_name"], []).append(s)

    edge_idx = 0
    for rname, members in sorted(by_region.items()):
        edge = edge_idx % 4
        edge_idx += 1
        members = sorted(members, key=lambda s: s["name"])
        for i, s in enumerate(members):
            if edge == 0:    # left
                x, y = 20, 60 + i * 40
            elif edge == 1:  # top
                x, y = 200 + i * 60, 10
            elif edge == 2:  # right
                x, y = canvas_w + 80, 60 + i * 40
            else:            # bottom
                x, y = 200 + i * 60, canvas_h + 80
            layout[s["name"]] = {
                "x": x,
                "y": y,
                "constellation": "neighbor",
                "note": rname,
            }

    return layout


# ---------------------------------------------------------------------------
# Module rendering
# ---------------------------------------------------------------------------

MODULE_TEMPLATE = '''"""
Deployment: {deployment_id}
Auto-generated by tools/bootstrap_deployment.py at {timestamp}
Region: {region_name} ({region_id})
Primary constellations: {primary_const_names}

Re-run the bootstrap to refresh region geography, gate connections, and PI
data. The MAP_LAYOUT and MAP_LAYOUT_SUBWAY positions are starter values from
an automatic layout — hand-tune them for readability, then keep them in
source control. SYSTEM_UPGRADES is intentionally empty: populate it as
upgrades are installed in-game.
"""

DEPLOYMENT_ID = {deployment_id!r}

ALLIANCE = {alliance}

REGION = {region}

PRIMARY_CONSTELLATION_IDS = {primary_const_ids}
PRIMARY_CONSTELLATION_NAMES = {primary_const_names_list}

# ===== Friendlies and threat tracking (manually maintained) =====
# Copy these from your previous deployment when migrating, or fill in fresh.
FRIENDLY_ALLIANCE_IDS = {friendly_alliance_ids}

FRIENDLY_ALLIANCES = {friendly_alliances}

FRIENDLY_CORPORATIONS = {friendly_corporations}

NEIGHBOR_ENTITIES = {neighbor_entities}

# ===== Region geography (auto-generated) =====
# Systems just outside the primary region that share a gate with one of our
# systems. Used by SystemState.resolve_all_systems for the early-warning panel.
NEIGHBOR_SYSTEM_NAMES = {neighbor_system_names}

PRIMARY_SYSTEMS = {primary_systems}

BORDER_SYSTEMS = {border_systems}

# ===== Sov upgrades (manual — populate as upgrades are installed) =====
SYSTEM_UPGRADES = {{}}

# ===== Map layout (auto-generated, hand-tune for readability) =====
MAP_LAYOUT = {map_layout}

# Subway-style layout: starts identical to MAP_LAYOUT. Adjust to taste; the
# subway view prioritises readability (orthogonal angles, generous spacing)
# over geometric accuracy.
MAP_LAYOUT_SUBWAY = {map_layout_subway}

MAP_CONNECTIONS = {map_connections}

# ===== Planetary Interaction =====
PI_DATA = {pi_data}
'''


def py_repr(obj, indent=4):
    """Pretty-print a Python literal with stable key ordering."""
    return json.dumps(obj, indent=indent, sort_keys=False).replace(": null", ": None").replace(": true", ": True").replace(": false", ": False")


def render_dict_of_lists(d, key_indent=4):
    """Render {key: [list]} compactly so each key's list fits on one line."""
    if not d:
        return "{}"
    lines = ["{"]
    for k in sorted(d.keys()):
        lines.append(f"    {k!r}: {d[k]!r},")
    lines.append("}")
    return "\n".join(lines)


def render_module(args, alliance, region, primary_constellations,
                  neighbour_system_names, primary_systems, border_systems,
                  map_layout, map_layout_subway, map_connections, pi_data,
                  inherited):
    primary_const_ids = [c[0] for c in primary_constellations]
    primary_const_names = [c[1] for c in primary_constellations]

    rendered = MODULE_TEMPLATE.format(
        deployment_id=args.name,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        region_name=region["name"],
        region_id=region["id"],
        primary_const_names=", ".join(primary_const_names),
        primary_const_names_list=py_repr(primary_const_names),
        primary_const_ids=py_repr(primary_const_ids),
        alliance=py_repr(alliance),
        region=py_repr(region),
        friendly_alliance_ids=py_repr(inherited.get("friendly_alliance_ids", [])),
        friendly_alliances=py_repr(inherited.get("friendly_alliances", [])),
        friendly_corporations=py_repr(inherited.get("friendly_corporations", [])),
        neighbor_entities=py_repr(inherited.get("neighbor_entities", [])),
        neighbor_system_names=py_repr(neighbour_system_names),
        primary_systems=py_repr(primary_systems),
        border_systems=py_repr(border_systems),
        map_layout=py_repr(map_layout),
        map_layout_subway=py_repr(map_layout_subway),
        map_connections=py_repr(map_connections),
        pi_data=py_repr(pi_data),
    )
    return rendered


def load_inherited(path):
    """Read FRIENDLY_*/NEIGHBOR_ENTITIES from a Python module path (e.g. config.py
    or a previous deployment) so they carry over to the new deployment."""
    if not path:
        return {}
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise SystemExit(f"--inherit-from path not found: {abs_path}")
    namespace = {}
    with open(abs_path) as f:
import importlib.util
import os

def load_inherited(path):
    """Read FRIENDLY_*/NEIGHBOR_ENTITIES from a Python module path using importlib."""
    if not path:
        return {}
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        raise SystemExit(f"--inherit-from path not found: {abs_path}")

    spec = importlib.util.spec_from_file_location("inherited_config", abs_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return {
        "friendly_alliance_ids": getattr(module, "FRIENDLY_ALLIANCE_IDS", []),
        "friendly_alliances": getattr(module, "FRIENDLY_ALLIANCES", []),
        "friendly_corporations": getattr(module, "FRIENDLY_CORPORATIONS", []),
        "neighbor_entities": getattr(module, "NEIGHBOR_ENTITIES", []),
    }
    return {
        "friendly_alliance_ids": namespace.get("FRIENDLY_ALLIANCE_IDS", []),
        "friendly_alliances": namespace.get("FRIENDLY_ALLIANCES", []),
        "friendly_corporations": namespace.get("FRIENDLY_CORPORATIONS", []),
        "neighbor_entities": namespace.get("NEIGHBOR_ENTITIES", []),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Deployment ID, e.g. lawn-perrigen")
    parser.add_argument("--alliance", required=True, help="Alliance display name")
    parser.add_argument("--region", required=True, help="Region name (e.g. 'Perrigen Falls')")
    parser.add_argument("--constellations", required=True,
                        help="Comma-separated constellation names this alliance holds")
    parser.add_argument("--inherit-from",
                        help="Python file to copy FRIENDLY_*/NEIGHBOR_ENTITIES from")
    parser.add_argument("--output",
                        help="Output path (default deployments/<name-with-underscores>.py)")
    args = parser.parse_args()

    print(f"[*] Resolving alliance: {args.alliance}")
    alliance = resolve_alliance(args.alliance)
    print(f"    {alliance['id']}  {alliance['name']}  [{alliance['ticker']}]")

    print(f"[*] Resolving region: {args.region}")
    region = resolve_region(args.region)
    print(f"    {region['id']}  {region['name']}")

    const_names = [s.strip() for s in args.constellations.split(",")]
    primary_constellations = resolve_constellations(const_names)
    print(f"[*] Primary constellations:")
    for cid, cname in primary_constellations:
        print(f"    {cid}  {cname}")

    print(f"[*] Fetching all systems in region {region['id']}...")
    constellations, systems = fetch_region(region["id"])
    print(f"    {len(constellations)} constellations, {len(systems)} systems")

    print(f"[*] Walking gate graph...")
    edges = fetch_gate_destinations(systems)

    in_region = set(systems.keys())
    neighbour_sids = set()
    for sid, dests in edges.items():
        for dest in dests:
            if dest not in in_region:
                neighbour_sids.add(dest)
    print(f"    {len(neighbour_sids)} neighbour systems just outside region")

    neighbour_sys = fetch_neighbour_systems(neighbour_sids)

    print(f"[*] Building connection list...")
    map_connections = build_connections(systems, neighbour_sys, edges)

    primary_cids = [c[0] for c in primary_constellations]
    primary_sids = set()
    for cid in primary_cids:
        primary_sids.update(constellations[cid]["system_ids"])
    primary_systems = sorted(systems[sid]["name"] for sid in primary_sids)

    border = set()
    for sid in primary_sids:
        for dest in edges[sid]:
            if dest not in primary_sids:
                border.add(systems[sid]["name"])
    border_systems = sorted(border)

    neighbour_names = sorted(s["name"] for s in neighbour_sys.values())

    print(f"[*] Generating auto-layout (hand-tune the output before shipping)...")
    map_layout = auto_layout(constellations, systems, primary_cids, neighbour_sys)
    map_layout_subway = {k: dict(v) for k, v in map_layout.items()}

    print(f"[*] Fetching PI data for {len(primary_sids)} primary systems...")
    pi_data = fetch_planet_data(systems, primary_sids)
    print(f"    {sum(len(v) for v in pi_data.values())} planets indexed")

    inherited = load_inherited(args.inherit_from)
    if args.inherit_from:
        print(f"[*] Inherited friendlies from {args.inherit_from}")

    output = args.output or f"deployments/{args.name.replace('-', '_')}.py"
    rendered = render_module(
        args, alliance, region, primary_constellations,
        neighbour_names, primary_systems, border_systems,
        map_layout, map_layout_subway, map_connections, pi_data,
        inherited,
    )

    out_dir = os.path.dirname(output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    with open(output, "w") as f:
        f.write(rendered)
    print(f"[*] Wrote {output} ({os.path.getsize(output)} bytes)")
    print(f"[*] Done. Hand-tune MAP_LAYOUT before deploying.")


if __name__ == "__main__":
    main()
