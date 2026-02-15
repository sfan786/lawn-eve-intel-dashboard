"""
ESI/zKill entity lookup utility.
Resolves alliance, corporation, and system names to numeric IDs.

Usage:
    python tools/esi_lookup.py alliance "The Rejected"
    python tools/esi_lookup.py corporation "Astrum Mechanica"
    python tools/esi_lookup.py system "UDVW-O"
    python tools/esi_lookup.py zkill "Deepwater Hooligans"
"""

import argparse
import json
import os
import sys

# Add project root so we can import esi_client
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import esi_client

ZKILL_AUTOCOMPLETE = "https://zkillboard.com/autocomplete/"
USER_AGENT = "AstrumMechanica-IntelDash/1.0 (contact: in-game)"


def resolve_names(names):
    """Resolve names to IDs via POST /universe/ids/. Returns full response dict."""
    try:
        return esi_client.post_universe_ids(names)
    except Exception as e:
        print(f"ESI resolve error: {e}", file=sys.stderr)
        return {}


def search_zkill(term, entity_type=None):
    """Search zKillboard autocomplete. Returns list of {id, name, type}."""
    try:
        resp = requests.get(
            f"{ZKILL_AUTOCOMPLETE}{term}/",
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if entity_type:
            results = [r for r in results if r.get("type") == entity_type]
        return results
    except Exception as e:
        print(f"zKill search error: {e}", file=sys.stderr)
        return []


def cmd_alliance(args):
    """Search for alliances by name.

    Uses ESI POST /universe/ids/ for exact match, then enriches with
    alliance details (ticker). Falls back to zKill autocomplete for
    fuzzy matching if ESI finds nothing.
    """
    data = resolve_names([args.term])
    matches = data.get("alliances", [])

    if not matches:
        # Fall back to zKill autocomplete for fuzzy/partial matches
        print(f"No exact ESI match — trying zKill autocomplete...", file=sys.stderr)
        zkill_results = search_zkill(args.term, entity_type="alliance")
        if not zkill_results:
            print(f"No alliances found for '{args.term}'")
            return
        if args.json:
            print(json.dumps(zkill_results, indent=2))
        else:
            for r in zkill_results:
                print(f"  {r['id']:>12}  {r['name']}  (via zKill)")
        return

    results = []
    for m in matches:
        aid = m["id"]
        try:
            info = esi_client.get_alliance_info(aid)
            entry = {"id": aid, "name": info.get("name"), "ticker": info.get("ticker")}
            results.append(entry)
            if not args.json:
                print(f"  {aid:>12}  {entry['name']}  [{entry['ticker']}]")
        except Exception as e:
            if not args.json:
                print(f"  {aid:>12}  {m['name']}  (detail fetch failed: {e})")
            results.append({"id": aid, "name": m["name"]})

    if args.json:
        print(json.dumps(results, indent=2))


def cmd_corporation(args):
    """Search for corporations by name. Same strategy as alliance."""
    data = resolve_names([args.term])
    matches = data.get("corporations", [])

    if not matches:
        print(f"No exact ESI match — trying zKill autocomplete...", file=sys.stderr)
        zkill_results = search_zkill(args.term, entity_type="corporation")
        if not zkill_results:
            print(f"No corporations found for '{args.term}'")
            return
        if args.json:
            print(json.dumps(zkill_results, indent=2))
        else:
            for r in zkill_results:
                print(f"  {r['id']:>12}  {r['name']}  (via zKill)")
        return

    results = []
    for m in matches:
        cid = m["id"]
        try:
            info = esi_client.get_corporation_info(cid)
            entry = {"id": cid, "name": info.get("name"), "ticker": info.get("ticker")}
            results.append(entry)
            if not args.json:
                print(f"  {cid:>12}  {entry['name']}  [{entry['ticker']}]")
        except Exception as e:
            if not args.json:
                print(f"  {cid:>12}  {m['name']}  (detail fetch failed: {e})")
            results.append({"id": cid, "name": m["name"]})

    if args.json:
        print(json.dumps(results, indent=2))


def cmd_system(args):
    """Resolve system name to ID via POST /universe/ids/."""
    try:
        data = esi_client.post_universe_ids([args.term])
        systems = data.get("systems", [])
        if not systems:
            print(f"No systems found for '{args.term}'")
            return

        if args.json:
            print(json.dumps(systems, indent=2))
        else:
            for s in systems:
                print(f"  {s['id']:>12}  {s['name']}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)


def cmd_zkill(args):
    """Search zKillboard autocomplete."""
    results = search_zkill(args.term, entity_type=args.type)
    if not results:
        print(f"No zKill results for '{args.term}'")
        return

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for r in results:
            print(f"  {r.get('id', '?'):>12}  {r.get('name')}  ({r.get('type')})")


def main():
    parser = argparse.ArgumentParser(
        description="ESI/zKill entity lookup — resolve names to IDs for config.py"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="command", required=True)

    p_a = sub.add_parser("alliance", help="Search alliances by name")
    p_a.add_argument("term", help="Alliance name (exact match via ESI, fuzzy via zKill fallback)")

    p_c = sub.add_parser("corporation", help="Search corporations by name")
    p_c.add_argument("term", help="Corporation name (exact match via ESI, fuzzy via zKill fallback)")

    p_s = sub.add_parser("system", help="Resolve system name to ID")
    p_s.add_argument("term", help="System name (e.g. UDVW-O)")

    p_z = sub.add_parser("zkill", help="Search zKillboard autocomplete")
    p_z.add_argument("term", help="Search term")
    p_z.add_argument(
        "--type",
        choices=["alliance", "corporation", "character"],
        help="Filter by entity type",
    )

    args = parser.parse_args()
    handlers = {
        "alliance": cmd_alliance,
        "corporation": cmd_corporation,
        "system": cmd_system,
        "zkill": cmd_zkill,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
