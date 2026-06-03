#!/usr/bin/env python3
"""Stream monitor web server for TikTok SRT Relay."""

import http.server
import json
import subprocess
import os
import sys
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PORT = 9988

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TikTok SRT 推流监控</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', system-ui, sans-serif; background: #0f1117; color: #e0e0e0; padding: 20px; min-height: 100vh; }
  .header { text-align: center; padding: 20px 0; border-bottom: 1px solid #2a2d3a; margin-bottom: 30px; }
  .header h1 { font-size: 22px; font-weight: 600; color: #fff; }
  .header .info { font-size: 13px; color: #666; margin-top: 6px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; max-width: 1100px; margin: 0 auto; }
  .card { background: #1a1d28; border-radius: 10px; padding: 20px; border: 1px solid #2a2d3a; transition: border-color 0.3s; }
  .card:hover { border-color: #444; }
  .card .name { font-size: 18px; font-weight: 700; color: #fff; margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
  .row { display: flex; justify-content: space-between; align-items: center; padding: 6px 0; }
  .row .label { font-size: 13px; color: #888; }
  .badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; letter-spacing: 0.3px; }
  .badge.online { background: #0d3320; color: #4ade80; border: 1px solid #166534; }
  .badge.offline { background: #331010; color: #f87171; border: 1px solid #991b1b; }
  .badge.reading { background: #0d2633; color: #60a5fa; border: 1px solid #1e40af; }
  .url-area { margin-top: 12px; background: #0f1117; border-radius: 6px; padding: 10px; overflow: hidden; }
  .url-area .title { font-size: 11px; color: #666; margin-bottom: 4px; }
  .url-area code { font-size: 11px; color: #999; word-break: break-all; line-height: 1.5; }
  .last-seen { font-size: 11px; color: #555; margin-top: 10px; text-align: right; }
  .footer { text-align: center; padding: 30px 0; font-size: 12px; color: #444; }
  .dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .dot.live { background: #4ade80; box-shadow: 0 0 6px #4ade80; animation: pulse 1.5s infinite; }
  .dot.dead { background: #555; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
</head>
<body>
<div class="header">
  <h1>TikTok SRT 推流监控</h1>
  <div class="info" id="info">加载中...</div>
</div>
<div class="grid" id="grid"></div>
<div class="footer">TikTok SRT Relay Monitor</div>
<script>
const API = '/api/status';
async function refresh() {
  try {
    const r = await fetch(API);
    const data = await r.json();
    document.getElementById('info').textContent =
      `服务器: ${data.host}:${data.port} | 更新时间: ${data.time}`;
    const grid = document.getElementById('grid');
    grid.innerHTML = data.streams.map(s => `
      <div class="card">
        <div class="name">
          <span class="dot ${s.publishing ? 'live' : 'dead'}"></span>
          ${s.name}
        </div>
        <div class="row">
          <span class="label">推流</span>
          <span class="badge ${s.publishing ? 'online' : 'offline'}">${s.publishing ? '在线' : '离线'}</span>
        </div>
        <div class="row">
          <span class="label">拉流</span>
          <span class="badge ${s.readers > 0 ? 'reading' : 'offline'}">${s.readers > 0 ? s.readers + ' 路在线' : '无连接'}</span>
        </div>
        <div class="url-area">
          <div class="title">推流 URL</div>
          <code>srt://${data.host}:${data.port}?streamid=publish:${s.name}&amp;passphrase=***</code>
        </div>
        <div class="url-area">
          <div class="title">拉流 URL</div>
          <code>srt://${data.host}:${data.port}?streamid=read:${s.name}&amp;passphrase=***</code>
        </div>
        <div class="last-seen">${s.last_event || '--'}</div>
      </div>
    `).join('');
  } catch(e) {
    document.getElementById('info').textContent = '连接服务器失败...';
  }
}
refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>"""

def load_env():
    env = {}
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def get_configured_streams():
    """Get stream names from mediamtx.yml"""
    yml = BASE_DIR / "mediamtx.yml"
    if not yml.exists():
        return []
    text = yml.read_text()
    streams = []
    for line in text.splitlines():
        if line.startswith("  ") and not line.startswith("    ") and line.endswith(":"):
            name = line.strip()[:-1]
            if name:
                streams.append(name)
    return streams

def get_stream_status():
    """Parse docker logs to determine active streams."""
    try:
        logs = subprocess.run(
            ["docker", "logs", "--tail=500", "tiktok-srt-relay"],
            capture_output=True, text=True, timeout=10
        ).stdout.strip()
    except Exception:
        logs = ""

    paths = get_configured_streams()
    env = load_env()

    result = []
    for path in paths:
        publishing = False
        readers = 0
        last_event = ""

        pattern = re.escape(path)
        pub_pattern = rf"is publishing to path '{pattern}'"
        read_pattern = rf"is reading from path '{pattern}'"
        close_pattern = rf"closed.*{pattern}"

        for line in logs.splitlines():
            if re.search(pub_pattern, line):
                publishing = True
                last_event = line.split(" INF ")[-1] if " INF " in line else line
            elif re.search(read_pattern, line):
                readers += 1
                last_event = line.split(" INF ")[-1] if " INF " in line else line
            elif re.search(close_pattern, line):
                if "is reading" in " ".join(logs.splitlines()[:logs.splitlines().index(line)]):
                    readers = max(0, readers - 1)
                if "is publishing" in " ".join(logs.splitlines()[:logs.splitlines().index(line)]):
                    publishing = False
                last_event = line.split(" INF ")[-1] if " INF " in line else line

        result.append({
            "name": path,
            "publishing": publishing,
            "readers": readers,
            "last_event": last_event or "--"
        })

    return result

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/status":
            env = load_env()
            try:
                streams = get_stream_status()
                from datetime import datetime
                data = {
                    "host": env.get("PUBLIC_HOST", "--"),
                    "port": env.get("SRT_PORT", "8890"),
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "streams": streams
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML.encode())

    def log_message(self, format, *args):
        pass

def main():
    os.chdir(BASE_DIR)
    env = load_env()
    host = env.get("PUBLIC_HOST", "0.0.0.0")
    print(f"Monitor: http://{host}:{PORT}")
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\nStopped.")

if __name__ == "__main__":
    main()
