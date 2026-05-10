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

REDIS_CLI_ARGS=(-h "${REDIS_ADDR%:*}" -p "${REDIS_ADDR##*:}")
if [[ -n "${REDIS_PASSWORD:-}" ]]; then
  REDIS_CLI_ARGS+=(-a "$REDIS_PASSWORD")
fi
if [[ -n "${REDIS_DB:-}" ]]; then
  REDIS_CLI_ARGS+=(-n "$REDIS_DB")
fi

delete_keys() {
  local pattern="$1"
  local keys=()

  while IFS= read -r key; do
    [[ -z "$key" ]] && continue
    keys+=("$key")
    if [[ "${#keys[@]}" -ge 500 ]]; then
      redis-cli "${REDIS_CLI_ARGS[@]}" UNLINK "${keys[@]}" >/dev/null 2>&1 \
        || redis-cli "${REDIS_CLI_ARGS[@]}" DEL "${keys[@]}" >/dev/null
      keys=()
    fi
  done < <(redis-cli "${REDIS_CLI_ARGS[@]}" --scan --pattern "$pattern" || true)

  if [[ "${#keys[@]}" -gt 0 ]]; then
    redis-cli "${REDIS_CLI_ARGS[@]}" UNLINK "${keys[@]}" >/dev/null 2>&1 \
      || redis-cli "${REDIS_CLI_ARGS[@]}" DEL "${keys[@]}" >/dev/null
  fi
}

delete_keys "${TICKET_PREFIX}*"
delete_keys "${DATA_PREFIX}*"

echo "cleanup done"
