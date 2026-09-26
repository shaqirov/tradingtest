#!/usr/bin/env bash
# One-shot setup of both dry-run bots on a fresh Ubuntu/Debian VPS.
# Usage (as root): curl -fsSL https://raw.githubusercontent.com/shaqirov/tradingtest/main/scripts/setup-vps.sh | bash
set -euo pipefail

REPO_URL="https://github.com/shaqirov/tradingtest.git"
APP_DIR="/opt/tradingtest"

if [ "$(id -u)" -ne 0 ]; then
    echo "Run this script as root (or via sudo)." >&2
    exit 1
fi

echo "==> Installing base packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl openssl ufw >/dev/null

if ! command -v docker >/dev/null 2>&1; then
    echo "==> Installing Docker"
    curl -fsSL https://get.docker.com | sh >/dev/null
fi
systemctl enable --now docker >/dev/null

# NostalgiaForInfinity is memory hungry: add swap on small servers.
if [ "$(swapon --noheadings | wc -l)" -eq 0 ]; then
    echo "==> Creating 4G swap file"
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile >/dev/null
    swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi

echo "==> Fetching project into $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone -q "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

if [ ! -f .env ]; then
    echo "==> Generating .env with random secrets"
    UI_PASSWORD="pw-$(openssl rand -hex 8)"
    cp .env.example .env
    sed -i \
        -e "s|^FREQTRADE__API_SERVER__PASSWORD=.*|FREQTRADE__API_SERVER__PASSWORD=${UI_PASSWORD}|" \
        -e "s|^FREQTRADE__API_SERVER__JWT_SECRET_KEY=.*|FREQTRADE__API_SERVER__JWT_SECRET_KEY=jwt-$(openssl rand -hex 32)|" \
        -e "s|^FREQTRADE__API_SERVER__WS_TOKEN=.*|FREQTRADE__API_SERVER__WS_TOKEN=ws-$(openssl rand -hex 16)|" \
        .env
    chmod 600 .env
fi

echo "==> Firewall: allow SSH only (FreqUI is reached through an SSH tunnel)"
ufw allow OpenSSH >/dev/null
ufw --force enable >/dev/null

echo "==> Starting bots"
docker compose pull -q
docker compose up -d

UI_USER="$(grep '^FREQTRADE__API_SERVER__USERNAME=' .env | cut -d= -f2-)"
UI_PASS="$(grep '^FREQTRADE__API_SERVER__PASSWORD=' .env | cut -d= -f2-)"
cat <<INFO

Done. Both bots are running in dry-run mode.
  FreqUI login:    ${UI_USER}
  FreqUI password: ${UI_PASS}

Open FreqUI from your computer through an SSH tunnel:
  ssh -N -L 8080:127.0.0.1:8080 -L 8081:127.0.0.1:8081 root@<server-ip>
then browse http://127.0.0.1:8080 (EmaRsi) and http://127.0.0.1:8081 (NFI).
INFO
