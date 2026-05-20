#!/bin/bash
# One-time setup for a fresh Debian/Ubuntu VPS.
# Works on Hetzner (Ubuntu 22.04), Oracle Cloud ARM, or any apt-based server.
# NOT needed for the existing server — use server-update.sh for updates.
set -e

REPO_URL="${REPO_URL:-https://github.com/YOUR_GITHUB_USER/lawn-eve-intel-dashboard.git}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/lawn-eve-intel-dashboard}"

echo "==> EVE Intel Dashboard — Server Setup"
echo "    Repo:    $REPO_URL"
echo "    Install: $INSTALL_DIR"
echo ""

# ── Docker ──────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    echo "==> Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    echo "    Docker installed. Re-login may be required for group to take effect."
    echo "    If 'docker compose' fails below, log out and back in, then re-run."
fi

# ── nginx ────────────────────────────────────────────────────────────────────
if ! command -v nginx &>/dev/null; then
    echo "==> Installing nginx..."
    sudo apt-get update -qq
    sudo apt-get install -y nginx
fi

# ── Clone or update repo ─────────────────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> Repo already cloned — pulling latest..."
    git -C "$INSTALL_DIR" pull origin main
else
    echo "==> Cloning repo..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# ── nginx config ─────────────────────────────────────────────────────────────
echo "==> Configuring nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/lawn-intel
sudo ln -sf /etc/nginx/sites-available/lawn-intel /etc/nginx/sites-enabled/lawn-intel
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable --now nginx
sudo systemctl reload nginx

# ── .env ─────────────────────────────────────────────────────────────────────
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "==> Created .env from template."
    echo "    IMPORTANT: Edit .env before continuing:"
    echo "      nano $INSTALL_DIR/.env"
    echo ""
    echo "    Set TIMER_PASSWORD to something only your alliance knows."
    echo "    Press Enter when done..."
    read -r
fi

# ── SQLite db file ────────────────────────────────────────────────────────────
# Must exist as a file before docker compose up, or Docker creates it as a dir.
touch intel.db

# ── Start app ────────────────────────────────────────────────────────────────
echo "==> Building and starting..."
docker compose build
docker compose up -d

echo "==> Waiting for health check..."
sleep 10

if curl -sf http://localhost:5000/api/status > /dev/null; then
    echo ""
    echo "==> Setup complete!"
    echo "    Dashboard: http://$(curl -sf ifconfig.me || echo '<server-ip>')"
    echo ""
    echo "Useful commands:"
    echo "  docker compose logs -f         # tail logs"
    echo "  docker compose restart         # restart app"
    echo "  bash scripts/server-update.sh  # pull + rebuild + restart"
else
    echo "==> ERROR — app did not come up. Check logs:"
    echo "    docker compose logs --tail=50"
    exit 1
fi
