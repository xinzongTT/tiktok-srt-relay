#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/xinzongTT/tiktok-srt-relay.git"
INSTALL_DIR="/opt/tiktok-srt-relay"

if [ "$(id -u)" -ne 0 ]; then
  echo "[!] 请用 root 执行，或前面加 sudo bash"
  exit 1
fi

echo "[0/3] 检查依赖 ..."
if ! command -v git >/dev/null 2>&1; then
  echo "      安装 git ..."
  apt-get update -qq
  apt-get install -y -qq git
fi

echo "[1/3] 克隆仓库到 ${INSTALL_DIR} ..."
if [ -d "$INSTALL_DIR" ]; then
  echo "      目录已存在，跳过克隆。"
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

if [ ! -d "$INSTALL_DIR" ]; then
  echo "[!] 克隆失败，请检查网络和仓库地址。"
  exit 1
fi

cd "$INSTALL_DIR"

echo "[2/3] 赋予脚本执行权限 ..."
chmod +x scripts/*.sh scripts/*.py 2>/dev/null || true

echo "[3/3] 执行安装 ..."
echo ""
bash scripts/setup.sh

echo ""
echo "============================================"
echo "  安装完成！"
echo ""
echo "  多路推流管理: python3 scripts/manage.py"
echo "  查看状态:     bash scripts/status.sh"
echo "============================================"
