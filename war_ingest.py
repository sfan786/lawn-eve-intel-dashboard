"""
Fetch, classify and store war kills.

Shared by the background poller (rolling window) and tools/backfill_war.py
(historical month walk) so that a kill written today and one written by a
backfill months from now go through exactly the same classification.

Kept out of routes/ because the backfill tool is a CLI with no Flask app.
"""

import logging
import time

import db
import esi_client
import war_classify

log = logging.getLogger(__name__)

# zKill serves at most this many kills per page, whatever modifiers are used.
ZKILL_PAGE_SIZE = 200
# Their published guidance is at most one request per second.
ZKILL_REQUEST_SPACING = 1.0


def _system_names(kills):
    """Resolve system IDs to names, one ESI call each but cached for 24h."""
    names = {}
    for km in kills:
        sid = km.get("solar_system_id")
        if sid and sid not in names:
            try:
                names[sid] = esi_client.get_system_info(sid).get("name", str(sid))
            except Exception:
                names[sid] = str(sid)
    return names


def store_kills(spec, region_id, kills, resolve_names=True):
    """Classify and insert a batch of raw zKill killmails. Returns rows added.

    Names are resolved in one bulk pre-pass, but a failure there is not allowed
    to lose kills: IDs are the source of truth and the row is written either
    way, with names repaired later by `resolve_pending_names`.
    """
    if not kills:
        return 0

    new = [k for k in kills if k.get("killmail_id")]
    known = db.get_known_war_kill_ids(spec.key, [k["killmail_id"] for k in new])
    fresh = [k for k in new if k["killmail_id"] not in known]
    if not fresh:
        return 0

    system_names = _system_names(fresh)

    rows = []
    for km in fresh:
        row = war_classify.classify_kill(
            km, spec,
            region_id=region_id,
            system_name=system_names.get(km.get("solar_system_id"), ""),
        )
        if row:
            rows.append(row)

    if resolve_names and rows:
        wanted = sorted({i for row in rows for i in war_classify.name_ids(row)})
        try:
            esi_client.bulk_resolve_names(wanted)
            for row in rows:
                row["victim_alliance_name"] = _name(row["victim_alliance_id"], "alliance")
                row["victim_corp_name"] = _name(row["victim_corp_id"], "corporation")
                row["victim_char_name"] = _name(row["victim_char_id"], "character")
                row["ship_name"] = (
                    esi_client.get_type_name(row["ship_type_id"]) if row["ship_type_id"] else ""
                )
                row["names_resolved"] = 1
        except Exception:
            log.warning("Name resolution failed; storing IDs and repairing later", exc_info=True)

    return db.record_war_kills(spec.key, rows)


def _name(entity_id, kind):
    if not entity_id:
        return ""
    try:
        if kind == "alliance":
            return esi_client.get_alliance_info(entity_id).get("name", "")
        if kind == "corporation":
            return esi_client.get_corporation_info(entity_id).get("name", "")
        return esi_client.get_character_name(entity_id)
    except Exception:
        return ""


def resolve_pending_names(spec, limit=900):
    """Repair rows stored without names. Returns rows updated."""
    ids = db.get_war_rows_needing_names(spec.key, limit=limit)
    if not ids:
        return 0
    try:
        esi_client.bulk_resolve_names(ids)
    except Exception:
        log.warning("Bulk name resolve failed, will retry next cycle", exc_info=True)
        return 0

    names = {}
    for entity_id in ids:
        for kind in ("alliance", "corporation", "character"):
            value = _name(entity_id, kind)
            if value:
                names[entity_id] = value
                break
        if entity_id not in names:
            names[entity_id] = esi_client.get_type_name(entity_id)
    return db.resolve_war_kill_names(spec.key, names, limit=limit)


def fetch_pages(region_id, max_pages, past_seconds=None, year=None, month=None,
                stop_before=None, spacing=ZKILL_REQUEST_SPACING):
    """Walk zKill pages for one region until the window is covered.

    Stops on the first short page (there is nothing older to get), on
    `stop_before` (a timestamp already stored), or at `max_pages`. Returns
    (kills, saturated) where saturated means the cap was hit with more to
    fetch — a possible gap the UI should own up to rather than hide.
    """
    collected = []
    saturated = False
    for page in range(1, max_pages + 1):
        if page > 1:
            time.sleep(spacing)
        batch = esi_client.get_zkill_region_kills(
            region_id, past_seconds=past_seconds, year=year, month=month, page=page
        )
        collected.extend(batch)

        if len(batch) < ZKILL_PAGE_SIZE:
            break
        oldest = min((k.get("killmail_time") or "" for k in batch), default="")
        if stop_before and oldest and oldest <= stop_before:
            break
        if page == max_pages:
            saturated = True
    return collected, saturated
