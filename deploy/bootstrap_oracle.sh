#!/usr/bin/env bash
# Run ONCE on a fresh Oracle Cloud Ampere VM (Ubuntu 22.04 / 24.04).
# Installs Docker, opens firewall, clones the repo, builds, runs.
#
# Usage:
#   ssh ubuntu@<your-oracle-public-ip>
#   curl -fsSL https://raw.githubusercontent.com/mikeLackovcan/gas-analytics/main/deploy/bootstrap_oracle.sh | sudo bash
# OR copy this file via scp and run: sudo bash bootstrap_oracle.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mikeLackovcan/gas-analytics.git}"
APP_DIR="/opt/gas-analytics"
DOMAIN="${DOMAIN:?Set DOMAIN env var (e.g. api.pneuma.energy or gas-XXX.duckdns.org)}"

echo "==> Updating apt"
apt-get update -y
apt-get install -y ca-certificates curl gnupg lsb-release ufw git

echo "==> Installing Docker"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "==> Firewall: allow 22/80/443"
# Oracle by default blocks everything except 22 in iptables — open 80/443.
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT  || true
iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || true
netfilter-persistent save 2>/dev/null || true
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp

echo "==> Cloning repo into $APP_DIR"
if [ ! -d "$APP_DIR" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  cd "$APP_DIR" && git pull
fi
cd "$APP_DIR"

if [ ! -f backend/.env ]; then
  echo
  echo "*** backend/.env is MISSING. Create it now: ***"
  echo "    nano backend/.env"
  echo "Required:"
  echo "    AGSI_API_KEY=..."
  echo "    ALSI_API_KEY=..."
  echo "    ENTSOE_API_TOKEN=..."
  echo
  exit 1
fi

echo "==> Building + starting containers (DOMAIN=$DOMAIN)"
DOMAIN="$DOMAIN" docker compose -f docker-compose.prod.yml up -d --build

echo
echo "==> Done. Tail logs with:"
echo "    cd $APP_DIR && docker compose -f docker-compose.prod.yml logs -f"
echo
echo "==> Health check:"
echo "    curl -s https://$DOMAIN/healthz"
