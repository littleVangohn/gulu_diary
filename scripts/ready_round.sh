#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f configs/race.env ]]; then
  echo "missing configs/race.env"
  echo "copy configs/race.env.example to configs/race.env first"
  exit 1
fi

set -a
source configs/race.env
set +a

BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT:-5000}}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-}"
DEVICE_ID="${DEVICE_ID:-20845}"
HEALTH_TIMEOUT_SECONDS="${HEALTH_TIMEOUT_SECONDS:-30}"
DO_TUNE="${DO_TUNE:-0}"
DO_BUILD="${DO_BUILD:-1}"
DO_SMOKE="${DO_SMOKE:-1}"
DO_FINAL_CLEANUP="${DO_FINAL_CLEANUP:-1}"

REDIS_CLI_ARGS=(-h "${REDIS_ADDR%:*}" -p "${REDIS_ADDR##*:}")
if [[ -n "${REDIS_PASSWORD:-}" ]]; then
  REDIS_CLI_ARGS+=(-a "$REDIS_PASSWORD")
fi
if [[ -n "${REDIS_DB:-}" ]]; then
  REDIS_CLI_ARGS+=(-n "$REDIS_DB")
fi

need_cmd() {
  local name="$1"
  command -v "$name" >/dev/null 2>&1 || {
    echo "missing command: $name"
    exit 1
  }
}

wait_health() {
  local url="$1"
  local timeout="$2"
  local i
  for ((i = 1; i <= timeout; i++)); do
    if curl -fsS "${url}/healthz" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

count_keys() {
  local pattern="$1"
  redis-cli "${REDIS_CLI_ARGS[@]}" --scan --pattern "$pattern" | wc -l | tr -d ' '
}

data_len() {
  redis-cli "${REDIS_CLI_ARGS[@]}" LLEN "${DATA_PREFIX}${DEVICE_ID}" 2>/dev/null || echo 0
}

echo "==== Ready Round Config ===="
echo "BASE_URL=${BASE_URL}"
echo "PUBLIC_BASE_URL=${PUBLIC_BASE_URL:-<skip>}"
echo "PORT=${PORT}"
echo "DEVICE_ID=${DEVICE_ID}"
echo "DO_TUNE=${DO_TUNE}"
echo "DO_BUILD=${DO_BUILD}"
echo "DO_SMOKE=${DO_SMOKE}"
echo "DO_FINAL_CLEANUP=${DO_FINAL_CLEANUP}"
echo

need_cmd curl
need_cmd redis-cli
need_cmd python3
need_cmd pgrep

if [[ "$DO_TUNE" == "1" ]]; then
  echo "== 1. tune linux =="
  "${ROOT_DIR}/scripts/tune_linux.sh"
  echo
fi

if [[ "$DO_BUILD" == "1" ]]; then
  echo "== 2. build =="
  "${ROOT_DIR}/scripts/build_linux.sh"
  echo
fi

echo "== 3. stop old server =="
"${ROOT_DIR}/scripts/stop_linux.sh"
echo

echo "== 4. cleanup redis before round =="
"${ROOT_DIR}/scripts/cleanup_round.sh"
echo "ticket_keys=$(count_keys "${TICKET_PREFIX}*")"
echo "data_keys=$(count_keys "${DATA_PREFIX}*")"
echo

echo "== 5. start server =="
"${ROOT_DIR}/scripts/start_linux.sh"
echo

echo "== 6. wait local health =="
if ! wait_health "$BASE_URL" "$HEALTH_TIMEOUT_SECONDS"; then
  echo "health check failed: ${BASE_URL}/healthz"
  exit 1
fi
curl -fsS "${BASE_URL}/healthz"
echo
echo

if [[ -n "$PUBLIC_BASE_URL" ]]; then
  echo "== 7. public health =="
  curl -fsS "${PUBLIC_BASE_URL}/healthz" || {
    echo "public health check failed: ${PUBLIC_BASE_URL}/healthz"
    exit 1
  }
  echo
  echo
else
  echo "== 7. public health =="
  echo "skip"
  echo
fi

if [[ "$DO_SMOKE" == "1" ]]; then
  echo "== 8. protocol smoke =="
  BASE_URL="$BASE_URL" DEVICE_ID="$DEVICE_ID" "${ROOT_DIR}/scripts/smoke_test.sh"
  echo

  echo "== 9. verify db write =="
  echo "device_llen=$(data_len)"
  "${ROOT_DIR}/scripts/query_device.sh" "$DEVICE_ID" 1
  echo
else
  echo "== 8. protocol smoke =="
  echo "skip"
  echo
fi

if [[ "$DO_FINAL_CLEANUP" == "1" ]]; then
  echo "== 10. final cleanup =="
  "${ROOT_DIR}/scripts/cleanup_round.sh"
  echo "ticket_keys=$(count_keys "${TICKET_PREFIX}*")"
  echo "data_keys=$(count_keys "${DATA_PREFIX}*")"
  echo
else
  echo "== 10. final cleanup =="
  echo "skip"
  echo
fi

echo "== 11. final status =="
"${ROOT_DIR}/scripts/status.sh"
echo
echo "ready for next round"
