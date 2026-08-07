"""
Gunicorn configuration.

preload_app matters here: app.py calls resolve_all_systems() at import, which
walks the whole region via ESI. Without preloading, every worker repeats that
walk on boot and then maintains its own private esi_client cache, roughly
doubling steady-state ESI traffic. Preloading runs it once in the master and
each worker inherits the warm cache through fork.

The catch is that threads do not survive fork, so the background poller cannot
be started at import time — it has to come up in post_fork, per worker.
"""

import os

bind = f"0.0.0.0:{os.environ.get('FLASK_PORT', '5000')}"
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
# Generous: the first request after a cold start can wait on ESI.
timeout = 120
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info").lower()


def post_fork(server, worker):
    """Start the background pollers after fork.

    Both start in every worker, but they coordinate differently: the ESI poller
    is safe to duplicate (its writes dedupe, and a redundant cycle is one small
    request), while the war poller takes a database lease so exactly one worker
    does the fetching — a duplicate war cycle would be megabytes of zKillboard
    traffic, not a rounding error.
    """
    from routes.poller import start_poller
    from routes.war_poller import start_war_poller

    start_poller()
    start_war_poller()
