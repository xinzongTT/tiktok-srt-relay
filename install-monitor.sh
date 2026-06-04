#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/xinzongTT/tiktok-srt-relay.git"
INSTALL_DIR="/opt/tiktok-srt-relay"
DEFAULT_HUB="http://23.238.118.221:9988/api/report"
ENV_FILE="/etc/tiktok-srt-reporter.env"
SERVICE_FILE="/etc/systemd/system/tiktok-srt-reporter.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "[!] 请用 root 执行，或使用 sudo bash"
  exit 1
fi

echo "[0/5] 检查依赖 ..."
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq git python3 curl
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y git python3 curl
elif command -v yum >/dev/null 2>&1; then
  yum install -y git python3 curl
fi

echo "[1/5] 安装或更新 relay 仓库 ..."
mkdir -p "$(dirname "$INSTALL_DIR")"
if [ -d "$INSTALL_DIR/.git" ]; then
  cd "$INSTALL_DIR"
  git remote set-url origin "$REPO_URL"
  git fetch origin master
  git reset --hard origin/master
else
  rm -rf "$INSTALL_DIR"
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

chmod +x scripts/*.sh scripts/*.py 2>/dev/null || true

if [ -f "$INSTALL_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$INSTALL_DIR/.env"
  set +a
fi

HUB="${HUB:-$DEFAULT_HUB}"
MTX_API="${MTX_API:-http://127.0.0.1:9997/v3/paths/list}"
MTX_AUTH="${MTX_AUTH:-admin:monitor}"
NAME="${NAME:-${REPORTER_NAME:-$(hostname)}}"
SRT_HOST="${SRT_HOST:-${PUBLIC_HOST:-$(curl -fsS --max-time 5 https://api.ipify.org 2>/dev/null || hostname -I | awk '{print $1}')}}"
SRT_PORT="${SRT_PORT:-8890}"
REPORT_INTERVAL="${REPORT_INTERVAL:-5}"
REPORT_TOKEN="${REPORT_TOKEN:-}"

echo "[2/5] 写入 reporter 配置 ..."
cat > "$ENV_FILE" <<EOF
HUB=$HUB
MTX_API=$MTX_API
MTX_AUTH=$MTX_AUTH
NAME=$NAME
SRT_HOST=$SRT_HOST
SRT_PORT=$SRT_PORT
REPORT_INTERVAL=$REPORT_INTERVAL
REPORT_TOKEN=$REPORT_TOKEN
EOF
chmod 600 "$ENV_FILE"

echo "[3/5] 创建 systemd 服务 ..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=TikTok SRT Relay Reporter
After=network.target docker.service
Wants=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$ENV_FILE
ExecStart=/bin/bash /opt/tiktok-srt-relay/scripts/reporter-start.sh
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

echo "[4/5] 启动 reporter ..."
systemctl daemon-reload
systemctl enable tiktok-srt-reporter
systemctl restart tiktok-srt-reporter
sleep 2

echo "[5/5] 验证状态 ..."
systemctl --no-pager --full status tiktok-srt-reporter || true
echo ""
echo "Reporter 配置："
echo "  HUB=$HUB"
echo "  MTX_API=$MTX_API"
echo "  NAME=$NAME"
echo "  SRT_HOST=$SRT_HOST"
echo "  SRT_PORT=$SRT_PORT"
if [ -n "$REPORT_TOKEN" ]; then
  echo "  REPORT_TOKEN=已设置"
else
  echo "  REPORT_TOKEN=未设置"
fi
echo ""
echo "查看日志：journalctl -u tiktok-srt-reporter -f"
