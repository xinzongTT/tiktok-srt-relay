#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="8890"
if [ -f .env ]; then
  set -a
  source .env
  set +a
  PORT="${SRT_PORT:-8890}"
fi

echo "== docker ps =="
docker ps --filter name=tiktok-srt-relay

echo
echo "== recent MediaMTX logs =="
docker logs --tail=100 tiktok-srt-relay || true

echo
echo "== UDP listeners =="
ss -lunp | grep ":${PORT}" || true
