#!/usr/bin/env bash
set -euo pipefail

pkill -f "bin/race-server" 2>/dev/null || true
echo "stopped"
