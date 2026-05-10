#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export GOPROXY="${GOPROXY:-https://goproxy.cn,direct}"
export GOSUMDB="${GOSUMDB:-sum.golang.google.cn}"

mkdir -p bin
go mod tidy
go build -trimpath -ldflags="-s -w" -o bin/race-server ./cmd/race-server
echo "built: $ROOT_DIR/bin/race-server"
