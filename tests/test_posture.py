"""Tests for deployment posture — the sov-holding vs rootless split.

A rootless deployment holds no sov, so the whole ADM/grinding/upgrade stack has
nothing true to say. These tests pin the three things that actually have to
hold: the posture reaches the frontend, the startup region walk is skipped, and
the poller does not file somebody else's ADM under our deployment_id.

Modules import config values by value at import time, so each test patches the
importing module's global rather than `config` alone.
"""

import pytest
from flask import Flask

import config
import esi_client
from routes import poller
from routes.config_routes import config_bp
from routes.regions import resolve_region_id
from routes.zkill_routes import zkill_bp

WATCHED = [
    {"id": 10000066, "name": "Perrigen Falls"},
    {"id": 10000030, "name": "Heimatar"},
]
UNWATCHED_REGION_ID = 10000002  # The Forge — deliberately not on the list


# ---------------------------------------------------------------------------
# The contract defaults
# ---------------------------------------------------------------------------

class TestPostureDefaults:
    def test_active_deployment_declares_a_posture(self):
        assert config.POSTURE in ("sovereign", "rootless", "guest")

    def test_holds_sov_tracks_posture(self):
        assert config.HOLDS_SOV == (config.POSTURE == "sovereign")

    def test_has_ao_tracks_posture(self):
        assert config.HAS_AO == (config.POSTURE in ("sovereign", "guest"))

    def test_holds_sov_implies_has_ao(self):
        """Owning space you don't operate in is not a state that exists."""
        if config.HOLDS_SOV:
            assert config.HAS_AO

    def test_deployment_without_posture_defaults_to_sovereign(self):
        """A pre-posture deployment module must keep working unchanged."""
        import deployments.example as example
        assert getattr(example, "POSTURE", "sovereign") == "sovereign"

    def test_watched_regions_always_populated(self):
        """Falls back to the deployment's own region, so REGION_ID is never orphaned."""
        assert config.WATCHED_REGIONS
        assert config.REGION_ID in config.WATCHED_REGION_IDS


class TestLocalDeploymentModules:
    """Live deployment modules live in private/ and are gitignored, because this
    repo is public and standings/staging are not things to publish while they
    are still true. So these tests validate whatever private modules happen to
    exist, structurally, without naming any of them or asserting on real entity
    IDs — and pass cleanly on a fresh clone or CI runner that has none.
    """

    @staticmethod
    def _local_modules():
        import pathlib

        from deployments import DEPLOYMENT_DIR, _load_from_dir

        out = []
        directory = pathlib.Path(DEPLOYMENT_DIR)
        if not directory.is_dir():
            return out
        for path in sorted(directory.glob("*.py")):
            if path.stem.startswith("_"):
                continue
            out.append(_load_from_dir(path.stem, str(directory)))
        return out

    def test_local_modules_declare_a_known_posture(self):
        for mod in self._local_modules():
            assert getattr(mod, "POSTURE", "sovereign") in ("sovereign", "rootless", "guest")

    def test_rootless_locals_hold_no_geography(self):
        for mod in self._local_modules():
            if getattr(mod, "POSTURE", "sovereign") != "rootless":
                continue
            assert mod.PRIMARY_CONSTELLATION_IDS == []
            assert mod.PRIMARY_SYSTEMS == []
            assert mod.MAP_LAYOUT == {}
            # The default region must be one it actually watches, or the kill
            # feed 400s against its own default.
            assert mod.REGION in mod.WATCHED_REGIONS

    def test_guest_locals_have_a_host_and_geography(self):
        for mod in self._local_modules():
            if getattr(mod, "POSTURE", "sovereign") != "guest":
                continue
            assert mod.HOST_ALLIANCE_IDS, "a guest posture needs a host"
            # A guest is not rootless: it has a home to render.
            assert mod.PRIMARY_CONSTELLATION_IDS
            assert mod.MAP_LAYOUT
            # Hosts are not implicitly friendly — standings must say so
            # separately, or local scan flags our own landlord as hostile.
            for host_id in mod.HOST_ALLIANCE_IDS:
                assert host_id in mod.FRIENDLY_ALLIANCE_IDS

    def test_local_deployment_ids_are_distinct(self):
        """A shared id would merge two deployments' history in intel.db."""
        ids = [m.DEPLOYMENT_ID for m in self._local_modules()]
        assert len(ids) == len(set(ids))
        assert "lawn-perrigen" not in ids


class TestGuestPostureDerivation:
    """Guest is holds_sov=False + has_ao=True. Both halves matter."""

    @pytest.fixture
    def guest(self, monkeypatch):
        monkeypatch.setattr(config, "POSTURE", "guest")
        monkeypatch.setattr(config, "HOLDS_SOV", False)
        monkeypatch.setattr(config, "HAS_AO", True)
        return config

    def test_guest_does_not_hold_sov(self, guest):
        assert guest.HOLDS_SOV is False

    def test_guest_still_has_an_ao(self, guest):
        assert guest.HAS_AO is True


# ---------------------------------------------------------------------------
# Region allowlist
# ---------------------------------------------------------------------------

class TestResolveRegionId:
    """The feed accepts ANY known-space region, not just the pinned shortlist —
    an alliance between homes wants to look wherever the fight is. Validation
    still rejects ids that aren't real regions, because each accepted request
    fans out to zKill and then to ESI per killmail."""

    ALL_REGIONS = [
        {"id": 10000066, "name": "Perrigen Falls"},
        {"id": 10000030, "name": "Heimatar"},
        {"id": 10000002, "name": "The Forge"},   # real, but NOT pinned
    ]

    @pytest.fixture(autouse=True)
    def _regions(self, monkeypatch):
        import routes.regions as regions
        monkeypatch.setattr(regions, "WATCHED_REGIONS", WATCHED)
        monkeypatch.setattr(regions, "REGION_ID", WATCHED[0]["id"])
        monkeypatch.setattr(esi_client, "get_all_regions", lambda: self.ALL_REGIONS)

    def test_absent_falls_back_to_deployment_region(self):
        assert resolve_region_id({}) == (WATCHED[0]["id"], None)

    def test_empty_string_falls_back(self):
        assert resolve_region_id({"region_id": ""}) == (WATCHED[0]["id"], None)

    def test_pinned_region_is_accepted(self):
        region_id, err = resolve_region_id({"region_id": str(WATCHED[1]["id"])})
        assert err is None
        assert region_id == WATCHED[1]["id"]

    def test_unpinned_but_real_region_is_accepted(self):
        """The whole point of opening this up: highsec, lowsec, anywhere."""
        region_id, err = resolve_region_id({"region_id": "10000002"})
        assert err is None
        assert region_id == 10000002

    def test_nonexistent_region_is_rejected(self):
        region_id, err = resolve_region_id({"region_id": "99999999"})
        assert region_id is None
        assert "known-space region" in err["error"]

    def test_non_integer_is_rejected(self):
        region_id, err = resolve_region_id({"region_id": "'; DROP TABLE"})
        assert region_id is None
        assert "integer" in err["error"]

    def test_falls_back_to_pinned_when_esi_is_down(self, monkeypatch):
        """If we can't confirm an id is real, don't forward it upstream while
        ESI is already struggling — accept only the known-good shortlist."""
        def _boom():
            raise RuntimeError("ESI down")
        monkeypatch.setattr(esi_client, "get_all_regions", _boom)

        assert resolve_region_id({"region_id": str(WATCHED[1]["id"])}) == (WATCHED[1]["id"], None)
        region_id, err = resolve_region_id({"region_id": "10000002"})
        assert region_id is None and err


class TestKillFeedRegionGate:
    """The feed fans out to zKill then ESI per killmail, so a bogus region_id
    must be rejected before any of that happens."""

    @pytest.fixture
    def client(self, monkeypatch):
        import routes.regions as regions
        from routes.limiter import limiter
        monkeypatch.setattr(regions, "WATCHED_REGIONS", WATCHED)
        monkeypatch.setattr(regions, "REGION_ID", WATCHED[0]["id"])
        monkeypatch.setattr(esi_client, "get_all_regions", lambda: list(WATCHED))
        flask_app = Flask(__name__)
        flask_app.config.update(TESTING=True, RATELIMIT_ENABLED=False)
        limiter.init_app(flask_app)
        flask_app.register_blueprint(zkill_bp)
        return flask_app.test_client()

    def test_nonexistent_region_400s_without_calling_out(self, client, monkeypatch):
        def _boom(*a, **kw):
            raise AssertionError("zKillboard must not be called for a rejected region")
        monkeypatch.setattr(esi_client, "get_zkill_region", _boom)

        resp = client.get(f"/api/zkill/feed?region_id={UNWATCHED_REGION_ID}")
        assert resp.status_code == 400
        assert "known-space region" in resp.get_json()["error"]

    def test_garbage_region_400s(self, client):
        assert client.get("/api/zkill/feed?region_id=banana").status_code == 400

    def test_regions_endpoint_lists_catalogue_and_pinned(self, client):
        body = client.get("/api/regions").get_json()
        assert body["regions"] == list(WATCHED)
        assert body["pinned"] == [r["id"] for r in WATCHED]

    def test_regions_endpoint_degrades_when_esi_is_down(self, client, monkeypatch):
        """A short picker beats a broken one."""
        def _boom():
            raise RuntimeError("ESI down")
        monkeypatch.setattr(esi_client, "get_all_regions", _boom)

        resp = client.get("/api/regions")
        assert resp.status_code == 200
        assert resp.get_json()["regions"] == list(WATCHED)


# ---------------------------------------------------------------------------
# /api/config publishes the posture the frontend gates on
# ---------------------------------------------------------------------------

class TestConfigEndpointPosture:
    @pytest.fixture
    def client(self, monkeypatch):
        import routes.config_routes as config_routes
        monkeypatch.setattr(config_routes, "POSTURE", "rootless")
        monkeypatch.setattr(config_routes, "POSTURE_LABEL", "NO FIXED AO")
        monkeypatch.setattr(config_routes, "HOLDS_SOV", False)
        monkeypatch.setattr(config_routes, "WATCHED_REGIONS", WATCHED)
        flask_app = Flask(__name__)
        flask_app.config.update(TESTING=True)
        flask_app.register_blueprint(config_bp)
        return flask_app.test_client()

    def test_config_reports_rootless(self, client):
        body = client.get("/api/config").get_json()
        assert body["holds_sov"] is False
        assert body["posture"] == "rootless"
        assert body["posture_label"] == "NO FIXED AO"
        assert body["watched_regions"] == WATCHED

    def test_status_reports_rootless(self, client):
        body = client.get("/api/status").get_json()
        assert body["holds_sov"] is False
        assert body["posture"] == "rootless"


# ---------------------------------------------------------------------------
# Startup does no region walk when there is no home region
# ---------------------------------------------------------------------------

class TestRootlessStartup:
    def test_region_walk_is_skipped(self, monkeypatch):
        import routes.system_state as system_state

        monkeypatch.setattr(system_state, "HAS_AO", False)
        monkeypatch.setattr(system_state, "PRIMARY_CONSTELLATION_IDS", [])

        def _boom(*a, **kw):
            raise AssertionError("rootless startup must not walk a region")
        monkeypatch.setattr(esi_client, "get_region_info", _boom)
        monkeypatch.setattr(esi_client, "get_constellation_info", _boom)
        monkeypatch.setattr(esi_client, "post_universe_ids", _boom)

        s = system_state.SystemState()
        system_state.resolve_all_systems(s)

        assert s.all_monitored_ids == set()
        assert s.primary_system_ids == set()
        assert s.constellation_data == {}

    def test_sovereign_deployment_still_walks(self, monkeypatch):
        """The skip must be posture-driven, not an unconditional short-circuit."""
        import routes.system_state as system_state

        monkeypatch.setattr(system_state, "HAS_AO", True)
        monkeypatch.setattr(system_state, "PRIMARY_CONSTELLATION_IDS", [20000748])
        monkeypatch.setattr(system_state, "NEIGHBOR_SYSTEM_NAMES", [])

        called = []
        monkeypatch.setattr(esi_client, "get_region_info", lambda *a, **kw: called.append("region") or {"constellations": []})

        system_state.resolve_all_systems(system_state.SystemState())
        assert called == ["region"]

    def test_guest_walks_the_region_despite_holding_no_sov(self, monkeypatch):
        """The skip is keyed on HAS_AO, not HOLDS_SOV. A guest owns nothing but
        still has a home to render, defend and watch the neighbours of — if this
        regresses to HOLDS_SOV a guest deployment's map silently comes up
        empty."""
        import routes.system_state as system_state

        monkeypatch.setattr(system_state, "HAS_AO", True)
        monkeypatch.setattr(system_state, "PRIMARY_CONSTELLATION_IDS", [20000001])
        monkeypatch.setattr(system_state, "NEIGHBOR_SYSTEM_NAMES", [])

        called = []
        monkeypatch.setattr(esi_client, "get_region_info", lambda *a, **kw: called.append("region") or {"constellations": []})

        system_state.resolve_all_systems(system_state.SystemState())
        assert called == ["region"]


# ---------------------------------------------------------------------------
# The poller must not file someone else's ADM under our deployment_id
# ---------------------------------------------------------------------------

class TestPollerPostureGuard:
    @pytest.fixture
    def calls(self, monkeypatch):
        seen = []
        monkeypatch.setattr(poller, "snapshot_sovereignty", lambda: seen.append("sov") or 0)
        monkeypatch.setattr(poller, "snapshot_activity", lambda: seen.append("act") or 0)
        return seen

    def test_rootless_writes_no_snapshots(self, calls, monkeypatch):
        monkeypatch.setattr(poller, "HOLDS_SOV", False)
        monkeypatch.setattr(poller, "HAS_AO", False)
        poller.poll_once()
        assert calls == []

    def test_sovereign_snapshots_both(self, calls, monkeypatch):
        monkeypatch.setattr(poller, "HOLDS_SOV", True)
        monkeypatch.setattr(poller, "HAS_AO", True)
        poller.poll_once()
        assert calls == ["sov", "act"]

    def test_guest_snapshots_activity_but_not_adm(self, calls, monkeypatch):
        """ADM would be the host's. Activity is ownership-neutral and feeds the
        heatmap plus the 7-day regional spike baselines, both of which render
        under a guest posture."""
        monkeypatch.setattr(poller, "HOLDS_SOV", False)
        monkeypatch.setattr(poller, "HAS_AO", True)
        poller.poll_once()
        assert calls == ["act"]


# ---------------------------------------------------------------------------
# Host sov classification
# ---------------------------------------------------------------------------

class TestHostSovClassification:
    """Fictional IDs on purpose — this repo is public, and which alliance is
    actually anybody's host is not a fact to publish in a test fixture."""

    HOST = 90000001       # the alliance whose sov we live under
    BLUE = 90000002       # friendly, holds sov nearby, but is not our host
    HOSTILE = 90000003
    OURS = 90000004

    @pytest.fixture
    def client(self, monkeypatch):
        import routes.sov_routes as sov_routes
        from routes.sov_routes import sov_bp
        from routes.system_state import state as live_state

        monkeypatch.setattr(sov_routes, "HOST_ALLIANCE_IDS", {self.HOST})
        monkeypatch.setattr(sov_routes, "FRIENDLY_ALLIANCE_IDS", [self.HOST, self.BLUE])
        monkeypatch.setattr(sov_routes, "FRIENDLY_ALLIANCES", [])
        monkeypatch.setattr(sov_routes, "PRIMARY_ALLIANCE_ID", self.OURS)
        monkeypatch.setattr(live_state, "all_monitored_ids", {1, 2, 3, 4})

        monkeypatch.setattr(esi_client, "get_sovereignty_map", lambda: [
            {"system_id": 1, "alliance_id": self.HOST},
            {"system_id": 2, "alliance_id": self.BLUE},
            {"system_id": 3, "alliance_id": self.HOSTILE},
            {"system_id": 4, "alliance_id": self.OURS},
        ])
        monkeypatch.setattr(esi_client, "get_sovereignty_structures", lambda: [])
        monkeypatch.setattr(esi_client, "get_alliance_info", lambda aid: {"name": f"A{aid}"})

        flask_app = Flask(__name__)
        flask_app.config.update(TESTING=True)
        flask_app.register_blueprint(sov_bp)
        return flask_app.test_client()

    def test_host_is_flagged_host(self, client):
        body = client.get("/api/sovereignty").get_json()
        assert body["1"]["is_host"] is True

    def test_host_is_not_confused_with_ours(self, client):
        """The map colours on is_host vs is_ours; a host must not read as ours."""
        body = client.get("/api/sovereignty").get_json()
        assert body["1"]["is_ours"] is False
        assert body["1"]["is_friendly"] is True

    def test_friendly_non_host_is_not_host(self, client):
        """A blue holding sov in the same region is not our landlord — treating
        it as host would mis-colour the map and mis-read its campaigns."""
        body = client.get("/api/sovereignty").get_json()
        assert body["2"]["is_friendly"] is True
        assert body["2"]["is_host"] is False

    def test_hostile_is_neither(self, client):
        body = client.get("/api/sovereignty").get_json()
        assert body["3"]["is_friendly"] is False
        assert body["3"]["is_host"] is False

    def test_our_own_sov_is_ours_not_host(self, client):
        body = client.get("/api/sovereignty").get_json()
        assert body["4"]["is_ours"] is True
        assert body["4"]["is_host"] is False

    def test_no_hosts_configured_means_no_host_flags(self, client, monkeypatch):
        """Sovereign deployments must be byte-for-byte unaffected."""
        import routes.sov_routes as sov_routes
        monkeypatch.setattr(sov_routes, "HOST_ALLIANCE_IDS", set())
        body = client.get("/api/sovereignty").get_json()
        assert all(entry["is_host"] is False for entry in body.values())
