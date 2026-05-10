#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <deviceId> [count]"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

set -a
source configs/race.env
set +a

DEVICE_ID="$1"
COUNT="${2:-10}"
MODE="${REDIS_WRITE_MODE:-list}"

REDIS_CLI_ARGS=(-h "${REDIS_ADDR%:*}" -p "${REDIS_ADDR##*:}")
if [[ -n "${REDIS_PASSWORD:-}" ]]; then
  REDIS_CLI_ARGS+=(-a "$REDIS_PASSWORD")
fi
if [[ -n "${REDIS_DB:-}" ]]; then
  REDIS_CLI_ARGS+=(-n "$REDIS_DB")
fi

if [[ "$MODE" == "stream" ]]; then
  redis-cli "${REDIS_CLI_ARGS[@]}" XRANGE "${DATA_PREFIX}${DEVICE_ID}" - + COUNT "$COUNT"
else
  redis-cli --raw "${REDIS_CLI_ARGS[@]}" LRANGE "${DATA_PREFIX}${DEVICE_ID}" 0 "$((COUNT - 1))" | while IFS= read -r line; do
    if [[ "$line" == *"|"* ]]; then
      IFS='|' read -r measure_time high low received_time <<<"$line"
      echo "{\"deviceId\":\"${DEVICE_ID}\",\"time\":${measure_time},\"high\":${high},\"low\":${low},\"receivedTime\":${received_time}}"
    else
      echo "$line"
    fi
  done
fi
