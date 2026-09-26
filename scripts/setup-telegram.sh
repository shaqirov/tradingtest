#!/usr/bin/env bash
# Interactive Telegram setup for both bots. Run from the project: bash scripts/setup-telegram.sh
# Each bot needs its own Telegram bot token: two bots polling one token conflict.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
    echo ".env not found - run scripts/setup-vps.sh first." >&2
    exit 1
fi

read -rp "Your Telegram chat id (digits, from @userinfobot): " CHAT_ID
read -rp "Token of Telegram bot #1 (EmaRsi): " TOKEN_MAIN
read -rp "Token of Telegram bot #2 (NFI), empty to disable NFI notifications: " TOKEN_NFI

TOKEN_RE='^[0-9]+:[A-Za-z0-9_-]+$'
[[ "$CHAT_ID" =~ ^-?[0-9]+$ ]] || { echo "Chat id must be a number." >&2; exit 1; }
[[ "$TOKEN_MAIN" =~ $TOKEN_RE ]] || { echo "Token #1 looks wrong (expected 123456:ABC...)." >&2; exit 1; }
if [ -n "$TOKEN_NFI" ]; then
    [[ "$TOKEN_NFI" =~ $TOKEN_RE ]] || { echo "Token #2 looks wrong (expected 123456:ABC...)." >&2; exit 1; }
    [ "$TOKEN_NFI" != "$TOKEN_MAIN" ] || { echo "Token #2 must differ from token #1." >&2; exit 1; }
fi

set_var() {
    local file="$1" key="$2" value="$3"
    if grep -q "^${key}=" "$file"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "$file"
    else
        echo "${key}=${value}" >> "$file"
    fi
}

set_var .env FREQTRADE__TELEGRAM__ENABLED true
set_var .env FREQTRADE__TELEGRAM__TOKEN "$TOKEN_MAIN"
set_var .env FREQTRADE__TELEGRAM__CHAT_ID "$CHAT_ID"

if [ -n "$TOKEN_NFI" ]; then
    printf 'FREQTRADE__TELEGRAM__TOKEN=%s\n' "$TOKEN_NFI" > .env.nfi
else
    printf 'FREQTRADE__TELEGRAM__ENABLED=false\n' > .env.nfi
fi
chmod 600 .env .env.nfi

echo "==> Restarting bots"
docker compose up -d
echo "Done. Each Telegram bot should send a 'Starting' message within a minute."
