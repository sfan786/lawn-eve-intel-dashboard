"""
War ledger API.

Every endpoint here is a pure SQLite read over data the poller already
gathered — no zKillboard or ESI fan-out on the request path. That is why none
of them are rate limited: routes/limiter.py caps the endpoints that spend
somebody else's error budget, and these spend none. `days` and `limit` are
clamped instead, which is what actually bounds the work.

A short in-process memo sits in front of the aggregates because the underlying
data only changes once per poll cycle, and without it every dashboard client
polling the page would re-run the same six GROUP BYs.
"""

import time

from flask import Blueprint, jsonify, request, session

import db
import wars
from routes.auth_sso import require_write_auth

war_bp = Blueprint("war", __name__)

MAX_DAYS = 365
MAX_FEED_LIMIT = 200
MEMO_SECONDS = 60

_memo = {}


def _memoized(key, fn):
    hit = _memo.get(key)
    now = time.time()
    if hit and now - hit[0] < MEMO_SECONDS:
        return hit[1]
    value = fn()
    _memo[key] = (now, value)
    return value


def _clear_memo():
    """Used by tests, and after any write that would invalidate a cached read."""
    _memo.clear()


def _days(default=7):
    """Requested window in days. `all` (or 0) means the whole ledger."""
    raw = (request.args.get("days") or "").strip().lower()
    if raw in ("all", "0"):
        return 0
    if not raw:
        return default
    try:
        return max(1, min(MAX_DAYS, int(raw)))
    except ValueError:
        return default


def _bucket(days):
    """Time granularity. Explicit if asked for, otherwise sized to the window.

    A five-month war bucketed by day is 150 bars in a panel a few hundred
    pixels wide, so anything longer than a couple of months rolls up to weeks.
    """
    raw = (request.args.get("bucket") or "").strip().lower()
    if raw in ("day", "week", "month"):
        return raw
    if days == 0 or days > 120:
        return "week"
    return "day"


def _require_war(key):
    """The war, with page-made roster edits applied.

    Overrides are read per request rather than cached: the table holds a
    handful of rows, and a roster edit has to take effect on the next page
    load, not whenever a cache happens to expire.
    """
    spec = wars.get(key)
    if not spec:
        return None, (jsonify({"error": f"unknown war '{key}'"}), 404)
    spec.apply_overrides(db.get_war_roster_overrides(key))
    return spec, None


@war_bp.route("/api/wars")
def api_wars():
    """Every configured war. Empty when none is set up, which is not an error."""
    return jsonify([spec.to_json() for spec in wars.WARS.values()])


@war_bp.route("/api/wars/<key>/summary")
def api_war_summary(key):
    spec, err = _require_war(key)
    if err:
        return err
    days = _days()
    bucket = _bucket(days)
    data = _memoized(
        ("summary", key, days, bucket),
        lambda: db.get_war_summary(key, days=days, bucket=bucket, region_ids=spec.region_ids),
    )
    return jsonify({**data, "war": spec.to_json()})


@war_bp.route("/api/wars/<key>/battles")
def api_war_battles(key):
    spec, err = _require_war(key)
    if err:
        return err
    days = _days()
    return jsonify(_memoized(
        ("battles", key, days),
        lambda: db.get_war_battles(key, days=days, region_ids=spec.region_ids),
    ))


@war_bp.route("/api/wars/<key>/leaderboard")
def api_war_leaderboard(key):
    spec, err = _require_war(key)
    if err:
        return err
    days = _days()
    return jsonify(_memoized(
        ("leaderboard", key, days),
        lambda: db.get_war_leaderboards(key, days=days, region_ids=spec.region_ids),
    ))


@war_bp.route("/api/wars/<key>/kills")
def api_war_kills(key):
    spec, err = _require_war(key)
    if err:
        return err
    try:
        limit = max(1, min(MAX_FEED_LIMIT, int(request.args.get("limit", 50))))
    except ValueError:
        limit = 50

    kills = db.get_war_kill_feed(
        key,
        limit=limit,
        before=request.args.get("before"),
        side=request.args.get("side"),
        ship_class=request.args.get("class"),
        system_id=request.args.get("system_id"),
        min_isk=request.args.get("min_isk"),
        include_npc=request.args.get("include_npc") == "1",
        region_ids=spec.region_ids,
    )
    # Opaque cursor: the feed sorts on (time, id) together, because a fight
    # puts many kills in the same second and time alone cannot page them.
    next_before = (
        f"{kills[-1]['killmail_time']}|{kills[-1]['killmail_id']}" if kills else None
    )
    return jsonify({"kills": kills, "next_before": next_before})


@war_bp.route("/api/wars/<key>/participant")
def api_war_participant(key):
    """One alliance's own record. Defaults to the war's HOME_ALLIANCE_IDS."""
    spec, err = _require_war(key)
    if err:
        return err

    raw = request.args.get("alliance_id")
    if raw:
        try:
            alliance_ids = [int(raw)]
        except ValueError:
            return jsonify({"error": "alliance_id must be an integer"}), 400
    else:
        alliance_ids = spec.home_alliance_ids

    if not alliance_ids:
        return jsonify(None)
    days = _days()
    return jsonify(_memoized(
        ("participant", key, tuple(alliance_ids), days),
        lambda: db.get_war_participant(key, alliance_ids, days=days, region_ids=spec.region_ids),
    ))


@war_bp.route("/api/wars/<key>/unclassified")
def api_war_unclassified(key):
    """Alliances fighting here that are on neither roster."""
    spec, err = _require_war(key)
    if err:
        return err
    days = _days()
    return jsonify(_memoized(
        ("unclassified", key, days),
        lambda: db.get_war_unclassified(
            key, days=days, region_ids=spec.region_ids,
            # Everything already decided — both rosters plus anything ruled
            # neutral from the page — so the panel only ever shows entities
            # nobody has judged yet.
            known_alliance_ids=list(spec.decided_alliance_ids),
        ),
    ))


@war_bp.route("/api/wars/<key>/roster", methods=["GET"])
def api_war_roster(key):
    """The war's effective rosters, and which entries came from the page."""
    spec, err = _require_war(key)
    if err:
        return err
    overrides = db.get_war_roster_overrides(key)
    return jsonify({
        "sides": spec.sides,
        "overrides": overrides,
        "counts": {
            "a": sum(1 for s in spec.side_by_alliance.values() if s == "a"),
            "b": sum(1 for s in spec.side_by_alliance.values() if s == "b"),
            "overrides": len(overrides),
        },
    })


@war_bp.route("/api/wars/<key>/roster", methods=["POST"])
@require_write_auth
def api_war_roster_set(key):
    """Assign an entity to a side from the page.

    Stored in the database, not written back into the war module: private/ is
    mounted read-only in production, and an app that edits its own config
    leaves nobody able to review what the roster actually is.

    The change is applied to stored history too, which is the point — a war's
    membership is discovered as it goes, and a correction that only affected
    future kills would leave the totals permanently wrong.
    """
    spec, err = _require_war(key)
    if err:
        return err

    body = request.get_json(silent=True) or {}
    try:
        entity_id = int(body.get("entity_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "entity_id must be an integer"}), 400

    side = body.get("side")
    if side not in ("a", "b", None):
        return jsonify({"error": "side must be 'a', 'b' or null"}), 400
    entity_type = body.get("entity_type", "alliance")
    if entity_type not in ("alliance", "corporation"):
        return jsonify({"error": "entity_type must be 'alliance' or 'corporation'"}), 400

    db.set_war_roster_override(
        key, entity_type, entity_id, side,
        name=(body.get("name") or "")[:100],
        added_by=session.get("character_name", ""),
    )

    spec.apply_overrides(db.get_war_roster_overrides(key))
    updated = db.reclassify_war_kills(
        key, spec, region_ids=spec.region_ids, entity_id=entity_id)
    _clear_memo()
    return jsonify({"ok": True, "reclassified": updated})


@war_bp.route("/api/wars/<key>/roster/<int:entity_id>", methods=["DELETE"])
@require_write_auth
def api_war_roster_delete(key, entity_id):
    """Remove an override, reverting to what the war module says."""
    spec, err = _require_war(key)
    if err:
        return err
    entity_type = request.args.get("entity_type", "alliance")
    db.delete_war_roster_override(key, entity_type, entity_id)

    spec.apply_overrides(db.get_war_roster_overrides(key))
    updated = db.reclassify_war_kills(
        key, spec, region_ids=spec.region_ids, entity_id=entity_id)
    _clear_memo()
    return jsonify({"ok": True, "reclassified": updated})


@war_bp.route("/api/wars/<key>/status")
def api_war_status(key):
    """Ingest health per region.

    Deliberately public and prominent: the ledger is assembled from a paginated
    feed behind an hour-long CDN cache, so the page has to be able to say how
    stale it is and whether a region reported a gap, rather than presenting a
    partial record as a complete one.
    """
    spec, err = _require_war(key)
    if err:
        return err

    state = {s["region_id"]: s for s in db.get_war_ingest_state(key)}
    regions = []
    for region_id in spec.region_ids:
        s = state.get(region_id) or {}
        regions.append({
            "region_id": region_id,
            "region_name": spec.region_names.get(region_id, str(region_id)),
            "last_success_at": s.get("last_success_at"),
            "last_kill_time": s.get("last_kill_time"),
            "new_kills": s.get("new_kills") or 0,
            "saturated": bool(s.get("saturated")),
            "last_error": s.get("last_error"),
        })

    summary = db.get_war_summary(key, days=0, region_ids=spec.region_ids)
    return jsonify({
        "war_id": key,
        "regions": regions,
        "coverage_since": summary["coverage"]["first_kill"],
        "last_kill": summary["coverage"]["last_kill"],
        "rows": summary["coverage"]["rows"],
        "any_gaps": any(r["saturated"] for r in regions),
    })
