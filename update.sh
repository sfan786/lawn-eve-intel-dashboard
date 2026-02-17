#!/bin/bash
# Full update — no cache rebuild.
# Use this when you've changed requirements.txt, package.json, or need a clean slate.
# Slower than quick-update.sh but guaranteed fresh.

set -e

echo "🔄 Full update (no-cache rebuild)..."
echo ""

echo "📥 Pulling latest code..."
git pull origin main

echo "🛑 Stopping containers..."
docker-compose down

echo "🏗️  Building fresh image (no cache)..."
echo "   This builds the Vite frontend + Python app from scratch."
echo "   Takes ~2-3 minutes on first run, faster after..."
docker-compose build --no-cache

echo "🚀 Starting containers..."
docker-compose up -d

echo "⏳ Waiting for startup (ESI resolution takes ~20-30s)..."
sleep 5

echo ""
echo "🧪 Testing API..."
# Poll up to 60s for the app to be ready
for i in $(seq 1 12); do
    if curl -sf http://localhost:5000/api/status | grep -q '"status"'; then
        echo "✅ Full update complete! Dashboard is live at https://lawn.sfan.xyz"
        echo "   View logs: docker-compose logs -f"
        echo ""
        docker-compose ps
        exit 0
    fi
    echo "   Waiting... ($((i * 5))s)"
    sleep 5
done

echo "⚠️  API still not responding after 60s. Check logs:"
echo "   docker-compose logs -f"
docker-compose ps
exit 1
