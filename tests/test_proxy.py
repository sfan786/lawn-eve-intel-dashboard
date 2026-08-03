"""Tests for reverse-proxy trust.

Behind nginx, remote_addr is the proxy for every visitor, which collapses the
per-IP rate limits into one shared bucket. These cover the opt-in that fixes
that, and the refusal to trust forwarding headers when it isn't set.
"""

import logging

import pytest
from flask import Flask, request

import config
from routes.proxy import apply_proxy_fix, warn_on_untrusted_proxy


@pytest.fixture
def make_app(monkeypatch):
    """Build a bare app with the proxy wiring at a given trust level."""

    def _make(hops):
        monkeypatch.setattr(config, "TRUSTED_PROXY_HOPS", hops)
        import routes.proxy as proxy_module
        monkeypatch.setattr(proxy_module, "_warned", False)

        app = Flask(__name__)
        app.config.update(TESTING=True)
        apply_proxy_fix(app)
        warn_on_untrusted_proxy(app)

        @app.route("/whoami")
        def whoami():
            return {"remote_addr": request.remote_addr, "scheme": request.scheme}

        return app

    return _make


FORWARDED = {"X-Forwarded-For": "203.0.113.7", "X-Forwarded-Proto": "https"}


class TestTrustDisabled:
    def test_forwarded_header_is_ignored(self, make_app):
        """Default is 0 hops: a client can't claim someone else's address."""
        client = make_app(0).test_client()
        body = client.get("/whoami", headers=FORWARDED).get_json()
        assert body["remote_addr"] != "203.0.113.7"

    def test_misconfiguration_is_logged_once(self, make_app, caplog):
        client = make_app(0).test_client()
        with caplog.at_level(logging.WARNING, logger="routes.proxy"):
            client.get("/whoami", headers=FORWARDED)
            client.get("/whoami", headers=FORWARDED)
        warnings = [r for r in caplog.records if "TRUSTED_PROXY_HOPS=0" in r.message]
        assert len(warnings) == 1

    def test_no_warning_without_forwarded_headers(self, make_app, caplog):
        client = make_app(0).test_client()
        with caplog.at_level(logging.WARNING, logger="routes.proxy"):
            client.get("/whoami")
        assert not [r for r in caplog.records if "TRUSTED_PROXY_HOPS" in r.message]


class TestTrustEnabled:
    def test_one_hop_yields_the_real_client(self, make_app):
        client = make_app(1).test_client()
        body = client.get("/whoami", headers=FORWARDED).get_json()
        assert body["remote_addr"] == "203.0.113.7"
        assert body["scheme"] == "https"

    def test_only_the_trusted_hop_is_taken(self, make_app):
        """With one trusted proxy, only its appended (right-most) entry counts.

        Everything left of it was supplied by the client and must not be able
        to impersonate another address.
        """
        client = make_app(1).test_client()
        body = client.get("/whoami", headers={"X-Forwarded-For": "1.2.3.4, 203.0.113.7"}).get_json()
        assert body["remote_addr"] == "203.0.113.7"

    def test_distinct_clients_are_distinguishable(self, make_app):
        """The point of the change: per-IP limits become per-user."""
        client = make_app(1).test_client()
        seen = {
            client.get("/whoami", headers={"X-Forwarded-For": ip}).get_json()["remote_addr"]
            for ip in ("203.0.113.7", "203.0.113.8")
        }
        assert seen == {"203.0.113.7", "203.0.113.8"}

    def test_no_warning_when_configured(self, make_app, caplog):
        client = make_app(1).test_client()
        with caplog.at_level(logging.WARNING, logger="routes.proxy"):
            client.get("/whoami", headers=FORWARDED)
        assert not [r for r in caplog.records if "TRUSTED_PROXY_HOPS=0" in r.message]


class TestConfigParsing:
    @pytest.mark.parametrize("raw,expected", [("1", 1), ("2", 2), (" 1 ", 1), ("0", 0)])
    def test_valid_values(self, raw, expected):
        assert config._parse_int(raw, 0) == expected

    @pytest.mark.parametrize("raw", ["", "abc", None, "1.5"])
    def test_garbage_falls_back_to_default(self, raw):
        assert config._parse_int(raw, 0) == 0

    def test_negative_is_clamped_off(self, raw=None):
        assert config._parse_int("-3", 0) == 0
