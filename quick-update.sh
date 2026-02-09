#!/bin/bash
# Quick update for code changes only (no dependency changes)
# Faster than full rebuild

set -e

echo "⚡ Quick update (code changes only)..."
echo ""

# Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# Rebuild and restart (uses cache)
echo "🔄 Restarting with new code..."
docker-compose up -d --build

# Wait for startup
sleep 2

# Show logs
echo ""
echo "📋 Recent logs:"
docker-compose logs --tail=20

echo ""
echo "✅ Quick update complete!"
echo "View live logs: docker-compose logs -f"
