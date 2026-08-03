"""
Reverse-proxy awareness.

Behind nginx, `request.remote_addr` is the proxy's own address — the same value
for every visitor. Anything keyed on it (notably the per-IP rate limits in
routes/limiter.py) therefore degrades into a single shared bucket: one noisy
visitor throttles the intel endpoints for everyone.

Werkzeug's ProxyFix rewrites remote_addr from X-Forwarded-For, but only as far
as you tell it to trust. That trust is the whole security property here, so it
is explicit config (TRUSTED_PROXY_HOPS) rather than a guess: a client can put
anything it likes in X-Forwarded-For, and only the entries appended by proxies
you control are trustworthy. Hence the default of 0 — no proxy assumed, and
remote_addr stays the real peer.
"""

import logging

from flask import request
from werkzeug.middleware.proxy_fix import ProxyFix

import config

log = logging.getLogger(__name__)

_warned = False


def apply_proxy_fix(app):
    """Trust TRUSTED_PROXY_HOPS worth of forwarding headers. No-op when 0.

    x_host/x_prefix stay 0: nginx.conf passes the original Host through as
    `Host`, and honouring X-Forwarded-Host as well would let a client rewrite
    the host Flask builds URLs from.
    """
    hops = config.TRUSTED_PROXY_HOPS
    if hops <= 0:
        return app
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=hops, x_host=0, x_prefix=0)
    log.info("Trusting %d proxy hop(s) for X-Forwarded-For/Proto", hops)
    return app


def warn_on_untrusted_proxy(app):
    """Log once if forwarded requests arrive while no hops are trusted.

    That combination is almost always a misconfiguration: the app is behind a
    proxy it doesn't know about, so every client looks identical and the
    per-IP limits are effectively global.
    """

    @app.before_request
    def _check_forwarded_headers():
        global _warned
        if _warned or config.TRUSTED_PROXY_HOPS > 0:
            return
        if request.headers.get("X-Forwarded-For"):
            _warned = True
            log.warning(
                "Requests carry X-Forwarded-For but TRUSTED_PROXY_HOPS=0, so every "
                "client is seen as %s and per-IP rate limits are shared by all users. "
                "Set TRUSTED_PROXY_HOPS to the number of proxies in front of this app "
                "(1 for the nginx in nginx.conf).",
                request.remote_addr,
            )
