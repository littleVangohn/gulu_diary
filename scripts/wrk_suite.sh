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
THREADS="${THREADS:-4}"
CONNECTIONS="${CONNECTIONS:-200}"
DURATION="${DURATION:-30s}"
DEVICE_ID="${DEVICE_ID:-CQU0000000}"
DEVICE_SECRET="${DEVICE_SECRET:-SmnT8UyI3gqmhMc9}"
HIGH="${HIGH:-120}"
LOW="${LOW:-80}"
POOL_COUNT="${POOL_COUNT:-100000}"
RESULT_ROOT="${RESULT_ROOT:-$ROOT_DIR/bench_results}"
RUN_NAME="${RUN_NAME:-wrk_$(date +%Y%m%d_%H%M%S)}"
RESULT_DIR="$RESULT_ROOT/$RUN_NAME"

mkdir -p "$RESULT_DIR"

TICKETS_FILE="$RESULT_DIR/tickets.txt"
GETTOKEN_BODIES_FILE="$RESULT_DIR/gettoken_bodies.jsonl"
TOKENS_FILE="$RESULT_DIR/tokens.txt"
UPLOAD_BODIES_FILE="$RESULT_DIR/upload_bodies.jsonl"

echo "RESULT_DIR=$RESULT_DIR"

{
  echo "BASE_URL=$BASE_URL"
  echo "THREADS=$THREADS"
  echo "CONNECTIONS=$CONNECTIONS"
  echo "DURATION=$DURATION"
  echo "DEVICE_ID=$DEVICE_ID"
  echo "HIGH=$HIGH"
  echo "LOW=$LOW"
  echo "POOL_COUNT=$POOL_COUNT"
  echo "STRICT_SIGNATURE=${STRICT_SIGNATURE:-}"
  echo "STRICT_TOKEN=${STRICT_TOKEN:-}"
  echo "REDIS_WRITE_MODE=${REDIS_WRITE_MODE:-}"
  echo "TICKET_PREFIX=${TICKET_PREFIX:-}"
  echo "DATA_PREFIX=${DATA_PREFIX:-}"
  echo "START_TIME=$(date '+%F %T %z')"
} > "$RESULT_DIR/meta.txt"

echo "== smoke =="
curl -s "$BASE_URL/healthz" | tee "$RESULT_DIR/healthz.json"
echo

echo "== stage 1: getTicket =="
wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency \
  "$BASE_URL/getTicket?deviceId=$DEVICE_ID" \
  | tee "$RESULT_DIR/getTicket.txt"

echo "== prepare getToken pool =="
python3 "$ROOT_DIR/scripts/prepare_wrk_pool.py" tickets \
  --base-url "$BASE_URL" \
  --device-id "$DEVICE_ID" \
  --count "$POOL_COUNT" \
  --out "$TICKETS_FILE" \
  | tee "$RESULT_DIR/prepare_tickets.txt"

python3 "$ROOT_DIR/scripts/prepare_wrk_pool.py" gettoken-bodies \
  --device-id "$DEVICE_ID" \
  --secret "$DEVICE_SECRET" \
  --tickets "$TICKETS_FILE" \
  --out "$GETTOKEN_BODIES_FILE" \
  | tee "$RESULT_DIR/prepare_gettoken_bodies.txt"

echo "== stage 2: getToken =="
export WRK_BODY_POOL_FILE="$GETTOKEN_BODIES_FILE"
wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency \
  -s "$ROOT_DIR/scripts/wrk_pool_post.lua" \
  "$BASE_URL/getToken" \
  | tee "$RESULT_DIR/getToken.txt"

echo "== prepare uploadData pool =="
python3 "$ROOT_DIR/scripts/prepare_wrk_pool.py" tokens \
  --base-url "$BASE_URL" \
  --device-id "$DEVICE_ID" \
  --secret "$DEVICE_SECRET" \
  --count "$POOL_COUNT" \
  --out "$TOKENS_FILE" \
  | tee "$RESULT_DIR/prepare_tokens.txt"

python3 "$ROOT_DIR/scripts/prepare_wrk_pool.py" upload-bodies \
  --device-id "$DEVICE_ID" \
  --tokens "$TOKENS_FILE" \
  --high "$HIGH" \
  --low "$LOW" \
  --out "$UPLOAD_BODIES_FILE" \
  | tee "$RESULT_DIR/prepare_upload_bodies.txt"

echo "== stage 3: uploadData =="
export WRK_BODY_POOL_FILE="$UPLOAD_BODIES_FILE"
wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency \
  -s "$ROOT_DIR/scripts/wrk_pool_post.lua" \
  "$BASE_URL/uploadData" \
  | tee "$RESULT_DIR/uploadData.txt"

{
  echo
  echo "END_TIME=$(date '+%F %T %z')"
  echo "RESULT_DIR=$RESULT_DIR"
} >> "$RESULT_DIR/meta.txt"

echo "done: $RESULT_DIR"
