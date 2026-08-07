"""Tests for the war API.

Registers war_bp on a bare Flask app rather than importing app.py, which would
call resolve_all_systems() and walk a whole region via ESI at import time.
"""

from datetime import UTC, datetime, timedelta

import pytest
from flask import Flask

import db
import wars
from routes import war_routes
from routes.war_routes import war_bp

WAR = "test-war"


class _StubModule:
    """The smallest thing wars.WarSpec accepts, standing in for a war module."""

    WAR_ID = WAR
    NAME = "Test War"
    SHORT_NAME = "TEST"
    START_DATE = "2026-03-01"
    DESCRIPTION = "A war for tests"
    REGIONS = [{"id": 10000066, "name": "Perrigen Falls"}]
    HOME_ALLIANCE_IDS = [300]
    SIDES = {
        "a": {"label": "Attackers", "short": "ATK", "color": "#ff3355",
              "alliance_ids": [100], "corporation_ids": []},
        "b": {"label": "Defenders", "short": "DEF", "color": "#00ff88",
              "alliance_ids": [200, 300], "corporation_ids": []},
    }


def FakeSpec():
    """A real WarSpec over a stub module.

    Built from the production class rather than hand-rolled, so the override
    merge and the flattened side maps under test are the ones that actually
    ship — a hand-written double silently drifts as WarSpec grows.
    """
    return wars.WarSpec(_StubModule)


@pytest.fixture
def app(tmp_db, monkeypatch):
    monkeypatch.setattr(wars, "WARS", {WAR: FakeSpec()})
    # The routes memoize aggregates for 60s; a stale entry would leak between
    # tests that write different rows.
    war_routes._clear_memo()
    flask_app = Flask(__name__)
    flask_app.config.update(TESTING=True)
    flask_app.register_blueprint(war_bp)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authed(monkeypatch):
    """Satisfy require_write_auth. Roster edits are a fleet write action."""
    import routes.auth_sso as auth_sso
    monkeypatch.setattr(auth_sso, "request_is_authorized", lambda: True)


def _ago(**kw):
    return (datetime.now(UTC) - timedelta(**kw)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(killmail_id, **kw):
    ts = kw.pop("ts", None) or _ago(hours=1)
    row = {
        "killmail_id": killmail_id, "killmail_time": ts, "hour_bucket": ts[:13],
        "region_id": 10000066, "system_id": 30000142, "system_name": "1-KCSA",
        "victim_side": "b", "killer_side": "a",
        "victim_alliance_id": 200, "victim_alliance_name": "Defenders",
        "victim_corp_id": 20, "victim_corp_name": "Def Corp",
        "victim_char_id": 2, "victim_char_name": "Def Pilot",
        "ship_type_id": 670, "ship_name": "Capsule", "ship_class": "subcap",
        "isk_value": 1000.0, "isk_destroyed": 800.0,
        "attacker_count": 5, "pilot_count": 5, "is_npc": 0, "is_awox": 0,
        "final_blow_alliance_id": 100, "attacker_alliance_ids": [100],
        "attacker_alliance_counts": {"100": 1},
        "names_resolved": 1,
    }
    row.update(kw)
    return row


class TestWarList:
    def test_lists_configured_wars(self, client):
        data = client.get("/api/wars").get_json()
        assert [w["key"] for w in data] == [WAR]
        assert data[0]["sides"]["a"]["label"] == "Attackers"

    def test_no_wars_is_an_empty_list_not_an_error(self, client, monkeypatch):
        # Wars are optional; the page hides itself rather than the API failing.
        monkeypatch.setattr(wars, "WARS", {})
        resp = client.get("/api/wars")
        assert resp.status_code == 200 and resp.get_json() == []


class TestUnknownWar:
    @pytest.mark.parametrize("path", [
        "summary", "battles", "leaderboard", "kills", "participant",
        "unclassified", "status",
    ])
    def test_404(self, client, path):
        assert client.get(f"/api/wars/nope/{path}").status_code == 404


class TestSummary:
    def test_empty_war_returns_a_zeroed_200(self, client):
        # The state the page is in before the first ingest cycle: it must
        # render, not error.
        resp = client.get(f"/api/wars/{WAR}/summary")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["totals"]["a_kills"] == 0
        assert data["coverage"]["rows"] == 0
        assert data["war"]["name"] == "Test War"

    def test_totals(self, client):
        db.record_war_kills(WAR, [_row(1), _row(2)])
        assert client.get(f"/api/wars/{WAR}/summary").get_json()["totals"]["a_kills"] == 2

    def test_days_clamped_to_the_maximum(self, client):
        assert client.get(f"/api/wars/{WAR}/summary?days=99999").get_json()["days"] == 365

    def test_days_all_means_the_whole_ledger(self, client):
        assert client.get(f"/api/wars/{WAR}/summary?days=all").get_json()["days"] == 0

    def test_garbage_days_falls_back_to_the_default(self, client):
        assert client.get(f"/api/wars/{WAR}/summary?days=abc").get_json()["days"] == 7

    def test_long_windows_roll_up_to_weeks(self, client):
        # 150 daily bars in one panel is unreadable, so wide windows bucket up.
        assert client.get(f"/api/wars/{WAR}/summary?days=all").get_json()["bucket"] == "week"
        assert client.get(f"/api/wars/{WAR}/summary?days=7").get_json()["bucket"] == "day"

    def test_explicit_bucket_is_honoured(self, client):
        assert client.get(f"/api/wars/{WAR}/summary?days=7&bucket=month").get_json()["bucket"] == "month"


class TestKills:
    def test_feed_and_cursor(self, client):
        db.record_war_kills(WAR, [_row(1), _row(2)])
        data = client.get(f"/api/wars/{WAR}/kills").get_json()
        assert len(data["kills"]) == 2
        assert data["next_before"].count("|") == 1

    def test_empty_feed_has_no_cursor(self, client):
        assert client.get(f"/api/wars/{WAR}/kills").get_json()["next_before"] is None

    def test_limit_clamped(self, client):
        db.record_war_kills(WAR, [_row(i) for i in range(1, 6)])
        assert len(client.get(f"/api/wars/{WAR}/kills?limit=2").get_json()["kills"]) == 2
        # Over the cap is clamped, not rejected.
        assert client.get(f"/api/wars/{WAR}/kills?limit=9999").status_code == 200

    def test_bad_limit_falls_back(self, client):
        assert client.get(f"/api/wars/{WAR}/kills?limit=abc").status_code == 200

    def test_side_filter(self, client):
        db.record_war_kills(WAR, [
            _row(1, victim_side="a", killer_side="b"),
            _row(2, victim_side=None, killer_side=None),
        ])
        assert len(client.get(f"/api/wars/{WAR}/kills?side=a").get_json()["kills"]) == 1


class TestParticipant:
    def test_defaults_to_the_home_alliances(self, client):
        db.record_war_kills(WAR, [_row(1, victim_alliance_id=300)])
        assert client.get(f"/api/wars/{WAR}/participant").get_json()["losses"] == 1

    def test_explicit_alliance_id(self, client):
        db.record_war_kills(WAR, [_row(1, victim_alliance_id=200)])
        assert client.get(f"/api/wars/{WAR}/participant?alliance_id=200").get_json()["losses"] == 1

    def test_bad_alliance_id_rejected(self, client):
        assert client.get(f"/api/wars/{WAR}/participant?alliance_id=abc").status_code == 400

    def test_null_when_the_war_has_no_home_side(self, client, monkeypatch):
        spec = FakeSpec()
        spec.home_alliance_ids = []
        monkeypatch.setattr(wars, "WARS", {WAR: spec})
        assert client.get(f"/api/wars/{WAR}/participant").get_json() is None


class TestStatus:
    def test_lists_every_region_even_before_first_ingest(self, client):
        data = client.get(f"/api/wars/{WAR}/status").get_json()
        assert [r["region_id"] for r in data["regions"]] == [10000066]
        assert data["regions"][0]["last_success_at"] is None
        assert data["any_gaps"] is False

    def test_reports_coverage_and_gaps(self, client):
        db.record_war_kills(WAR, [_row(1)])
        db.upsert_war_ingest_state(WAR, 10000066, saturated=1, last_success_at=_ago(minutes=5))
        data = client.get(f"/api/wars/{WAR}/status").get_json()
        assert data["rows"] == 1
        assert data["any_gaps"] is True
        assert data["coverage_since"] is not None


class TestOtherEndpoints:
    def test_battles(self, client):
        assert client.get(f"/api/wars/{WAR}/battles").get_json() == []

    def test_leaderboard(self, client):
        data = client.get(f"/api/wars/{WAR}/leaderboard").get_json()
        assert data == {"bleeders": [], "killers": []}

    def test_unclassified(self, client):
        assert client.get(f"/api/wars/{WAR}/unclassified").get_json() == []

    def test_unclassified_excludes_rostered_alliances(self, client):
        # 200 is on side b; it must not be offered as a roster suggestion even
        # when it appears on kills that resolved to no side.
        db.record_war_kills(WAR, [
            _row(i, killer_side=None, attacker_alliance_ids=[200, 777])
            for i in range(1, 5)
        ])
        listed = [r["alliance_id"] for r in
                  client.get(f"/api/wars/{WAR}/unclassified").get_json()]
        assert 200 not in listed
        assert 777 in listed


class TestRoster:
    """Roster edits made from the page.

    Stored in SQLite rather than written back to the war module, because
    private/ is mounted read-only in production.
    """

    def test_get_returns_effective_roster(self, client):
        data = client.get(f"/api/wars/{WAR}/roster").get_json()
        assert data["counts"] == {"a": 1, "b": 2, "overrides": 0}

    def test_assigning_a_side_needs_auth(self, client):
        resp = client.post(f"/api/wars/{WAR}/roster",
                           json={"entity_id": 777, "side": "b"})
        assert resp.status_code == 401

    def test_assigning_a_side(self, client, authed):
        db.record_war_kills(WAR, [_row(1, victim_alliance_id=777, victim_side=None)])
        resp = client.post(f"/api/wars/{WAR}/roster",
                           json={"entity_id": 777, "side": "b", "name": "New Ally"})
        assert resp.status_code == 200
        # The change reaches stored history, not just future kills.
        assert resp.get_json()["reclassified"] == 1
        assert client.get(f"/api/wars/{WAR}/summary").get_json()["totals"]["a_kills"] == 1

    def test_assignment_survives_into_the_roster_listing(self, client, authed):
        client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 777, "side": "a"})
        data = client.get(f"/api/wars/{WAR}/roster").get_json()
        assert data["counts"]["overrides"] == 1
        assert data["overrides"][0]["entity_id"] == 777

    def test_ruling_an_alliance_neutral_removes_it_from_a_side(self, client, authed):
        # side=null is an explicit "not a belligerent", which differs from
        # having no opinion — it also stops the suggestion panel re-offering.
        db.record_war_kills(WAR, [_row(1, victim_alliance_id=200, victim_side="b")])
        client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 200, "side": None})
        roster = client.get(f"/api/wars/{WAR}/roster").get_json()
        assert roster["counts"]["b"] == 1  # 300 remains, 200 removed
        assert client.get(f"/api/wars/{WAR}/summary").get_json()["totals"]["a_kills"] == 0

    def test_removing_an_override_reverts_to_the_module(self, client, authed):
        client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 200, "side": "a"})
        assert client.get(f"/api/wars/{WAR}/roster").get_json()["counts"]["a"] == 2
        client.delete(f"/api/wars/{WAR}/roster/200")
        counts = client.get(f"/api/wars/{WAR}/roster").get_json()["counts"]
        assert counts == {"a": 1, "b": 2, "overrides": 0}

    def test_assign_then_undo_restores_the_original_totals(self, client, authed):
        # The regression that mattered: an early version rewrote every row on
        # every edit using a rule that could not reproduce ingest, so an
        # assignment and its undo did not cancel out and the ledger drifted.
        db.record_war_kills(WAR, [
            # 777 brings the majority here, so putting it on a side flips who
            # scored the kill — the edit has to actually move the numbers for
            # the round-trip to prove anything.
            _row(1, victim_side="b", killer_side="a",
                 attacker_alliance_ids=[100, 777],
                 attacker_alliance_counts={"100": 2, "777": 9}),
            _row(2, victim_side="a", killer_side="b", victim_alliance_id=100,
                 attacker_alliance_ids=[200], attacker_alliance_counts={"200": 5}),
        ])

        def totals():
            t = client.get(f"/api/wars/{WAR}/summary?days=all").get_json()["totals"]
            return (t["a_kills"], t["b_kills"], t["a_isk"], t["b_isk"])

        original = totals()
        client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 777, "side": "b"})
        assert totals() != original
        client.delete(f"/api/wars/{WAR}/roster/777")
        assert totals() == original

    def test_only_rows_touching_the_entity_are_rewritten(self, client, authed):
        # A kill the entity was never on must keep its ingest-time answer.
        db.record_war_kills(WAR, [
            _row(1, attacker_alliance_ids=[100], attacker_alliance_counts={"100": 3}),
            _row(2, attacker_alliance_ids=[777], attacker_alliance_counts={"777": 3}),
        ])
        resp = client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 777, "side": "b"})
        assert resp.get_json()["reclassified"] == 1

    def test_majority_rule_survives_a_roster_change(self, client, authed):
        # 9 pilots from a side-b alliance against 2 from the newly-added one:
        # the reclassification must still credit the majority, exactly as
        # ingest would.
        db.record_war_kills(WAR, [
            _row(1, victim_side="a", killer_side="b", victim_alliance_id=100,
                 attacker_alliance_ids=[200, 777], final_blow_alliance_id=777,
                 attacker_alliance_counts={"200": 9, "777": 2}),
        ])
        client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 777, "side": "a"})
        feed = client.get(f"/api/wars/{WAR}/kills").get_json()["kills"]
        assert feed[0]["killer_side"] == "b"

    def test_bad_input_rejected(self, client, authed):
        assert client.post(f"/api/wars/{WAR}/roster",
                           json={"entity_id": "abc", "side": "a"}).status_code == 400
        assert client.post(f"/api/wars/{WAR}/roster",
                           json={"entity_id": 1, "side": "c"}).status_code == 400
        assert client.post(f"/api/wars/{WAR}/roster",
                           json={"entity_id": 1, "side": "a",
                                 "entity_type": "wormhole"}).status_code == 400

    def test_assigned_alliance_leaves_the_suggestion_panel(self, client, authed):
        db.record_war_kills(WAR, [
            _row(i, killer_side=None, attacker_alliance_ids=[777]) for i in range(1, 5)
        ])
        assert 777 in [r["alliance_id"] for r in
                       client.get(f"/api/wars/{WAR}/unclassified").get_json()]
        client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 777, "side": "a"})
        assert 777 not in [r["alliance_id"] for r in
                           client.get(f"/api/wars/{WAR}/unclassified").get_json()]

    def test_alliance_ruled_neutral_also_leaves_the_panel(self, client, authed):
        db.record_war_kills(WAR, [
            _row(i, killer_side=None, attacker_alliance_ids=[888]) for i in range(1, 5)
        ])
        client.post(f"/api/wars/{WAR}/roster", json={"entity_id": 888, "side": None})
        assert 888 not in [r["alliance_id"] for r in
                           client.get(f"/api/wars/{WAR}/unclassified").get_json()]


class TestMemoization:
    def test_repeat_reads_are_served_from_the_memo(self, client, monkeypatch):
        calls = []
        real = db.get_war_summary

        def counted(*a, **kw):
            calls.append(1)
            return real(*a, **kw)
        monkeypatch.setattr(db, "get_war_summary", counted)

        client.get(f"/api/wars/{WAR}/summary?days=7")
        client.get(f"/api/wars/{WAR}/summary?days=7")
        assert len(calls) == 1

    def test_different_windows_are_cached_separately(self, client, monkeypatch):
        calls = []
        real = db.get_war_summary
        monkeypatch.setattr(db, "get_war_summary",
                            lambda *a, **kw: (calls.append(1), real(*a, **kw))[1])
        client.get(f"/api/wars/{WAR}/summary?days=7")
        client.get(f"/api/wars/{WAR}/summary?days=30")
        assert len(calls) == 2
