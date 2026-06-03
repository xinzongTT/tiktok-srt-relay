#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo ".env not found. Run scripts/setup.sh first."
  exit 1
fi

source .env

if [ -n "${MUSIC_PATH:-}" ] && [ -n "${MUSIC_PUBLISH_PASSPHRASE:-}" ] && [ -n "${MUSIC_READ_PASSPHRASE:-}" ]; then
  echo "Music channel already configured in .env"
else
  echo "Adding music channel to .env..."
  MUSIC_PUB_PASS="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24)"
  MUSIC_READ_PASS="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24)"

  cat >> .env <<EOF

# Music sync channel
MUSIC_PATH=music
MUSIC_PUBLISH_PASSPHRASE=${MUSIC_PUB_PASS}
MUSIC_READ_PASSPHRASE=${MUSIC_READ_PASS}
MUSIC_LATENCY=500000
EOF
fi

if ! grep -q "__MUSIC_PATH__" mediamtx.yml.template 2>/dev/null; then
  echo "mediamtx.yml.template does not contain music path placeholders."
  echo "Please update mediamtx.yml.template first (git pull)."
  exit 1
fi

bash scripts/render-config.sh

COMPOSE_CMD=()
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "Docker Compose not found."
  exit 1
fi

"${COMPOSE_CMD[@]}" restart

set -a
source .env
set +a

echo
echo "Music channel added. Restarting MediaMTX..."
echo
echo "US ffmpeg push command (audio only):"
echo "ffmpeg -f dshow -i audio=\"YOUR_AUDIO_DEVICE\" -c:a libmp3lame -b:a 128k -f mpegts \"srt://${PUBLIC_HOST}:${SRT_PORT}?streamid=publish:${MUSIC_PATH}&pkt_size=1316&latency=${MUSIC_LATENCY:-500000}&passphrase=${MUSIC_PUBLISH_PASSPHRASE}&pbkeylen=16\""
echo
echo "China ffplay pull command:"
echo "ffplay -i \"srt://${PUBLIC_HOST}:${SRT_PORT}?streamid=read:${MUSIC_PATH}&latency=${MUSIC_LATENCY:-500000}&passphrase=${MUSIC_READ_PASSPHRASE}&pbkeylen=16\""
echo
