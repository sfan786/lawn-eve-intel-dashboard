"""Tests for the war ledger tables and aggregates (uses the tmp_db fixture)."""

import sqlite3
from datetime import UTC, datetime, timedelta

import db

WAR = "test-war"


def _conn(tmp_db):
    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    return conn


def _count(tmp_db, table, where="1=1"):
    with _conn(tmp_db) as c:
        return c.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]


def _ago(**kw):
    """ISO timestamp in the past. Never hardcode dates — windowed queries
    would turn green today and fail permanently later."""
    return (datetime.now(UTC) - timedelta(**kw)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row(killmail_id, ts=None, **kw):
    ts = ts or _ago(hours=1)
    row = {
        "killmail_id": killmail_id,
        "killmail_time": ts,
        "hour_bucket": ts[:13],
        "region_id": 10000066,
        "system_id": 30000142,
        "system_name": "1-KCSA",
        "victim_side": "b",
        "killer_side": "a",
        "victim_alliance_id": 200,
        "victim_alliance_name": "Defenders",
        "victim_corp_id": 20,
        "victim_corp_name": "Def Corp",
        "victim_char_id": 2,
        "victim_char_name": "Def Pilot",
        "ship_type_id": 670,
        "ship_name": "Capsule",
        "ship_class": "subcap",
        "isk_value": 1000.0,
        "isk_destroyed": 800.0,
        "attacker_count": 5,
        "pilot_count": 5,
        "is_npc": 0,
        "is_awox": 0,
        "final_blow_alliance_id": 100,
        "attacker_alliance_ids": [100],
        "names_resolved": 1,
    }
    row.update(kw)
    return row


# ---------------------------------------------------------------------------
# Writes and dedup
# ---------------------------------------------------------------------------

class TestRecordWarKills:
    def test_insert_returns_count(self, tmp_db):
        assert db.record_war_kills(WAR, [_row(1), _row(2)]) == 2
        assert _count(tmp_db, "war_kills") == 2

    def test_reinsert_is_a_no_op(self, tmp_db):
        rows = [_row(1), _row(2)]
        db.record_war_kills(WAR, rows)
        assert db.record_war_kills(WAR, rows) == 0
        assert _count(tmp_db, "war_kills") == 2

    def test_empty_batch(self, tmp_db):
        assert db.record_war_kills(WAR, []) == 0

    def test_same_killmail_in_two_wars_is_two_rows(self, tmp_db):
        # Pins the composite primary key: two wars can legitimately cover the
        # same region, and each needs its own classification of the same kill.
        db.record_war_kills(WAR, [_row(1)])
        db.record_war_kills("other-war", [_row(1)])
        assert _count(tmp_db, "war_kills") == 2

    def test_attacker_alliances_round_trip_as_json(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, attacker_alliance_ids=[100, 101, 102])])
        with _conn(tmp_db) as c:
            raw = c.execute("SELECT attacker_alliance_ids FROM war_kills").fetchone()[0]
        assert raw == "[100, 101, 102]"

    def test_ledger_is_not_scoped_by_deployment(self, tmp_db, monkeypatch):
        # A war outlives a deployment; switching homes must not hide the record.
        db.record_war_kills(WAR, [_row(1)])
        monkeypatch.setattr(db, "DEPLOYMENT_ID", "some_other_deployment")
        assert db.get_war_summary(WAR, days=0)["coverage"]["rows"] == 1


class TestKnownIds:
    def test_returns_only_stored_ids(self, tmp_db):
        db.record_war_kills(WAR, [_row(1), _row(2)])
        assert db.get_known_war_kill_ids(WAR, [1, 2, 3]) == {1, 2}

    def test_empty_input(self, tmp_db):
        assert db.get_known_war_kill_ids(WAR, []) == set()

    def test_chunks_past_the_sqlite_variable_limit(self, tmp_db):
        db.record_war_kills(WAR, [_row(i) for i in range(1, 51)])
        found = db.get_known_war_kill_ids(WAR, list(range(1, 1201)))
        assert len(found) == 50

    def test_scoped_to_the_war(self, tmp_db):
        db.record_war_kills("other-war", [_row(1)])
        assert db.get_known_war_kill_ids(WAR, [1]) == set()


# ---------------------------------------------------------------------------
# Aggregates
# ---------------------------------------------------------------------------

class TestSummary:
    def test_empty_ledger_is_zeroed_not_an_error(self, tmp_db):
        s = db.get_war_summary(WAR, days=7)
        assert s["totals"]["a_kills"] == 0
        assert s["coverage"]["rows"] == 0
        assert s["series"] == []

    def test_counts_each_side(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, victim_side="b", killer_side="a", isk_destroyed=100.0),
            _row(2, victim_side="b", killer_side="a", isk_destroyed=200.0),
            _row(3, victim_side="a", killer_side="b", isk_destroyed=50.0),
        ])
        t = db.get_war_summary(WAR, days=7)["totals"]
        assert (t["a_kills"], t["a_isk"]) == (2, 300.0)
        assert (t["b_kills"], t["b_isk"]) == (1, 50.0)

    def test_efficiency_is_share_of_isk_destroyed(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, killer_side="a", victim_side="b", isk_destroyed=750.0),
            _row(2, killer_side="b", victim_side="a", isk_destroyed=250.0),
        ])
        t = db.get_war_summary(WAR, days=7)["totals"]
        assert t["a_efficiency"] == 75.0 and t["b_efficiency"] == 25.0

    def test_npc_kills_excluded_from_headline(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, is_npc=1)])
        assert db.get_war_summary(WAR, days=7)["totals"]["a_kills"] == 0

    def test_same_side_kill_excluded(self, tmp_db):
        # Awoxes and duels are not war kills.
        db.record_war_kills(WAR, [_row(1, victim_side="a", killer_side="a")])
        assert db.get_war_summary(WAR, days=7)["totals"]["a_kills"] == 0

    def test_third_party_kills_are_context_within_a_war_system(self, tmp_db):
        # Counted as `other_losses` where the war is being fought, but never
        # counted as war kills, and never enough on their own to list a system.
        db.record_war_kills(WAR, [
            _row(1, victim_side="b", killer_side="a"),
            _row(2, victim_side=None, killer_side=None),
        ])
        s = db.get_war_summary(WAR, days=7)
        assert s["totals"]["a_kills"] == 1
        system = s["contested_systems"][0]
        assert system["other_losses"] == 1
        assert system["war_kills"] == 1
        assert system["kills"] == 2

    def test_window_excludes_older_rows(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, ts=_ago(hours=2)), _row(2, ts=_ago(days=9))])
        assert db.get_war_summary(WAR, days=7)["totals"]["a_kills"] == 1
        assert db.get_war_summary(WAR, days=0)["totals"]["a_kills"] == 2

    def test_contest_score_ignores_one_sided_systems(self, tmp_db):
        # A 4-0 gank corridor must not outrank a genuinely contested system.
        db.record_war_kills(WAR, [
            _row(i, system_id=1, system_name="GANK", victim_side="b", killer_side="a")
            for i in range(1, 5)
        ] + [
            _row(10, system_id=2, system_name="FIGHT", victim_side="b", killer_side="a"),
            _row(11, system_id=2, system_name="FIGHT", victim_side="a", killer_side="b"),
        ])
        systems = {s["system_name"]: s for s in db.get_war_summary(WAR, days=7)["contested_systems"]}
        assert systems["GANK"]["contest_score"] == 0
        assert systems["FIGHT"]["contest_score"] > 0
        assert db.get_war_summary(WAR, days=7)["contested_systems"][0]["system_name"] == "FIGHT"

    def test_systems_with_no_war_activity_are_excluded(self, tmp_db):
        # A war's regions include busy space that has nothing to do with it.
        # A system where only third parties died is not a contested system,
        # however much ISK burned there.
        db.record_war_kills(WAR, [
            _row(1, system_id=1, system_name="WARZONE", victim_side="b", killer_side="a",
                 isk_destroyed=10.0),
            _row(2, system_id=2, system_name="RATTING", victim_side=None, killer_side=None,
                 isk_destroyed=90000.0),
        ])
        systems = db.get_war_summary(WAR, days=7)["contested_systems"]
        assert [s["system_name"] for s in systems] == ["WARZONE"]

    def test_shortlist_ranks_on_war_kills_not_isk(self, tmp_db):
        # The expensive system must not crowd out the genuinely fought-over one.
        rows = [
            _row(i, system_id=1, system_name="FIGHT",
                 victim_side="a" if i % 2 else "b", killer_side="b" if i % 2 else "a",
                 isk_destroyed=1.0)
            for i in range(1, 9)
        ]
        rows.append(_row(99, system_id=2, system_name="BLINGY", victim_side=None,
                         killer_side="a", isk_destroyed=500000.0))
        db.record_war_kills(WAR, rows)
        systems = db.get_war_summary(WAR, days=7)["contested_systems"]
        assert systems[0]["system_name"] == "FIGHT"

    def test_ship_classes_split_by_side(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, victim_side="b", ship_class="capital", isk_destroyed=900.0),
            _row(2, victim_side="a", ship_class="subcap", isk_destroyed=100.0),
        ])
        classes = db.get_war_summary(WAR, days=7)["ship_classes"]
        assert classes["b"]["capital"]["count"] == 1
        assert classes["a"]["subcap"]["count"] == 1

    def test_bucket_granularity(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, ts=_ago(days=1)), _row(2, ts=_ago(days=3))])
        assert len(db.get_war_summary(WAR, days=30, bucket="day")["series"]) == 2
        assert len(db.get_war_summary(WAR, days=30, bucket="month")["series"]) == 1


class TestRegionFilter:
    """Dropping a region from a war's REGIONS must remove it from the page.

    Filtering rather than deleting: the rows stay, so putting the region back
    restores its history without another backfill walk.
    """

    def _two_regions(self):
        db.record_war_kills(WAR, [
            _row(1, region_id=10000066, system_id=1, isk_destroyed=100.0),
            _row(2, region_id=10000034, system_id=2, isk_destroyed=900.0,
                 victim_alliance_id=500),
        ])

    def test_summary_excludes_dropped_regions(self, tmp_db):
        self._two_regions()
        s = db.get_war_summary(WAR, days=7, region_ids=[10000066])
        assert s["totals"]["a_kills"] == 1
        assert s["totals"]["a_isk"] == 100.0
        assert [x["system_id"] for x in s["contested_systems"]] == [1]

    def test_no_region_ids_means_everything(self, tmp_db):
        self._two_regions()
        assert db.get_war_summary(WAR, days=7)["totals"]["a_kills"] == 2

    def test_feed_battles_leaderboard_and_participant_all_filter(self, tmp_db):
        self._two_regions()
        kept = [10000066]
        assert len(db.get_war_kill_feed(WAR, region_ids=kept)) == 1
        assert all(b["region_id"] == 10000066
                   for b in db.get_war_battles(WAR, days=7, min_kills=1, region_ids=kept))
        bleeders = db.get_war_leaderboards(WAR, days=7, region_ids=kept)["bleeders"]
        assert [b["alliance_id"] for b in bleeders] == [200]
        p = db.get_war_participant(WAR, [200], days=7, region_ids=kept)
        assert p["losses"] == 1

    def test_dropped_rows_are_retained_for_re_adding(self, tmp_db):
        self._two_regions()
        assert _count(tmp_db, "war_kills") == 2
        # Put the region back: its history returns with no re-fetch.
        both = db.get_war_summary(WAR, days=7, region_ids=[10000066, 10000034])
        assert both["totals"]["a_kills"] == 2


class TestLeaderboards:
    def test_bleeders_grouped_by_alliance(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, victim_alliance_id=200, isk_destroyed=100.0),
            _row(2, victim_alliance_id=200, isk_destroyed=200.0),
            _row(3, victim_alliance_id=300, victim_side="a", isk_destroyed=50.0),
        ])
        bleeders = {b["alliance_id"]: b for b in db.get_war_leaderboards(WAR, days=7)["bleeders"]}
        assert bleeders[200]["losses"] == 2 and bleeders[200]["isk_lost"] == 300.0

    def test_killers_credit_every_participant(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, attacker_alliance_ids=[100, 101])])
        killers = {k["alliance_id"]: k for k in db.get_war_leaderboards(WAR, days=7)["killers"]}
        assert killers[100]["involved_kills"] == 1
        assert killers[101]["involved_kills"] == 1


class TestParticipant:
    def test_kills_and_losses(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, victim_alliance_id=200, isk_destroyed=100.0),
            _row(2, victim_alliance_id=999, attacker_alliance_ids=[200], isk_destroyed=400.0),
        ])
        p = db.get_war_participant(WAR, [200], days=7)
        assert p["losses"] == 1 and p["isk_lost"] == 100.0
        assert p["kills"] == 1 and p["isk_killed"] == 400.0
        assert p["efficiency"] == 80.0

    def test_no_alliance_ids_returns_none(self, tmp_db):
        assert db.get_war_participant(WAR, [], days=7) is None


class TestUnclassified:
    def test_surfaces_unrostered_attackers(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(i, killer_side=None, attacker_alliance_ids=[555], victim_side="b")
            for i in range(1, 5)
        ])
        rows = db.get_war_unclassified(WAR, days=7)
        assert rows[0]["alliance_id"] == 555
        # They only shoot side b, so they are probably fighting for side a.
        assert rows[0]["suggested_side"] == "a"

    def test_ignores_rare_appearances(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, killer_side=None, attacker_alliance_ids=[555])])
        assert db.get_war_unclassified(WAR, days=7) == []

    def test_already_rostered_alliances_are_never_suggested(self, tmp_db):
        # killer_side is NULL whenever no side won a majority of the attackers.
        # A rostered alliance turning up on such a kill is not unaligned, and
        # suggesting it sends the operator to re-add something already there.
        db.record_war_kills(WAR, [
            _row(i, killer_side=None, attacker_alliance_ids=[100, 555], victim_side="b")
            for i in range(1, 5)
        ])
        listed = [r["alliance_id"] for r in
                  db.get_war_unclassified(WAR, days=7, known_alliance_ids=[100, 200])]
        assert 100 not in listed
        assert 555 in listed


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------

class TestKillFeed:
    def test_newest_first_and_limited(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, ts=_ago(hours=3)), _row(2, ts=_ago(hours=1)), _row(3, ts=_ago(hours=2)),
        ])
        feed = db.get_war_kill_feed(WAR, limit=2)
        assert [k["killmail_id"] for k in feed] == [2, 3]

    def test_cursor_paginates_rows_sharing_a_timestamp(self, tmp_db):
        # A fleet fight puts many kills in the same second. Paging on time
        # alone would repeat and skip rows; the cursor carries the id too.
        ts = _ago(hours=1)
        db.record_war_kills(WAR, [_row(1, ts=ts), _row(2, ts=ts), _row(3, ts=ts)])
        seen = []
        before = None
        for _ in range(3):
            page = db.get_war_kill_feed(WAR, limit=1, before=before)
            assert len(page) == 1
            seen.append(page[0]["killmail_id"])
            before = f"{page[0]['killmail_time']}|{page[0]['killmail_id']}"
        assert sorted(seen) == [1, 2, 3]

    def test_side_filter_matches_either_role(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, victim_side="a", killer_side="b"),
            _row(2, victim_side="b", killer_side="a"),
            _row(3, victim_side=None, killer_side=None),
        ])
        assert len(db.get_war_kill_feed(WAR, side="a")) == 2
        assert len(db.get_war_kill_feed(WAR, side="b")) == 2

    def test_npc_hidden_unless_requested(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, is_npc=1)])
        assert db.get_war_kill_feed(WAR) == []
        assert len(db.get_war_kill_feed(WAR, include_npc=True)) == 1

    def test_class_and_system_filters(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, ship_class="capital", system_id=1),
            _row(2, ship_class="subcap", system_id=2),
        ])
        assert len(db.get_war_kill_feed(WAR, ship_class="capital")) == 1
        assert len(db.get_war_kill_feed(WAR, system_id=2)) == 1


# ---------------------------------------------------------------------------
# Battles
# ---------------------------------------------------------------------------

class TestBattles:
    def _fight(self, base, offsets, system_id=1, start_id=1):
        return [
            _row(start_id + i,
                 ts=(base + timedelta(minutes=off)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                 system_id=system_id)
            for i, off in enumerate(offsets)
        ]

    def test_kills_close_together_are_one_battle(self, tmp_db):
        base = datetime.now(UTC) - timedelta(hours=3)
        db.record_war_kills(WAR, self._fight(base, [0, 5, 9]))
        battles = db.get_war_battles(WAR, days=7, min_kills=3)
        assert len(battles) == 1 and battles[0]["kills"] == 3

    def test_a_long_gap_splits_the_battle(self, tmp_db):
        base = datetime.now(UTC) - timedelta(hours=6)
        db.record_war_kills(WAR,
            self._fight(base, [0, 2, 4]) + self._fight(base, [45, 47, 49], start_id=10))
        assert len(db.get_war_battles(WAR, days=7, min_kills=3)) == 2

    def test_battle_spanning_the_hour_boundary_stays_one(self, tmp_db):
        # The case clock-hour bucketing gets wrong: 19:55 and 20:05 are one
        # fight, not two.
        base = (datetime.now(UTC) - timedelta(days=1)).replace(hour=19, minute=55, second=0, microsecond=0)
        db.record_war_kills(WAR, self._fight(base, [0, 5, 10]))
        battles = db.get_war_battles(WAR, days=7, min_kills=3)
        assert len(battles) == 1 and battles[0]["kills"] == 3

    def test_simultaneous_kills_in_two_systems_are_two_battles(self, tmp_db):
        base = datetime.now(UTC) - timedelta(hours=2)
        db.record_war_kills(WAR,
            self._fight(base, [0, 1, 2], system_id=1)
            + self._fight(base, [0, 1, 2], system_id=2, start_id=10))
        assert len(db.get_war_battles(WAR, days=7, min_kills=3)) == 2

    def test_small_skirmishes_below_threshold_are_dropped(self, tmp_db):
        base = datetime.now(UTC) - timedelta(hours=2)
        db.record_war_kills(WAR, self._fight(base, [0, 1]))
        assert db.get_war_battles(WAR, days=7, min_kills=3) == []

    def test_related_url_anchors_on_the_busiest_hour(self, tmp_db):
        # A fight that starts at 19:58 belongs on the 20:00 related page.
        base = (datetime.now(UTC) - timedelta(days=1)).replace(hour=19, minute=58, second=0, microsecond=0)
        db.record_war_kills(WAR, self._fight(base, [0, 4, 8, 12], system_id=30000142))
        url = db.get_war_battles(WAR, days=7, min_kills=3)[0]["related_url"]
        stamp = (base + timedelta(hours=1)).strftime("%Y%m%d%H")
        assert url == f"https://zkillboard.com/related/30000142/{stamp}00/"

    def test_winner_is_the_side_that_lost_less(self, tmp_db):
        base = datetime.now(UTC) - timedelta(hours=2)
        rows = self._fight(base, [0, 1, 2])
        for r in rows:
            r["victim_side"] = "a"
        db.record_war_kills(WAR, rows)
        assert db.get_war_battles(WAR, days=7, min_kills=3)[0]["winner"] == "b"


# ---------------------------------------------------------------------------
# Ingest state, lease, retention
# ---------------------------------------------------------------------------

class TestIngestState:
    def test_upsert_merges_fields(self, tmp_db):
        db.upsert_war_ingest_state(WAR, 10000066, last_kill_time="2026-08-06T00:00:00Z")
        db.upsert_war_ingest_state(WAR, 10000066, saturated=1)
        state = db.get_war_ingest_state(WAR)[0]
        assert state["last_kill_time"] == "2026-08-06T00:00:00Z"
        assert state["saturated"] == 1

    def test_unknown_fields_ignored(self, tmp_db):
        db.upsert_war_ingest_state(WAR, 1, bogus="x", new_kills=4)
        assert db.get_war_ingest_state(WAR)[0]["new_kills"] == 4


class TestPollLease:
    def test_first_caller_wins_and_second_is_denied(self, tmp_db):
        assert db.acquire_war_poll_lease(WAR, "worker-1", 600) is True
        assert db.acquire_war_poll_lease(WAR, "worker-2", 600) is False

    def test_holder_can_renew(self, tmp_db):
        db.acquire_war_poll_lease(WAR, "worker-1", 600)
        assert db.acquire_war_poll_lease(WAR, "worker-1", 600) is True

    def test_expired_lease_is_takeable(self, tmp_db):
        # A crashed holder must not block ingest forever.
        db.acquire_war_poll_lease(WAR, "worker-1", -10)
        assert db.acquire_war_poll_lease(WAR, "worker-2", 600) is True

    def test_leases_are_per_war(self, tmp_db):
        db.acquire_war_poll_lease(WAR, "worker-1", 600)
        assert db.acquire_war_poll_lease("other-war", "worker-2", 600) is True


class TestPrune:
    def test_keeps_belligerent_rows_by_default(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, ts=_ago(days=400))])
        db.prune_war_kills(WAR)
        assert _count(tmp_db, "war_kills") == 1

    def test_drops_old_third_party_rows(self, tmp_db):
        db.record_war_kills(WAR, [
            _row(1, ts=_ago(days=400), victim_side=None, killer_side=None),
            _row(2, ts=_ago(hours=1), victim_side=None, killer_side=None),
        ])
        db.prune_war_kills(WAR, third_party_days=180)
        assert _count(tmp_db, "war_kills") == 1

    def test_hard_retention_when_configured(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, ts=_ago(days=400))])
        db.prune_war_kills(WAR, days=90)
        assert _count(tmp_db, "war_kills") == 0

    def test_other_wars_untouched(self, tmp_db):
        db.record_war_kills("other-war", [_row(1, ts=_ago(days=400))])
        db.prune_war_kills(WAR, days=1)
        assert _count(tmp_db, "war_kills") == 1


class TestNameRepair:
    def test_pending_ids_then_resolution(self, tmp_db):
        db.record_war_kills(WAR, [_row(1, names_resolved=0, victim_alliance_name="",
                                       victim_alliance_id=200, ship_type_id=670)])
        assert 200 in db.get_war_rows_needing_names(WAR)
        db.resolve_war_kill_names(WAR, {200: "Defenders", 670: "Capsule"})
        with _conn(tmp_db) as c:
            row = c.execute("SELECT victim_alliance_name, ship_name, names_resolved "
                            "FROM war_kills").fetchone()
        assert row["victim_alliance_name"] == "Defenders"
        assert row["ship_name"] == "Capsule"
        assert row["names_resolved"] == 1
