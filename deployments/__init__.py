"""
Deployment loader. Picks the active deployment module from the DEPLOYMENT
environment variable (default: lawn_perrigen) and exposes it as `ACTIVE`.

A deployment module defines everything that varies between (alliance, region)
pairs: alliance IDs, region/constellation IDs, friendly entities, neighbor
threat list, map layout, sov upgrades, planetary interaction data. Game-wide
constants (ESI base URLs, cache TTLs, upgrade catalogue) live in
eve_constants.py instead.

Add a new deployment by running tools/bootstrap_deployment.py — it scaffolds a
module that satisfies this loader.
"""

import importlib
import os

DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT", "lawn_perrigen")

try:
    ACTIVE = importlib.import_module(f"deployments.{DEPLOYMENT_NAME}")
except ModuleNotFoundError as e:
    raise SystemExit(
        f"Deployment '{DEPLOYMENT_NAME}' not found in deployments/. "
        f"Available deployments: "
        f"{[f.removesuffix('.py') for f in os.listdir(os.path.dirname(__file__)) if f.endswith('.py') and not f.startswith('_') and f != 'example.py']}. "
        f"Bootstrap a new one with tools/bootstrap_deployment.py."
    ) from e
