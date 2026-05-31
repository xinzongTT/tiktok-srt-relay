#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

set -a
source .env
set +a

URL="srt://127.0.0.1:${SRT_PORT}?streamid=publish:${STREAM_PATH}&pkt_size=1316&latency=${SRT_LATENCY_US}&passphrase=${SRT_PUBLISH_PASSPHRASE}&pbkeylen=16"

echo "Publishing test stream to:"
echo "$URL"

ffmpeg -re \
  -f lavfi -i "testsrc=size=720x1280:rate=30" \
  -f lavfi -i "sine=frequency=1000:sample_rate=44100" \
  -c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p \
  -b:v 2500k -maxrate 2500k -bufsize 5000k -g 60 \
  -c:a aac -b:a 128k -ar 44100 \
  -f mpegts "$URL"
