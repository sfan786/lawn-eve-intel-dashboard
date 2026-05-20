#!/bin/bash
# On-server update script — git pull → rebuild → restart.
# Called by GitHub Actions on every push to main, or run manually.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"

cd "$APP_DIR"

echo "==> Pulling latest code..."
git pull origin main

echo "==> Rebuilding Docker image..."
docker compose build

echo "==> Restarting container..."
docker compose up -d

echo "==> Waiting for health check..."
sleep 8

if curl -sf http://localhost:5000/api/status > /dev/null; then
    echo "==> OK — app is healthy"
else
    echo "==> ERROR — app did not come up. Check logs:"
    echo "    docker compose logs --tail=50"
    exit 1
fi
