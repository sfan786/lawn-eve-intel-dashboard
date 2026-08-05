"""
Deployment loader. Picks the active deployment module from the DEPLOYMENT
environment variable (default: lawn_perrigen) and exposes it as `ACTIVE`.

A deployment module defines everything that varies between (alliance, region)
pairs: alliance IDs, region/constellation IDs, friendly entities, neighbor
threat list, map layout, sov upgrades, planetary interaction data. Game-wide
constants (ESI base URLs, cache TTLs, upgrade catalogue) live in
eve_constants.py instead.

Two locations are searched, private first:

  private/<name>.py      — live operational deployments. Gitignored AND
                           dockerignored: a deployment module states current
                           standings and where the alliance actually lives,
                           and this repo is public. On a server it arrives as
                           a mounted volume (see docker-compose.yml), so it is
                           never committed and never baked into an image
                           layer. Override the directory with DEPLOYMENT_DIR.

  deployments/<name>.py  — reference and historical deployments that are safe
                           to publish.

Add a new deployment by running tools/bootstrap_deployment.py — it scaffolds a
module that satisfies this loader.
"""

import importlib
import importlib.util
import os
import sys

DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT", "lawn_perrigen")

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEPLOYMENT_DIR = (os.environ.get("DEPLOYMENT_DIR") or "").strip() or os.path.join(_REPO_ROOT, "private")


def _load_from_dir(name, directory):
    """Import <directory>/<name>.py as a module, or return None if absent."""
    path = os.path.join(directory, f"{name}.py")
    if not os.path.isfile(path):
        return None
    # A flat, unique module name: this file lives outside any package, so a
    # dotted name would send Python looking for a parent that isn't there.
    mod_name = f"_private_deployment_{name}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so a re-import gets the same object rather than
    # executing the module twice.
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


def _available():
    """Names loadable from either location, for the error message."""
    found = []
    for directory in (DEPLOYMENT_DIR, os.path.dirname(__file__)):
        if not os.path.isdir(directory):
            continue
        for f in sorted(os.listdir(directory)):
            if f.endswith(".py") and not f.startswith("_") and f != "example.py":
                found.append(f.removesuffix(".py"))
    return sorted(set(found))


ACTIVE = _load_from_dir(DEPLOYMENT_NAME, DEPLOYMENT_DIR)

if ACTIVE is None:
    try:
        ACTIVE = importlib.import_module(f"deployments.{DEPLOYMENT_NAME}")
    except ModuleNotFoundError as e:
        raise SystemExit(
            f"Deployment '{DEPLOYMENT_NAME}' not found.\n"
            f"  Looked in: {DEPLOYMENT_DIR}/{DEPLOYMENT_NAME}.py\n"
            f"         and: deployments/{DEPLOYMENT_NAME}.py\n"
            f"  Available: {_available() or '(none)'}\n"
            f"\n"
            f"Private deployments are gitignored, so a fresh clone or a rebuilt\n"
            f"container will not have one until it is copied in. On a server it\n"
            f"is mounted from ./private (see docker-compose.yml); push it with\n"
            f"tools/push-deployment.sh. Bootstrap a new one with\n"
            f"tools/bootstrap_deployment.py."
        ) from e
