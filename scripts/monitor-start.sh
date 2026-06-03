#!/usr/bin/env bash
# Start stream monitor in background
cd "$(dirname "$0")/.."
pkill -f "python3.*monitor.py" 2>/dev/null || true
nohup python3 scripts/monitor.py > /tmp/srt-monitor.log 2>&1 &
echo "Monitor started: http://$(grep PUBLIC_HOST .env 2>/dev/null | cut -d= -f2):9988"
