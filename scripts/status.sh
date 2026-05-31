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
docker ps --filter name=tiktok-srt-relay 2>/dev/null || echo "(Docker may not be running)"

echo
echo "== recent MediaMTX logs =="
docker logs --tail=100 tiktok-srt-relay 2>/dev/null || echo "(container not found or not running)"

echo
echo "== active stream status =="
docker logs --tail=500 tiktok-srt-relay 2>/dev/null | grep -E "(is publishing|is reading|closed)" | tail -20 || echo "(no stream activity detected)"

echo
echo "== UDP listeners =="
ss -lunp 2>/dev/null | grep ":${PORT}" || echo "(port ${PORT} may not be listening, try: sudo bash scripts/status.sh)"
