#!/usr/bin/env bash
# Run ONCE on a fresh Oracle Cloud Ampere VM (Oracle Linux 8/9/10 or Ubuntu 22/24).
# Installs Docker, opens firewall, clones the repo, builds, runs.
#
# Usage:
#   ssh opc@<your-oracle-public-ip>          # OL family uses 'opc' user
#   ssh ubuntu@<your-oracle-public-ip>       # Ubuntu uses 'ubuntu' user
#   sudo DOMAIN=gas-mike.duckdns.org bash bootstrap.sh

set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/mikeLackovcan/gas-analytics.git}"
APP_DIR="/opt/gas-analytics"
DOMAIN="${DOMAIN:?Set DOMAIN env var (e.g. api.pneuma.energy or gas-XXX.duckdns.org)}"

# --- Detect package manager ---
if   command -v dnf >/dev/null 2>&1; then PKG=dnf; FAMILY=rhel
elif command -v apt-get >/dev/null 2>&1; then PKG=apt; FAMILY=debian
else echo "Unsupported distro: need dnf or apt-get"; exit 1
fi
echo "==> Detected package manager: $PKG ($FAMILY family)"

# --- Add swap if RAM < 2GB (handles E2.1.Micro 1GB shape) ---
MEM_MB=$(free -m | awk '/^Mem:/ {print $2}')
SWAP_MB=$(free -m | awk '/^Swap:/ {print $2}')
if [ "$MEM_MB" -lt 1800 ] && [ "$SWAP_MB" -lt 1000 ]; then
  echo "==> Low RAM ($MEM_MB MB) and no swap — adding 4GB swap file"
  fallocate -l 4G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
  sysctl vm.swappiness=10 >/dev/null
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
fi

# --- Install Docker ---
if [ "$FAMILY" = "rhel" ]; then
  echo "==> Installing Docker (Oracle Linux)"
  dnf -y install dnf-plugins-core git
  dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
  dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
else
  echo "==> Installing Docker (Ubuntu)"
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg lsb-release ufw git
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

# --- Firewall ---
echo "==> Firewall: allow 22/80/443"
if [ "$FAMILY" = "rhel" ]; then
  # Oracle Linux uses firewalld + iptables/nftables. Both layers must allow.
  if command -v firewall-cmd >/dev/null 2>&1 && systemctl is-active --quiet firewalld; then
    firewall-cmd --permanent --add-service=http
    firewall-cmd --permanent --add-service=https
    firewall-cmd --reload
  fi
  # OL ships with iptables rules that drop everything except 22.
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT  || true
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || true
  if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save || true
  elif [ -f /etc/sysconfig/iptables ]; then
    iptables-save > /etc/sysconfig/iptables
  fi
else
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT  || true
  iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || true
  netfilter-persistent save 2>/dev/null || true
  ufw --force enable
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
fi

# --- Clone repo ---
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
  echo "    sudo nano $APP_DIR/backend/.env"
  echo "Required:"
  echo "    AGSI_API_KEY=..."
  echo "    ALSI_API_KEY=..."
  echo "    ENTSOE_API_TOKEN=..."
  echo "Optional:"
  echo "    CORS_ORIGINS=https://your-app.vercel.app"
  echo
  exit 1
fi

# --- Build and start ---
echo "==> Building + starting containers (DOMAIN=$DOMAIN)"
DOMAIN="$DOMAIN" docker compose -f docker-compose.prod.yml up -d --build

echo
echo "==> Done. Tail logs with:"
echo "    cd $APP_DIR && docker compose -f docker-compose.prod.yml logs -f"
echo
echo "==> Health check (wait ~30s for Caddy to fetch cert):"
echo "    curl -s https://$DOMAIN/healthz"
