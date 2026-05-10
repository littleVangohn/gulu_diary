#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

set -a
source configs/race.env
set +a

BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT:-5000}}"
THREADS="${THREADS:-4}"
CONNECTIONS="${CONNECTIONS:-200}"
DURATION="${DURATION:-30s}"
DEVICE_ID="${DEVICE_ID:-20845}"
HIGH="${HIGH:-120}"
LOW="${LOW:-90}"

TMP_DIR="${ROOT_DIR}/tmp"
mkdir -p "$TMP_DIR"
BODY_FILE="${TMP_DIR}/wrk_upload_body.json"

python3 "$ROOT_DIR/scripts/prepare_upload_body.py" \
  --base-url "$BASE_URL" \
  --secret "$SECRET" \
  --device-id "$DEVICE_ID" \
  --high "$HIGH" \
  --low "$LOW" \
  --out "$BODY_FILE"

export WRK_BODY_FILE="$BODY_FILE"
wrk -t"$THREADS" -c"$CONNECTIONS" -d"$DURATION" --latency -s "$ROOT_DIR/scripts/bench_post.lua" "$BASE_URL/uploadData"
