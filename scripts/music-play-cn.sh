#!/usr/bin/env bash
# music-play-cn.sh
# China side: pull music stream from VPS and play locally
# Usage: bash scripts/music-play-cn.sh
set -euo pipefail

cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

if [ ! -f .env ]; then
  echo -e "${RED}[ERROR] .env not found. Copy .env.example from VPS and fill in values.${NC}"
  exit 1
fi

set -a
source .env
set +a

MUSIC_PATH="${MUSIC_PATH:-music}"
MUSIC_LATENCY="${MUSIC_LATENCY:-500000}"

if [ -z "${PUBLIC_HOST:-}" ] || [ -z "${SRT_PORT:-}" ] || [ -z "${MUSIC_READ_PASSPHRASE:-}" ]; then
  echo -e "${RED}[ERROR] Missing env vars: PUBLIC_HOST, SRT_PORT, MUSIC_READ_PASSPHRASE${NC}"
  exit 1
fi

SRT_URL="srt://${PUBLIC_HOST}:${SRT_PORT}?streamid=read:${MUSIC_PATH}&latency=${MUSIC_LATENCY}&passphrase=${MUSIC_READ_PASSPHRASE}&pbkeylen=16"

PLAYER=""
PLAYER_ARGS=()

if command -v ffplay >/dev/null 2>&1; then
  PLAYER="ffplay"
  PLAYER_ARGS=(-i "$SRT_URL" -nodisp)
elif command -v vlc >/dev/null 2>&1; then
  PLAYER="vlc"
  PLAYER_ARGS=(-I dummy --play-and-exit "$SRT_URL")
elif command -v mpv >/dev/null 2>&1; then
  PLAYER="mpv"
  PLAYER_ARGS=(--no-video "$SRT_URL")
else
  echo -e "${RED}[ERROR] No supported player found.${NC}"
  echo "Install one of: ffplay, vlc, mpv"
  exit 1
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  Music Player - VPS -> China${NC}"
echo -e "${CYAN}========================================${NC}"
echo -e "VPS    : ${PUBLIC_HOST}:${SRT_PORT}"
echo -e "Path   : read:${MUSIC_PATH}"
echo -e "Latency: ${MUSIC_LATENCY} us ($((MUSIC_LATENCY / 1000)) ms)"
echo -e "Player : ${PLAYER}"
echo -e ""
echo -e "${YELLOW}Press Ctrl+C to stop.${NC}"
echo -e ""

exec "$PLAYER" "${PLAYER_ARGS[@]}"
