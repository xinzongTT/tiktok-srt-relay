#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export HUB="${HUB:-http://23.238.118.221:9988/api/report}"
export MTX_API="${MTX_API:-http://127.0.0.1:9997/v3/paths/list}"
export MTX_AUTH="${MTX_AUTH:-admin:monitor}"
export NAME="${NAME:-${REPORTER_NAME:-$(hostname)}}"
export SRT_HOST="${SRT_HOST:-${PUBLIC_HOST:-?}}"
export SRT_PORT="${SRT_PORT:-8890}"
export REPORT_INTERVAL="${REPORT_INTERVAL:-5}"
export REPORT_TOKEN="${REPORT_TOKEN:-}"

exec python3 scripts/reporter.py
