#!/usr/bin/env bash
# Backtest the NFI bot with its current live settings over a recent period:
# takes the bot's current pairlist (test-pairlist), downloads candles and runs the backtest.
# Usage (on the server, from /opt/tradingtest): bash scripts/backtest-recent.sh 20261016- [pairlist-config]
# pairlist-config defaults to user_data/pairs-live-wide.json (the live bot's pairlist).
set -euo pipefail
cd "$(dirname "$0")/.."

TIMERANGE="${1:?usage: $0 <timerange, e.g. 20261016- or 20261016-20261025>}"
START="${TIMERANGE:0:8}"
PAIRLIST_CFG="${2:-user_data/pairs-live-wide.json}"
# The 'freqtrade' service is not running (profile), so its one-off containers never clash with the bot.
RUN="docker compose run --rm -T freqtrade"
CFG="--config /freqtrade/user_data/config.json --config /freqtrade/user_data/config-nfi.json --config /freqtrade/user_data/blacklist-binance.json"
PAIRS_FILE="user_data/pairs-backtest-current.json"

echo "==> Current pairlist from $PAIRLIST_CFG"
$RUN test-pairlist $CFG --config "/freqtrade/$PAIRLIST_CFG" --print-json 2>/dev/null \
    | grep '^\[' | tail -1 > "$PAIRS_FILE.tmp"
python3 - "$PAIRS_FILE.tmp" "$PAIRS_FILE" <<'PY'
import json, sys
pairs = json.load(open(sys.argv[1]))
if not pairs:
    sys.exit("Pairlist is empty")
json.dump({"exchange": {"pair_whitelist": pairs}, "pairlists": [{"method": "StaticPairList"}]},
          open(sys.argv[2], "w"), indent=4)
print(f"{len(pairs)} pairs: {' '.join(pairs)}")
PY
rm -f "$PAIRS_FILE.tmp"

# NFI needs history before the start date for its indicators (startup candles + informative timeframes).
SHORT_FROM="$(date -d "$START -40 days" +%Y%m%d)"
LONG_FROM="$(date -d "$START -300 days" +%Y%m%d)"
echo "==> Downloading candles (5m/15m/1h from $SHORT_FROM, 4h/1d from $LONG_FROM)"
$RUN download-data $CFG --config "/freqtrade/$PAIRS_FILE" --timerange "$SHORT_FROM-" --timeframes 5m 15m 1h
$RUN download-data $CFG --config "/freqtrade/$PAIRS_FILE" --timerange "$LONG_FROM-" --timeframes 4h 1d

echo "==> Backtesting $TIMERANGE"
$RUN backtesting $CFG --config "/freqtrade/$PAIRS_FILE" \
    --strategy NostalgiaForInfinityX7Ru --timerange "$TIMERANGE" --enable-protections --breakdown day
