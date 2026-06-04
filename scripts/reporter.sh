#!/usr/bin/env bash
# reporter.sh - Report stream status to central hub
# Usage: bash scripts/reporter.sh <HUB_IP> [HUB_PORT]
#        bash scripts/reporter.sh 154.12.53.31 9988

set -euo pipefail
cd "$(dirname "$0")/.."

HUB_HOST="${1:-}"
HUB_PORT="${2:-9988}"

if [ -z "$HUB_HOST" ]; then
  echo "Usage: bash scripts/reporter.sh <HUB_IP> [HUB_PORT]"
  echo "Example: bash scripts/reporter.sh 154.12.53.31"
  exit 1
fi

source .env 2>/dev/null || true
SRT_PORT="${SRT_PORT:-8890}"
SERVER_NAME="${REPORTER_NAME:-$(hostname)}"

get_streams() {
  python3 -c '
import json, sys, re, subprocess
from pathlib import Path

yml = Path("mediamtx.yml")
if not yml.exists():
    print(json.dumps([]))
    sys.exit(0)

text = yml.read_text()
paths = []
for line in text.splitlines():
    if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
        name = line.strip()[:-1]
        if name:
            paths.append(name)

try:
    r = subprocess.run(["docker","logs","--tail=300","tiktok-srt-relay"], capture_output=True, text=True, timeout=8)
    logs = r.stdout if r.returncode == 0 else ""
except:
    logs = ""

result = []
for path in paths:
    publishing = False
    readers = 0
    last_event = ""
    p_pub = f"is publishing to path {repr(path)}"
    p_read = f"is reading from path {repr(path)}"
    for line in logs.splitlines():
        if p_pub in line:
            publishing = True
            last_event = line.split(" INF ")[-1] if " INF " in line else line
        elif p_read in line:
            readers += 1
            last_event = line.split(" INF ")[-1] if " INF " in line else line
    result.append({"name": path, "publishing": publishing, "readers": readers, "last_event": last_event or "--"})

print(json.dumps(result, ensure_ascii=False))
'
}

# Run in loop
echo "[reporter] Hub: ${HUB_HOST}:${HUB_PORT}  Server: ${SERVER_NAME}"
while true; do
  STREAMS=$(get_streams 2>/dev/null || echo "[]")
  curl -s -X POST "http://${HUB_HOST}:${HUB_PORT}/api/report" \
    -H "Content-Type: application/json" \
    -d "{\"name\":\"${SERVER_NAME}\",\"host\":\"${PUBLIC_HOST:-?}\",\"port\":\"${SRT_PORT}\",\"streams\":${STREAMS}}" \
    > /dev/null 2>&1 || true
  sleep 5
done
