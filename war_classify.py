"""
Turn a raw zKillboard killmail into a classified war-ledger row.

Everything here is a pure function over a plain dict: no database, no network,
no globals. That is deliberate on three counts.

  * It makes the interesting logic — which side lost that ship — testable from
    a JSON fixture, with no fake HTTP and no temp database.
  * The ingest path and the backfill tool share one implementation, so history
    written months apart classifies identically.
  * The zKillboard REST feed and the RedisQ stream hand out the *same* killmail
    shape. Swapping the ingest to RedisQ later is then a change of transport
    only, with no schema migration and no reclassification.

Why the killmail arrives complete: zKill's /kills/ endpoints embed the full
`victim` and `attackers` blocks alongside the `zkb` metadata, so no ESI
killmail fetch is needed to classify one. (The older kill-feed routes in this
repo do fetch from ESI; they predate that discovery.)
"""

import esi_client
from eve_constants import (
    CAPITAL_GROUP_IDS,
    KILL_CATEGORY_CLASSES,
    POD_GROUP_IDS,
    SUPER_GROUP_IDS,
)

# An attacker list longer than this is a structure bash or a supercap fight;
# the tail adds nothing to a leaderboard and would bloat every row.
MAX_STORED_ATTACKER_ALLIANCES = 40


def ship_class_from_group(group_id: int) -> str:
    """Coarse hull bucket from an EVE ship group ID."""
    if group_id in SUPER_GROUP_IDS:
        return "super"
    if group_id in CAPITAL_GROUP_IDS:
        return "capital"
    if group_id in POD_GROUP_IDS:
        return "pod"
    return "subcap"


def _categories(zkb: dict) -> set:
    """Victim category IDs from zKill's `cat:N` labels."""
    cats = set()
    for label in zkb.get("labels") or []:
        if isinstance(label, str) and label.startswith("cat:"):
            try:
                cats.add(int(label[4:]))
            except ValueError:
                continue
    return cats


def ship_class(km: dict, resolve_group=None) -> str:
    """Hull bucket for a killmail's victim.

    Reads zKill's category label first: it is already in the payload, and it is
    the only thing that distinguishes a structure or a fighter from a ship.
    Falls back to an ESI group lookup for ordinary ships, where the category
    (6, "Ship") does not say which *kind* of ship died.
    """
    for cat in _categories(km.get("zkb") or {}):
        if cat in KILL_CATEGORY_CLASSES:
            return KILL_CATEGORY_CLASSES[cat]

    type_id = (km.get("victim") or {}).get("ship_type_id")
    if not type_id:
        return "subcap"
    lookup = resolve_group or esi_client.get_type_group_id
    try:
        return ship_class_from_group(lookup(type_id))
    except Exception:
        # A missing hull bucket is cosmetic; never lose a row over it.
        return "subcap"


def side_of(alliance_id, corporation_id, spec) -> str | None:
    """Which side an entity fights for, or None if it is on neither roster.

    Corporation membership is checked first: a corp is listed explicitly only
    when it needs to differ from its alliance, so the more specific statement
    has to win.
    """
    if corporation_id and corporation_id in spec.side_by_corp:
        return spec.side_by_corp[corporation_id]
    if alliance_id and alliance_id in spec.side_by_alliance:
        return spec.side_by_alliance[alliance_id]
    return None


def _killer_side(attackers, spec) -> tuple[str | None, int | None]:
    """The side that scored the kill, and the final blow's alliance.

    Decided by weight of numbers rather than by the final blow, because the
    last shot is often a straggler or an opportunist. The final blow only
    breaks a tie, which is what makes a genuinely mixed gank resolve at all.
    """
    counts = {}
    final_blow_alliance = None
    final_blow_side = None

    for att in attackers or []:
        alliance_id = att.get("alliance_id")
        side = side_of(alliance_id, att.get("corporation_id"), spec)
        if att.get("final_blow"):
            final_blow_alliance = alliance_id
            final_blow_side = side
        # NPC attackers carry no character_id and must not vote.
        if side and att.get("character_id"):
            counts[side] = counts.get(side, 0) + 1

    if not counts:
        return None, final_blow_alliance

    best = max(counts.values())
    leaders = [s for s, n in counts.items() if n == best]
    if len(leaders) == 1:
        return leaders[0], final_blow_alliance
    # Tied: defer to whoever landed the killing blow, if they were involved.
    if final_blow_side in leaders:
        return final_blow_side, final_blow_alliance
    return sorted(leaders)[0], final_blow_alliance


def classify_kill(km: dict, spec, region_id=None, system_name="", resolve_group=None) -> dict | None:
    """Build a `war_kills` row from a raw zKill killmail.

    Returns None only for a payload too malformed to store. Kills involving
    neither side are still returned: they are third-party activity in the war
    zone, and — more practically — a row that is fetched and dropped gets
    re-fetched and re-dropped on every later cycle, so storing it is what makes
    the "already seen" filter a true high-water mark.
    """
    killmail_id = km.get("killmail_id")
    killmail_time = km.get("killmail_time")
    if not killmail_id or not killmail_time:
        return None

    zkb = km.get("zkb") or {}
    victim = km.get("victim") or {}
    attackers = km.get("attackers") or []

    victim_alliance = victim.get("alliance_id")
    victim_corp = victim.get("corporation_id")
    victim_side = side_of(victim_alliance, victim_corp, spec)
    killer_side, final_blow_alliance = _killer_side(attackers, spec)

    # Distinct alliances (for leaderboards) plus how many pilots each brought.
    # The counts are what make a later reclassification able to reproduce the
    # majority rule below exactly, instead of guessing from presence alone —
    # without them, editing a roster silently rewrites unrelated kills.
    attacker_alliances = []
    attacker_counts = {}
    for att in attackers:
        aid = att.get("alliance_id")
        if not aid:
            continue
        if aid not in attacker_counts and len(attacker_counts) >= MAX_STORED_ATTACKER_ALLIANCES:
            continue
        if aid not in attacker_counts:
            attacker_alliances.append(aid)
            attacker_counts[aid] = 0
        # Only pilots vote, matching _killer_side: NPCs carry no character_id.
        if att.get("character_id"):
            attacker_counts[aid] += 1

    return {
        "killmail_id": killmail_id,
        "killmail_time": killmail_time,
        "hour_bucket": killmail_time[:13],
        "region_id": region_id or 0,
        "system_id": km.get("solar_system_id") or 0,
        "system_name": system_name or "",
        "victim_side": victim_side,
        "killer_side": killer_side,
        "victim_alliance_id": victim_alliance,
        "victim_alliance_name": "",
        "victim_corp_id": victim_corp,
        "victim_corp_name": "",
        "victim_char_id": victim.get("character_id"),
        "victim_char_name": "",
        "ship_type_id": victim.get("ship_type_id"),
        "ship_name": "",
        "ship_class": ship_class(km, resolve_group=resolve_group),
        "isk_value": float(zkb.get("totalValue") or 0),
        # Dropped loot survives the fight; only destroyedValue is destruction.
        "isk_destroyed": float(zkb.get("destroyedValue") or 0),
        "attacker_count": len(attackers),
        "pilot_count": sum(1 for a in attackers if a.get("character_id")),
        "is_npc": 1 if zkb.get("npc") else 0,
        "is_awox": 1 if zkb.get("awox") else 0,
        "final_blow_alliance_id": final_blow_alliance,
        "attacker_alliance_ids": attacker_alliances,
        "attacker_alliance_counts": attacker_counts,
        "names_resolved": 0,
    }


def name_ids(row: dict) -> list:
    """Entity IDs in a row that need a name, for one bulk resolve pre-pass."""
    return [
        v
        for v in (
            row.get("victim_alliance_id"),
            row.get("victim_corp_id"),
            row.get("victim_char_id"),
            row.get("ship_type_id"),
        )
        if v
    ]
