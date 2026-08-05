#!/bin/bash
# Push a private deployment module to the production server.
#
# Deployment modules under private/ are gitignored and dockerignored on
# purpose: they state current standings and where the alliance actually lives,
# and the repo is public. That means `git pull` on the server will never bring
# them — this script is how they get there.
#
# It copies into the server's ./private/ directory, which docker-compose mounts
# read-only at /app/private. Once a module is there it survives every later
# `git pull`, `docker-compose build`, and update.sh run, so this is normally a
# one-time step per deployment (re-run it whenever you edit the module).
#
# Usage:
#   tools/push-deployment.sh <name> [user@host] [remote-path]
#   tools/push-deployment.sh my_deployment
#   tools/push-deployment.sh my_deployment deploy@example.com /srv/lawn-intel
#
# Defaults come from env vars so you can set them once in your shell:
#   DEPLOY_HOST   e.g. deploy@lawn.example.com   (required, no default)
#   DEPLOY_PATH   e.g. ~/lawn-eve-intel-dashboard (default below)
#
# After pushing, activate it by setting DEPLOYMENT=<name> in the server's .env
# and restarting: the script reminds you and offers to do the restart.

set -euo pipefail

NAME="${1:-}"
HOST="${2:-${DEPLOY_HOST:-}}"
REMOTE_PATH="${3:-${DEPLOY_PATH:-~/lawn-eve-intel-dashboard}}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCAL_DIR="${DEPLOYMENT_DIR:-$REPO_ROOT/private}"

if [ -z "$NAME" ]; then
    echo "Usage: tools/push-deployment.sh <name> [user@host] [remote-path]"
    echo ""
    if [ -d "$LOCAL_DIR" ]; then
        echo "Available private deployments in $LOCAL_DIR:"
        found=0
        for f in "$LOCAL_DIR"/*.py; do
            [ -e "$f" ] || continue
            echo "   $(basename "${f%.py}")"
            found=1
        done
        [ "$found" = 1 ] || echo "   (none — bootstrap one with tools/bootstrap_deployment.py)"
    else
        echo "No $LOCAL_DIR directory yet."
    fi
    exit 1
fi

SRC="$LOCAL_DIR/$NAME.py"
if [ ! -f "$SRC" ]; then
    echo "❌ No such deployment: $SRC"
    echo "   Private deployments live in $LOCAL_DIR/<name>.py"
    exit 1
fi

if [ -z "$HOST" ]; then
    echo "❌ No target host. Pass one, or set DEPLOY_HOST:"
    echo "     tools/push-deployment.sh $NAME user@host"
    echo "     export DEPLOY_HOST=user@host"
    exit 1
fi

# Sanity-check the module before shipping it: a syntax error or a missing
# required key is much cheaper to find here than as a crash-looping container.
echo "🔎 Validating $NAME..."
DEPLOYMENT="$NAME" DEPLOYMENT_DIR="$LOCAL_DIR" \
    "${PYTHON:-python3}" -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
import config
print('   posture=%s  holds_sov=%s  has_ao=%s' % (config.POSTURE, config.HOLDS_SOV, config.HAS_AO))
print('   alliance=%s  region=%s' % (config.ALLIANCE['name'], config.REGION['name']))
print('   deployment_id=%s' % config.DEPLOYMENT_ID)
" || { echo "❌ $NAME failed to load — fix it before pushing."; exit 1; }

echo ""
echo "📤 Pushing $NAME.py → $HOST:$REMOTE_PATH/private/"

# Make sure the destination is writable BEFORE scp, and explain it if not.
# `mkdir -p` exits 0 on an existing directory, so it happily succeeds on one
# Docker created — Docker makes a missing bind-mount source as root, exactly
# like the intel.db gotcha. Without this check scp fails with a bare
# "Permission denied" that gives no hint the cause is ownership.
#
# REMOTE_PATH is deliberately NOT single-quoted inside the remote command: it
# usually starts with ~, and a quoted tilde is a literal directory name rather
# than $HOME — which silently creates ~/'~'/... and then tests a path that is
# not the one scp writes to. Unquoted lets the remote shell expand it, at the
# cost of not supporting remote paths containing spaces.
remote_check=$(ssh "$HOST" "mkdir -p $REMOTE_PATH/private 2>/dev/null; \
    if [ ! -d $REMOTE_PATH/private ]; then echo NODIR; \
    elif [ ! -w $REMOTE_PATH/private ]; then stat -c 'NOTWRITABLE %U:%G' $REMOTE_PATH/private; \
    else echo OK; fi")

case "$remote_check" in
    OK) ;;
    NODIR)
        echo "❌ Could not create $REMOTE_PATH/private on $HOST."
        echo "   Does $REMOTE_PATH exist and is it yours?"
        exit 1
        ;;
    NOTWRITABLE*)
        owner=$(echo "$remote_check" | awk '{print $2}')
        echo "❌ $REMOTE_PATH/private exists on $HOST but is not writable by you."
        echo "   It is owned by: $owner"
        echo ""
        echo "   Docker created it. A bind-mount source that doesn't exist yet gets"
        echo "   made by the daemon as root — the same trap as intel.db. Fix it once:"
        echo ""
        echo "     ssh $HOST 'sudo chown -R \$(id -un):\$(id -gn) $REMOTE_PATH/private'"
        echo ""
        echo "   update.sh/quick-update.sh now mkdir it first, so this won't recur."
        exit 1
        ;;
    *)
        echo "❌ Unexpected response checking $REMOTE_PATH/private: $remote_check"
        exit 1
        ;;
esac

scp "$SRC" "$HOST:$REMOTE_PATH/private/$NAME.py"

echo ""
echo "✅ Pushed. It is mounted read-only at /app/private and survives"
echo "   git pull / rebuilds from here on."
echo ""
echo "To activate, on the server:"
echo "   cd $REMOTE_PATH"
echo "   echo 'DEPLOYMENT=$NAME' >> .env     # or edit an existing DEPLOYMENT= line"
echo "   ./quick-update.sh"
echo ""
read -r -p "Set DEPLOYMENT=$NAME in the server's .env and restart now? [y/N] " reply
case "$reply" in
    [yY]*)
        echo "🚀 Activating $NAME on $HOST..."
        # Replace an existing DEPLOYMENT= line if present, otherwise append.
        # Compose v2 if available; v1 is EOL and its --force-recreate dies with
        # KeyError: 'ContainerConfig' against images built by a modern engine,
        # leaving the container stopped. On v1 use down+up, which avoids that
        # code path — the same thing update.sh does.
        ssh "$HOST" "cd $REMOTE_PATH && touch .env && \
            if grep -q '^DEPLOYMENT=' .env; then \
                sed -i 's/^DEPLOYMENT=.*/DEPLOYMENT=$NAME/' .env; \
            else \
                echo 'DEPLOYMENT=$NAME' >> .env; \
            fi && \
            if docker compose version >/dev/null 2>&1; then \
                docker compose up -d --force-recreate; \
            else \
                docker-compose down && docker-compose up -d; \
            fi"
        echo "✅ Restarted. Verify with:"
        echo "   ssh $HOST 'cd $REMOTE_PATH && curl -s localhost:5000/api/status'"
        ;;
    *)
        echo "Skipped. Run the commands above when ready."
        ;;
esac
