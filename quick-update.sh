#!/bin/bash
# Quick update — code changes only (uses Docker layer cache)
# Rebuilds Python + Vite layers only where files changed.
# Use update.sh instead if you've changed requirements.txt or package.json.

set -e

# Prefer Compose v2 — see the note in update.sh. v1 is EOL and breaks against
# images built by a modern engine.
if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
    echo "⚠️  Using Compose v1 (EOL). Install the v2 plugin when you can:"
    echo "     sudo apt-get install docker-compose-plugin"
    echo ""
else
    echo "❌ Neither 'docker compose' nor 'docker-compose' is available."
    exit 1
fi

echo "⚡ Quick update (cached build)..."
echo ""

echo "📥 Pulling latest code..."
git pull origin main

echo "🗄️  Ensuring intel.db and .env exist as files..."
touch intel.db
touch .env

# Same bind-mount gotcha as intel.db: if ./private does not exist when
# docker-compose starts, Docker creates it as a ROOT-OWNED directory, and
# pushing a deployment into it then fails with "Permission denied".
mkdir -p private

echo "🛑 Stopping containers..."
$DC down

echo "🔄 Rebuilding (with cache) and restarting..."
$DC up -d --build

sleep 3

echo ""
echo "📋 Recent logs:"
$DC logs --tail=20

echo ""
echo "🧪 Testing API..."
if curl -sf http://localhost:5000/api/status | grep -q '"status"'; then
    echo "✅ Quick update complete! Dashboard is live."
    echo "   View logs: $DC logs -f"
else
    echo "⚠️  API not responding yet — may still be starting (ESI resolution takes ~20s)"
    echo "   Check: $DC logs -f"
fi
