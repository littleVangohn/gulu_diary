#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

set -a
source configs/race.env
set +a

BASE_URL="${BASE_URL:-http://127.0.0.1:${PORT:-5000}}"
DEVICE_ID="${DEVICE_ID:-20845}"

echo "== getTicket =="
curl -s "${BASE_URL}/getTicket?deviceId=${DEVICE_ID}" | tee /tmp/get_ticket.json
TICKET=$(python3 - <<'PY'
import json
with open('/tmp/get_ticket.json','r',encoding='utf-8') as f:
    print(json.load(f)['data']['ticket'])
PY
)

SIG=$(python3 - <<PY
import hashlib
ticket = "${TICKET}"
device = "${DEVICE_ID}"
secret = "${SECRET}"
print(hashlib.md5((ticket + device + secret).encode()).hexdigest())
PY
)

echo "== getToken =="
curl -s -X POST "${BASE_URL}/getToken" \
  -H "Content-Type: application/json" \
  -d "{\"deviceId\":\"${DEVICE_ID}\",\"signature\":\"${SIG}\",\"ticket\":\"${TICKET}\"}" | tee /tmp/get_token.json

TOKEN=$(python3 - <<'PY'
import json
with open('/tmp/get_token.json','r',encoding='utf-8') as f:
    print(json.load(f)['data']['token'])
PY
)

NOW_TS=$(date +%s)
echo "== uploadData =="
curl -s -X POST "${BASE_URL}/uploadData" \
  -H "Content-Type: application/json" \
  -d "{\"deviceId\":\"${DEVICE_ID}\",\"token\":\"${TOKEN}\",\"data\":{\"time\":${NOW_TS},\"high\":120,\"low\":90}}"
