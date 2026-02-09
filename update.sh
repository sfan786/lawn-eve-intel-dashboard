#!/bin/bash
# Quick update script for LAWN Intel Dashboard
# Run this on your Hetzner server after pushing code changes

set -e

echo "🔄 Updating LAWN Intel Dashboard..."
echo ""

# Pull latest code
echo "📥 Pulling latest code from GitHub..."
git pull origin main

# Stop containers cleanly
echo "🛑 Stopping containers..."
docker-compose down

# Rebuild with fresh images
echo "🏗️  Building new image..."
docker-compose build --no-cache

# Start containers
echo "🚀 Starting containers..."
docker-compose up -d

# Wait a moment for startup
sleep 3

# Check status
echo ""
echo "✅ Update complete! Checking status..."
docker-compose ps

# Test API
echo ""
echo "🧪 Testing API..."
if curl -s http://localhost:5000/api/status | grep -q "online"; then
    echo "✅ API is responding!"
    echo ""
    echo "Dashboard updated and running at https://lawn.sfan.xyz"
else
    echo "⚠️  API not responding. Check logs:"
    echo "  docker-compose logs -f"
    exit 1
fi
