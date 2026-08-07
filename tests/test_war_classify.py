"""Tests for war_classify — pure classification, no DB and no network.

Fixtures are plain dicts in zKillboard's shape, which is what both the poller
and the backfill actually hand to the classifier.
"""

import war_classify
from war_classify import classify_kill, ship_class, side_of


class FakeSpec:
    """Minimal stand-in for wars.WarSpec, so tests need no war module."""

    def __init__(self, alliances=None, corps=None):
        self.key = "test-war"
        self.side_by_alliance = alliances or {}
        self.side_by_corp = corps or {}


SPEC = FakeSpec(alliances={100: "a", 200: "b"}, corps={999: "b"})


def _km(victim=None, attackers=None, zkb=None, **kw):
    base = {
        "killmail_id": 1,
        "killmail_time": "2026-08-06T12:34:56Z",
        "solar_system_id": 30000142,
        "victim": victim if victim is not None else {"alliance_id": 200, "character_id": 5, "ship_type_id": 670},
        "attackers": attackers if attackers is not None else [{"alliance_id": 100, "character_id": 9, "final_blow": True}],
        "zkb": {"totalValue": 1000.0, "destroyedValue": 800.0, "labels": ["cat:6"], **(zkb or {})},
    }
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# Side membership
# ---------------------------------------------------------------------------

class TestSideOf:
    def test_alliance_membership(self):
        assert side_of(100, None, SPEC) == "a"
        assert side_of(200, None, SPEC) == "b"

    def test_unknown_entity_has_no_side(self):
        assert side_of(12345, 6789, SPEC) is None

    def test_corp_wins_over_conflicting_alliance(self):
        # A corp is listed explicitly only when it must differ from its
        # alliance, so the more specific statement has to take precedence.
        spec = FakeSpec(alliances={100: "a"}, corps={999: "b"})
        assert side_of(100, 999, spec) == "b"


# ---------------------------------------------------------------------------
# Killer attribution
# ---------------------------------------------------------------------------

class TestKillerSide:
    def test_majority_wins(self):
        km = _km(attackers=[
            {"alliance_id": 100, "character_id": 1},
            {"alliance_id": 100, "character_id": 2},
            {"alliance_id": 100, "character_id": 3},
            {"alliance_id": 200, "character_id": 4, "final_blow": True},
        ])
        assert classify_kill(km, SPEC)["killer_side"] == "a"

    def test_tie_breaks_to_final_blow(self):
        km = _km(attackers=[
            {"alliance_id": 100, "character_id": 1},
            {"alliance_id": 100, "character_id": 2},
            {"alliance_id": 200, "character_id": 3},
            {"alliance_id": 200, "character_id": 4, "final_blow": True},
        ])
        assert classify_kill(km, SPEC)["killer_side"] == "b"

    def test_npc_attackers_do_not_vote(self):
        # NPCs carry no character_id; a rat landing the final blow must not
        # decide who "won" a fight.
        km = _km(attackers=[
            {"alliance_id": 100, "character_id": 1},
            {"faction_id": 500011, "final_blow": True},
        ])
        row = classify_kill(km, SPEC)
        assert row["killer_side"] == "a"

    def test_no_belligerent_attackers_leaves_killer_unset(self):
        km = _km(attackers=[{"alliance_id": 777, "character_id": 1, "final_blow": True}])
        assert classify_kill(km, SPEC)["killer_side"] is None

    def test_final_blow_alliance_recorded_even_when_unaligned(self):
        km = _km(attackers=[{"alliance_id": 777, "character_id": 1, "final_blow": True}])
        assert classify_kill(km, SPEC)["final_blow_alliance_id"] == 777


# ---------------------------------------------------------------------------
# Hull classification
# ---------------------------------------------------------------------------

class TestShipClass:
    def test_structure_from_category_label(self):
        assert ship_class(_km(zkb={"labels": ["cat:65"]})) == "structure"

    def test_sov_structure_from_category_label(self):
        assert ship_class(_km(zkb={"labels": ["cat:40"]})) == "structure"

    def test_fighter_from_category_label(self):
        # One supercap fight yields hundreds of these; they must not read as
        # ship kills in the headline counts.
        assert ship_class(_km(zkb={"labels": ["cat:87"]})) == "fighter"

    def test_deployable_from_category_label(self):
        assert ship_class(_km(zkb={"labels": ["cat:22"]})) == "deployable"

    def test_ship_falls_back_to_group_lookup(self):
        km = _km(zkb={"labels": ["cat:6"]})
        assert ship_class(km, resolve_group=lambda t: 30) == "super"
        assert ship_class(km, resolve_group=lambda t: 485) == "capital"
        assert ship_class(km, resolve_group=lambda t: 29) == "pod"
        assert ship_class(km, resolve_group=lambda t: 26) == "subcap"

    def test_group_lookup_failure_degrades_to_subcap(self):
        def boom(_):
            raise RuntimeError("ESI down")
        assert ship_class(_km(), resolve_group=boom) == "subcap"

    def test_missing_labels_and_type_is_subcap(self):
        km = _km(victim={}, zkb={"labels": []})
        assert ship_class(km) == "subcap"


# ---------------------------------------------------------------------------
# Row construction
# ---------------------------------------------------------------------------

class TestClassifyKill:
    def test_basic_row(self):
        row = classify_kill(_km(), SPEC, region_id=10000066, system_name="1-KCSA",
                            resolve_group=lambda t: 26)
        assert row["victim_side"] == "b"
        assert row["killer_side"] == "a"
        assert row["region_id"] == 10000066
        assert row["system_name"] == "1-KCSA"
        assert row["hour_bucket"] == "2026-08-06T12"
        assert row["isk_destroyed"] == 800.0
        assert row["isk_value"] == 1000.0

    def test_third_party_kill_is_still_built(self):
        # Storing these is what makes the already-seen filter a true high-water
        # mark; dropping them means re-fetching the same kills forever.
        km = _km(victim={"alliance_id": 777, "character_id": 1},
                 attackers=[{"alliance_id": 888, "character_id": 2, "final_blow": True}])
        row = classify_kill(km, SPEC, resolve_group=lambda t: 26)
        assert row is not None
        assert row["victim_side"] is None and row["killer_side"] is None

    def test_structure_kill_without_character(self):
        km = _km(victim={"alliance_id": 200, "corporation_id": 1}, zkb={"labels": ["cat:65"]})
        row = classify_kill(km, SPEC)
        assert row["victim_char_id"] is None
        assert row["ship_class"] == "structure"
        assert row["victim_side"] == "b"

    def test_victim_without_alliance_uses_corp(self):
        km = _km(victim={"corporation_id": 999, "character_id": 3})
        assert classify_kill(km, SPEC, resolve_group=lambda t: 26)["victim_side"] == "b"

    def test_npc_and_awox_flags(self):
        row = classify_kill(_km(zkb={"npc": True, "awox": True}), SPEC, resolve_group=lambda t: 26)
        assert row["is_npc"] == 1 and row["is_awox"] == 1

    def test_pilot_count_excludes_npcs(self):
        km = _km(attackers=[
            {"alliance_id": 100, "character_id": 1},
            {"faction_id": 500011},
        ])
        row = classify_kill(km, SPEC, resolve_group=lambda t: 26)
        assert row["attacker_count"] == 2
        assert row["pilot_count"] == 1

    def test_attacker_alliances_deduped_and_capped(self):
        attackers = [{"alliance_id": 100, "character_id": i} for i in range(5)]
        attackers += [{"alliance_id": 1000 + i, "character_id": 100 + i} for i in range(60)]
        row = classify_kill(_km(attackers=attackers), SPEC, resolve_group=lambda t: 26)
        ids = row["attacker_alliance_ids"]
        assert ids[0] == 100
        assert len(ids) == len(set(ids))
        assert len(ids) <= war_classify.MAX_STORED_ATTACKER_ALLIANCES

    def test_malformed_killmail_returns_none(self):
        assert classify_kill({"victim": {}}, SPEC) is None
        assert classify_kill({"killmail_id": 5}, SPEC) is None
