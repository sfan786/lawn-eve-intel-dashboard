#!/bin/bash
# Quick update — code changes only (uses Docker layer cache)
# Rebuilds Python + Vite layers only where files changed.
# Use update.sh instead if you've changed requirements.txt or package.json.

set -e

echo "⚡ Quick update (cached build)..."
echo ""

echo "📥 Pulling latest code..."
git pull origin main

echo "🗄️  Ensuring intel.db and .env exist as files..."
touch intel.db
touch .env

echo "🛑 Stopping containers..."
docker-compose down

echo "🔄 Rebuilding (with cache) and restarting..."
docker-compose up -d --build

sleep 3

echo ""
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo ""
echo "🧪 Testing API..."
if curl -sf http://localhost:5000/api/status | grep -q '"status"'; then
    echo "✅ Quick update complete! Dashboard is live."
    echo "   View logs: docker-compose logs -f"
else
    echo "⚠️  API not responding yet — may still be starting (ESI resolution takes ~20s)"
    echo "   Check: docker-compose logs -f"
fi
