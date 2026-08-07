"""Tests for the war ingest cycle.

Network is stubbed at esi_client, so nothing here touches zKillboard or ESI.
The fixture in tests/fixtures/zkill_region.json is trimmed from a real
Perrigen Falls response and deliberately keeps one structure kill, one NPC
kill and one fighter kill — the cases that classify differently.
"""

import json
import os

import pytest

import db
import esi_client
import war_ingest
import wars
from routes import war_poller

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "zkill_region.json")
REGION = 10000066


class _StubModule:
    """Minimal war module for wars.WarSpec.

    The alliance IDs are the ones in the checked-in fixture, so at least one
    killmail classifies as a belligerent loss.
    """

    WAR_ID = "test-war"
    NAME = "Test War"
    START_DATE = "2026-03-01"
    REGIONS = [{"id": REGION, "name": "Perrigen Falls"}]
    HOME_ALLIANCE_IDS = []
    SIDES = {
        "a": {"label": "A", "alliance_ids": [99007887], "corporation_ids": []},
        "b": {"label": "B", "alliance_ids": [1411711376, 99014948], "corporation_ids": []},
    }


def FakeSpec():
    """A real WarSpec, so the poller is tested against the shipping class."""
    return wars.WarSpec(_StubModule)


@pytest.fixture
def spec():
    return FakeSpec()


@pytest.fixture
def kills():
    with open(FIXTURE) as f:
        return json.load(f)


@pytest.fixture
def no_names(monkeypatch):
    """Stub out every name lookup, counting calls so tests can assert on them."""
    calls = {"bulk": 0, "system": 0}

    def bulk(ids):
        calls["bulk"] += 1

    def system_info(sid):
        calls["system"] += 1
        return {"name": f"SYS-{sid}"}

    monkeypatch.setattr(esi_client, "bulk_resolve_names", bulk)
    monkeypatch.setattr(esi_client, "get_system_info", system_info)
    monkeypatch.setattr(esi_client, "get_type_name", lambda t: f"Type{t}")
    monkeypatch.setattr(esi_client, "get_type_group_id", lambda t: 26)
    monkeypatch.setattr(esi_client, "get_alliance_info", lambda i: {"name": f"Alliance{i}"})
    monkeypatch.setattr(esi_client, "get_corporation_info", lambda i: {"name": f"Corp{i}"})
    monkeypatch.setattr(esi_client, "get_character_name", lambda i: f"Pilot{i}")
    return calls


# ---------------------------------------------------------------------------
# store_kills
# ---------------------------------------------------------------------------

class TestStoreKills:
    def test_stores_every_killmail(self, tmp_db, spec, kills, no_names):
        assert war_ingest.store_kills(spec, REGION, kills) == len(kills)

    def test_second_pass_stores_nothing_and_resolves_nothing(self, tmp_db, spec, kills, no_names):
        war_ingest.store_kills(spec, REGION, kills)
        before = no_names["bulk"]
        assert war_ingest.store_kills(spec, REGION, kills) == 0
        # Already-stored kills must not cost another round of lookups.
        assert no_names["bulk"] == before

    def test_classifies_the_awkward_cases(self, tmp_db, spec, kills, no_names):
        war_ingest.store_kills(spec, REGION, kills)
        rows = db.get_war_kill_feed(spec.key, limit=50, include_npc=True)
        classes = {r["ship_class"] for r in rows}
        assert "structure" in classes
        assert "fighter" in classes
        assert any(r["is_npc"] for r in rows)

    def test_survives_name_resolution_failure(self, tmp_db, spec, kills, monkeypatch):
        # IDs are the source of truth; a name outage must not lose kills.
        monkeypatch.setattr(esi_client, "get_system_info", lambda s: {"name": "X"})
        monkeypatch.setattr(esi_client, "get_type_group_id", lambda t: 26)

        def boom(ids):
            raise RuntimeError("ESI down")
        monkeypatch.setattr(esi_client, "bulk_resolve_names", boom)

        assert war_ingest.store_kills(spec, REGION, kills) == len(kills)
        assert db.get_war_rows_needing_names(spec.key)

    def test_empty_batch(self, tmp_db, spec, no_names):
        assert war_ingest.store_kills(spec, REGION, []) == 0


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class TestEmptyWindow:
    def test_null_entries_are_filtered(self, monkeypatch):
        # zKill returns `[null]` rather than `[]` for a window with no kills.
        # Verified against the live API; it crashed the ingest before this.
        class Resp:
            status_code = 200
            headers = {}

            def raise_for_status(self):
                pass

            def json(self):
                return [None]

        monkeypatch.setattr(esi_client._session, "get", lambda *a, **kw: Resp())
        assert esi_client.get_zkill_region_kills(REGION, past_seconds=600) == []

    def test_quiet_region_stores_nothing_without_erroring(self, tmp_db, spec, no_names, monkeypatch):
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", lambda *a, **kw: [])
        assert war_poller.poll_region(spec, REGION, {}) == 0
        assert db.get_war_ingest_state(spec.key)[0]["last_error"] is None


class TestFetchPages:
    def test_stops_on_a_short_page(self, monkeypatch):
        seen = []

        def fetch(region_id, past_seconds=None, year=None, month=None, page=1):
            seen.append(page)
            return [{"killmail_id": page, "killmail_time": "2026-08-06T00:00:00Z"}]
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", fetch)

        kills, saturated = war_ingest.fetch_pages(REGION, max_pages=5, spacing=0)
        assert seen == [1] and len(kills) == 1 and saturated is False

    def test_walks_on_when_a_page_is_full(self, monkeypatch):
        pages = {
            1: [{"killmail_id": i, "killmail_time": "2026-08-06T12:00:00Z"} for i in range(200)],
            2: [{"killmail_id": 500, "killmail_time": "2026-08-05T12:00:00Z"}],
        }
        monkeypatch.setattr(esi_client, "get_zkill_region_kills",
                            lambda region_id, page=1, **kw: pages.get(page, []))
        kills, saturated = war_ingest.fetch_pages(REGION, max_pages=5, spacing=0)
        assert len(kills) == 201 and saturated is False

    def test_reports_saturation_at_the_cap(self, monkeypatch):
        full = [{"killmail_id": i, "killmail_time": "2026-08-06T12:00:00Z"} for i in range(200)]
        monkeypatch.setattr(esi_client, "get_zkill_region_kills",
                            lambda region_id, page=1, **kw: list(full))
        kills, saturated = war_ingest.fetch_pages(REGION, max_pages=2, spacing=0)
        assert saturated is True and len(kills) == 400

    def test_stops_once_it_reaches_the_cursor(self, monkeypatch):
        pages = {
            1: [{"killmail_id": i, "killmail_time": "2026-08-06T12:00:00Z"} for i in range(200)],
            2: [{"killmail_id": i, "killmail_time": "2026-08-01T00:00:00Z"} for i in range(200)],
            3: [{"killmail_id": 9, "killmail_time": "2026-07-01T00:00:00Z"}],
        }
        calls = []

        def fetch(region_id, page=1, **kw):
            calls.append(page)
            return pages.get(page, [])
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", fetch)

        war_ingest.fetch_pages(REGION, max_pages=9, stop_before="2026-08-03T00:00:00Z", spacing=0)
        assert calls == [1, 2]


# ---------------------------------------------------------------------------
# Cycle behaviour
# ---------------------------------------------------------------------------

class TestPollRegion:
    def test_stores_and_advances_the_cursor(self, tmp_db, spec, kills, no_names, monkeypatch):
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", lambda *a, **kw: kills)
        assert war_poller.poll_region(spec, REGION, {}) == len(kills)
        state = db.get_war_ingest_state(spec.key)[0]
        assert state["last_kill_time"] == max(k["killmail_time"] for k in kills)
        assert state["last_error"] is None

    def test_a_failed_fetch_leaves_the_cursor_alone(self, tmp_db, spec, no_names, monkeypatch):
        # The regression that matters: treating an outage as "no kills" would
        # advance the high-water mark past a window that was never fetched.
        db.upsert_war_ingest_state(spec.key, REGION, last_kill_time="2026-08-01T00:00:00Z")
        state_before = {REGION: db.get_war_ingest_state(spec.key)[0]}

        def boom(*a, **kw):
            raise RuntimeError("zkill timeout")
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", boom)

        assert war_poller.poll_region(spec, REGION, state_before) == 0
        state = db.get_war_ingest_state(spec.key)[0]
        assert state["last_kill_time"] == "2026-08-01T00:00:00Z"
        assert "zkill timeout" in state["last_error"]

    def test_picks_up_where_a_backfill_left_off(self, tmp_db, spec, kills, no_names, monkeypatch):
        # A backfill writes rows but no ingest cursor. Without falling back to
        # the ledger the first cycle would ask for a full week already stored.
        war_ingest.store_kills(spec, REGION, kills)
        assert db.get_war_ingest_state(spec.key) == []

        asked = {}

        def fetch(region_id, past_seconds=None, **kw):
            asked["past_seconds"] = past_seconds
            return []
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", fetch)

        war_poller.poll_region(spec, REGION, {})
        assert asked["past_seconds"] < 604800

    def test_records_saturation(self, tmp_db, spec, no_names, monkeypatch):
        full = [
            {"killmail_id": i, "killmail_time": "2026-08-06T12:00:00Z",
             "victim": {}, "attackers": [], "zkb": {}, "solar_system_id": 30000142}
            for i in range(200)
        ]
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", lambda *a, **kw: list(full))
        monkeypatch.setattr(war_poller, "WAR_MAX_PAGES_PER_CYCLE", 1)
        war_poller.poll_region(spec, REGION, {})
        assert db.get_war_ingest_state(spec.key)[0]["saturated"] == 1


class TestPollWar:
    def test_lease_stops_a_second_worker(self, tmp_db, spec, kills, no_names, monkeypatch):
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", lambda *a, **kw: kills)
        assert war_poller.poll_war(spec) == len(kills)
        # A different process must not repeat the fetch — the point of the
        # lease is that a duplicate cycle costs megabytes, not one call.
        monkeypatch.setattr(war_poller, "_owner", lambda: "someone-else:999")
        assert war_poller.poll_war(spec) == 0

    def test_one_bad_region_does_not_stop_the_rest(self, tmp_db, spec, kills, no_names, monkeypatch):
        spec.region_ids = [REGION, 10000053]

        def fetch(region_id, **kw):
            if region_id == REGION:
                raise RuntimeError("down")
            return kills
        monkeypatch.setattr(esi_client, "get_zkill_region_kills", fetch)
        assert war_poller.poll_war(spec) == len(kills)


class TestWindow:
    def test_no_cursor_asks_for_the_maximum(self):
        assert war_poller._window_seconds(None) == 604800

    def test_unparseable_cursor_asks_for_the_maximum(self):
        assert war_poller._window_seconds("not-a-date") == 604800

    def test_window_is_never_below_the_floor(self):
        from datetime import UTC, datetime
        now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert war_poller._window_seconds(now) >= 600

    def test_window_grows_with_the_gap(self):
        from datetime import UTC, datetime, timedelta
        old = (datetime.now(UTC) - timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        recent = (datetime.now(UTC) - timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert war_poller._window_seconds(old) > war_poller._window_seconds(recent)
