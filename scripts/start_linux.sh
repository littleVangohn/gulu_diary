#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f configs/race.env ]]; then
  echo "missing configs/race.env"
  echo "copy configs/race.env.example to configs/race.env first"
  exit 1
fi

mkdir -p logs
set -a
source configs/race.env
set +a

if [[ ! -x bin/race-server ]]; then
  "$ROOT_DIR/scripts/build_linux.sh"
fi

pkill -f "bin/race-server" 2>/dev/null || true
nohup "$ROOT_DIR/bin/race-server" > "$ROOT_DIR/logs/server.log" 2>&1 &
sleep 1
pgrep -af "bin/race-server" || true
echo "started"
