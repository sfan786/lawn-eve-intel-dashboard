"""
Demo-mode war ledger.

Serves the same shapes as routes/war_routes.py from `mock_data`'s synthetic
war, so /war renders in demo mode with no database and no network. Values are
derived deterministically per period/system, not randomised per request — a
demo that reshuffles on every refresh hides UI regressions.
"""

from flask import Blueprint, jsonify, request

from mock.mock_data import (
    MOCK_WAR,
    MOCK_WAR_BATTLES,
    MOCK_WAR_KILLS,
    MOCK_WAR_LEADERBOARD,
    MOCK_WAR_PARTICIPANT,
    MOCK_WAR_STATUS,
    MOCK_WAR_SUMMARY,
    MOCK_WAR_UNCLASSIFIED,
)

mock_war_bp = Blueprint("mock_war", __name__)

_KEY = MOCK_WAR["key"]


def _guard(key):
    if key != _KEY:
        return jsonify({"error": f"unknown war '{key}'"}), 404
    return None


@mock_war_bp.route("/api/wars")
def api_wars():
    return jsonify([MOCK_WAR])


@mock_war_bp.route("/api/wars/<key>/summary")
def api_war_summary(key):
    return _guard(key) or jsonify({**MOCK_WAR_SUMMARY, "war": MOCK_WAR})


@mock_war_bp.route("/api/wars/<key>/battles")
def api_war_battles(key):
    return _guard(key) or jsonify(MOCK_WAR_BATTLES)


@mock_war_bp.route("/api/wars/<key>/leaderboard")
def api_war_leaderboard(key):
    return _guard(key) or jsonify(MOCK_WAR_LEADERBOARD)


@mock_war_bp.route("/api/wars/<key>/kills")
def api_war_kills(key):
    guard = _guard(key)
    if guard:
        return guard
    side = request.args.get("side")
    ship_class = request.args.get("class")
    kills = MOCK_WAR_KILLS
    if side in ("a", "b"):
        kills = [k for k in kills if side in (k["victim_side"], k["killer_side"])]
    if ship_class:
        kills = [k for k in kills if k["ship_class"] == ship_class]
    return jsonify({"kills": kills, "next_before": None})


@mock_war_bp.route("/api/wars/<key>/participant")
def api_war_participant(key):
    return _guard(key) or jsonify(MOCK_WAR_PARTICIPANT)


@mock_war_bp.route("/api/wars/<key>/unclassified")
def api_war_unclassified(key):
    return _guard(key) or jsonify(MOCK_WAR_UNCLASSIFIED)


@mock_war_bp.route("/api/wars/<key>/roster")
def api_war_roster(key):
    return _guard(key) or jsonify({
        "sides": MOCK_WAR["sides"],
        "overrides": [],
        "counts": {"a": 4, "b": 12, "overrides": 0},
    })


@mock_war_bp.route("/api/wars/<key>/roster", methods=["POST"])
def api_war_roster_set(key):
    """Demo mode has no database, so roster edits are accepted and discarded.

    Answering 200 keeps the buttons exercisable in a demo; answering 401 would
    make the panel look broken rather than sandboxed.
    """
    return _guard(key) or jsonify({"ok": True, "reclassified": 0, "demo": True})


@mock_war_bp.route("/api/wars/<key>/roster/<int:entity_id>", methods=["DELETE"])
def api_war_roster_delete(key, entity_id):
    return _guard(key) or jsonify({"ok": True, "reclassified": 0, "demo": True})


@mock_war_bp.route("/api/wars/<key>/status")
def api_war_status(key):
    return _guard(key) or jsonify(MOCK_WAR_STATUS)
