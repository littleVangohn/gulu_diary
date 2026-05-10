#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f configs/race.env ]]; then
  echo "missing configs/race.env"
  exit 1
fi

set -a
source configs/race.env
set +a

BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT:-5000}}"
DEVICE_ID="${DEVICE_ID:-20845}"
TAIL_LINES="${TAIL_LINES:-20}"

REDIS_CLI_ARGS=(-h "${REDIS_ADDR%:*}" -p "${REDIS_ADDR##*:}")
if [[ -n "${REDIS_PASSWORD:-}" ]]; then
  REDIS_CLI_ARGS+=(-a "$REDIS_PASSWORD")
fi
if [[ -n "${REDIS_DB:-}" ]]; then
  REDIS_CLI_ARGS+=(-n "$REDIS_DB")
fi

count_keys() {
  local pattern="$1"
  local count
  count=$(redis-cli "${REDIS_CLI_ARGS[@]}" --scan --pattern "$pattern" | wc -l | tr -d ' ')
  echo "${count:-0}"
}

echo "== config =="
echo "BASE_URL=${BASE_URL}"
echo "PORT=${PORT}"
echo "REDIS_ADDR=${REDIS_ADDR}"
echo "REDIS_DB=${REDIS_DB:-0}"
echo "REDIS_WRITE_MODE=${REDIS_WRITE_MODE:-list}"
echo

echo "== process =="
pgrep -af "bin/race-server" || echo "race-server not running"
echo

echo "== port =="
ss -lntp 2>/dev/null | grep -F ":${PORT} " || echo "port ${PORT} not listening"
echo

echo "== health =="
curl -fsS "${BASE_URL}/healthz" || echo "health check failed"
echo
echo

echo "== redis =="
redis-cli "${REDIS_CLI_ARGS[@]}" ping
echo "ticket_keys=$(count_keys "${TICKET_PREFIX}*")"
echo "data_keys=$(count_keys "${DATA_PREFIX}*")"
echo "sample_device=${DEVICE_ID}"
redis-cli "${REDIS_CLI_ARGS[@]}" LLEN "${DATA_PREFIX}${DEVICE_ID}" 2>/dev/null || true
echo

echo "== log tail =="
tail -n "${TAIL_LINES}" "${ROOT_DIR}/logs/server.log" 2>/dev/null || echo "logs/server.log not found"
