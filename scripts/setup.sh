#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
export APT_LISTCHANGES_FRONTEND=none

if command -v sudo >/dev/null 2>&1 && [ "$(id -u)" -ne 0 ]; then
  SUDO="sudo"
else
  SUDO=""
fi

if ! apt-cache show docker-compose-plugin >/dev/null 2>&1; then
  DOCKER_COMPOSE_PACKAGE="docker-compose-v2"
else
  DOCKER_COMPOSE_PACKAGE="docker-compose-plugin"
fi

$SUDO apt-get update
$SUDO apt-get install -y docker.io "$DOCKER_COMPOSE_PACKAGE" ffmpeg ufw openssl python3 curl

$SUDO systemctl enable --now docker

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD=(docker-compose)
else
  echo "Docker Compose command not found after installation."
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env

  PUBLIC_IP="$(curl -4 --max-time 10 -s https://ifconfig.me || true)"
  if [ -z "$PUBLIC_IP" ]; then
    # filter out Docker bridge, loopback, and link-local IPs
    PUBLIC_IP="$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -vE '^172\.(1[6-9]|2[0-9]|3[0-1])\.|^10\.|^192\.168\.|^127\.|^169\.254\.' | head -1)"
  fi
  if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP="YOUR_SERVER_PUBLIC_IP_OR_DOMAIN"
  fi

  PUB_PASS="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24)"
  READ_PASS="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24)"
  MUSIC_PUB_PASS="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24)"
  MUSIC_READ_PASS="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 24)"

  sed -i "s/YOUR_SERVER_PUBLIC_IP_OR_DOMAIN/${PUBLIC_IP}/g" .env
  sed -i "s/CHANGE_ME_PUBLISH_123456/${PUB_PASS}/g" .env
  sed -i "s/CHANGE_ME_READ_123456/${READ_PASS}/g" .env
  sed -i "s/CHANGE_ME_MUSIC_PUB_123456/${MUSIC_PUB_PASS}/g" .env
  sed -i "s/CHANGE_ME_MUSIC_READ_123456/${MUSIC_READ_PASS}/g" .env
fi

bash scripts/render-config.sh

set -a
source .env
set +a

$SUDO ufw allow 22/tcp
$SUDO ufw allow "${SRT_PORT}/udp"
if ! ufw status | grep -q "^Status: active"; then
  $SUDO ufw --force enable
fi

if ! "${COMPOSE_CMD[@]}" up -d; then
  echo "Primary image failed, retrying with :latest (one-time, config unchanged)..."
  MEDIAMTX_IMAGE="bluenviron/mediamtx:latest" "${COMPOSE_CMD[@]}" up -d
fi

# Install global tkm command
$SUDO install -m 755 /dev/stdin /usr/local/bin/tkm <<'TKMSCRIPT'
#!/bin/bash
cd /opt/tiktok-srt-relay && bash scripts/manage.sh
TKMSCRIPT

echo
echo "MediaMTX SRT relay is running."
echo
echo "Phone publish URL:"
echo "srt://${PUBLIC_HOST}:${SRT_PORT}?streamid=publish:${STREAM_PATH}&pkt_size=1316&latency=${SRT_PUBLISH_LATENCY:-500}&passphrase=${SRT_PUBLISH_PASSPHRASE}&pbkeylen=16"
echo
echo "OBS read URL:"
echo "srt://${PUBLIC_HOST}:${SRT_PORT}?streamid=read:${STREAM_PATH}&latency=${SRT_READ_LATENCY:-500000}&passphrase=${SRT_READ_PASSPHRASE}&pbkeylen=16"
echo
echo "OBS Media Source Input Format:"
echo "mpegts"
echo
echo "Quick manage: tkm"
echo "========================================="
echo "Music sync channel (US desktop -> China):"
echo "-----------------------------------------"
echo "US FFmpeg push command:"
echo "ffmpeg -f dshow -i audio=\"YOUR_AUDIO_DEVICE\" -c:a libmp3lame -b:a 128k -f mpegts \"srt://${PUBLIC_HOST}:${SRT_PORT}?streamid=publish:${MUSIC_PATH}&pkt_size=1316&latency=${MUSIC_LATENCY:-500000}&passphrase=${MUSIC_PUBLISH_PASSPHRASE}&pbkeylen=16\""
echo
echo "China ffplay pull command:"
echo "ffplay -i \"srt://${PUBLIC_HOST}:${SRT_PORT}?streamid=read:${MUSIC_PATH}&latency=${MUSIC_LATENCY:-500000}&passphrase=${MUSIC_READ_PASSPHRASE}&pbkeylen=16\""
echo
