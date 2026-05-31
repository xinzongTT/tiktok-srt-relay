#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

set -a
source .env
set +a

URL="srt://127.0.0.1:${SRT_PORT}?streamid=read:${STREAM_PATH}&latency=${SRT_LATENCY_US}&passphrase=${SRT_READ_PASSPHRASE}&pbkeylen=16"

echo "Reading test stream from:"
echo "$URL"

timeout 15 ffmpeg -i "$URL" -t 10 -f null -
