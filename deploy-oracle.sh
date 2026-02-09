#!/bin/bash
# Deployment script for Oracle Cloud Free Tier (Ubuntu ARM)

set -e

echo "🚀 LAWN Intel Dashboard - Oracle Cloud Deployment"
echo "=================================================="

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  Don't run as root. Run as ubuntu user."
    exit 1
fi

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "🐳 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo "✅ Docker installed. You may need to log out and back in."
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo apt install -y docker-compose
fi

# Install nginx if not present
if ! command -v nginx &> /dev/null; then
    echo "🌐 Installing nginx..."
    sudo apt install -y nginx

    # Copy nginx config
    sudo cp nginx.conf /etc/nginx/sites-available/lawn-intel
    sudo ln -sf /etc/nginx/sites-available/lawn-intel /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default

    # Test and reload nginx
    sudo nginx -t
    sudo systemctl enable nginx
    sudo systemctl restart nginx
fi

# Build and start Docker container
echo "🏗️  Building Docker image..."
docker-compose build

echo "🚀 Starting application..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for app to be healthy..."
sleep 10

# Check status
if curl -f http://localhost:5000/api/status &> /dev/null; then
    echo "✅ Application is running!"
    echo ""
    echo "Dashboard available at:"
    echo "  http://$(curl -s ifconfig.me)"
    echo ""
    echo "Useful commands:"
    echo "  docker-compose logs -f       # View logs"
    echo "  docker-compose restart       # Restart app"
    echo "  docker-compose down          # Stop app"
    echo "  docker-compose up -d --build # Rebuild and restart"
else
    echo "❌ Application failed to start. Check logs:"
    echo "  docker-compose logs"
fi
