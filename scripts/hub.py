#!/usr/bin/env python3
"""Central hub: receive status from VPS reporters, serve dashboard."""

import http.server
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
PORT = 9988

# In-memory store: { server_name: { host, port, streams, last_seen, status_data } }
SERVERS = {}

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TikTok SRT 多服务器监控</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#0b0d14;color:#e0e0e0;padding:20px;min-height:100vh}
  .topbar{display:flex;justify-content:space-between;align-items:center;padding:14px 0;border-bottom:1px solid #1e2230;margin-bottom:20px;position:sticky;top:0;background:#0b0d14;z-index:10}
  .topbar h1{font-size:20px;color:#fff}
  .topbar .meta{display:flex;gap:20px;font-size:13px;color:#555;align-items:center}
  .hb{display:flex;align-items:center;gap:6px}
  .hb .dot{width:6px;height:6px;border-radius:50%}
  .dot.green{background:#4ade80;box-shadow:0 0 6px #4ade80;animation:pulse 1.5s infinite}
  .dot.yellow{background:#f59e0b}
  .dot.red{background:#f87171}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  .server-block{margin-bottom:24px}
  .server-header{display:flex;align-items:center;gap:10px;padding:8px 0}
  .server-header h2{font-size:15px;color:#aaa}
  .server-header .sd{width:10px;height:10px;border-radius:50%}
  .server-header .sd.ok{background:#4ade80}.server-header .sd.err{background:#f87171}
  .server-header .urls{font-size:11px;color:#555;margin-left:auto}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:12px}
  .card{background:#131620;border-radius:8px;padding:16px;border:1px solid #1e2230}
  .card .name{font-size:15px;font-weight:700;color:#fff;margin-bottom:10px;display:flex;align-items:center;gap:8px}
  .card .name .dot{width:8px;height:8px;border-radius:50%;display:inline-block}
  .card .name .dot.live{background:#4ade80;box-shadow:0 0 6px #4ade80;animation:pulse 1.5s infinite}
  .card .name .dot.dead{background:#444}
  .row{display:flex;justify-content:space-between;align-items:center;padding:4px 0}
  .row .lbl{font-size:12px;color:#666}
  .badge{padding:3px 10px;border-radius:16px;font-size:11px;font-weight:600}
  .badge.online{background:#0d3320;color:#4ade80;border:1px solid #166534}
  .badge.offline{background:#251010;color:#f87171;border:1px solid #7f1d1d}
  .badge.reading{background:#0d2633;color:#60a5fa;border:1px solid #1e40af}
  .url-area{margin-top:8px;background:#0b0d14;border-radius:4px;padding:8px}
  .url-area .t{font-size:10px;color:#555;margin-bottom:2px}
  .url-area code{font-size:10px;color:#777;word-break:break-all}
  .last-seen{font-size:10px;color:#444;margin-top:8px;text-align:right}
  .footer{text-align:center;padding:30px 0;font-size:11px;color:#333}
  @media(max-width:700px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="topbar">
  <h1>TikTok SRT 多服务器监控</h1>
  <div class="meta">
    <span id="total-streams">--</span>
    <span id="online-count">--</span>
    <span class="hb"><span class="dot green" id="global-hb"></span><span id="update-time">--</span></span>
  </div>
</div>
<div id="servers"></div>
<div class="footer">TikTok SRT Relay Monitor</div>
<script>
setInterval(async()=>{
  try{
    const r=await fetch('/api/status');
    const data=await r.json();
    const servers=data.servers||{};
    let total=0,active=0;
    let allOk=true,anyOk=false;
    let html='';

    for(const[name,svr]of Object.entries(servers)){
      const alive=(Date.now()/1000-svr.last_seen)<20;
      if(alive)anyOk=true;else allOk=false;
      html+=`<div class="server-block">`;
      html+=`<div class="server-header">`;
      html+=`<span class="sd ${alive?'ok':'err'}"></span>`;
      html+=`<h2>${name}</h2>`;
      html+=`<span class="urls">${svr.host}:${svr.port} | ${alive?'在线':'超时'}</span>`;
      html+=`</div>`;
      if(alive&&svr.streams&&svr.streams.length){
        total+=svr.streams.length;
        html+=`<div class="grid">`;
        svr.streams.forEach(st=>{
          if(st.publishing||st.readers>0)active++;
          html+=`<div class="card">
            <div class="name"><span class="dot ${st.publishing?'live':'dead'}"></span>${st.name}</div>
            <div class="row"><span class="lbl">推流</span><span class="badge ${st.publishing?'online':'offline'}">${st.publishing?'在线':'离线'}</span></div>
            <div class="row"><span class="lbl">拉流</span><span class="badge ${st.readers>0?'reading':'offline'}">${st.readers>0?st.readers+' 路':'无连接'}</span></div>
            <div class="url-area"><div class="t">推流</div><code>srt://${svr.host}:${svr.port}?streamid=publish:${st.name}&amp;passphrase=***</code></div>
            <div class="url-area"><div class="t">拉流</div><code>srt://${svr.host}:${svr.port}?streamid=read:${st.name}&amp;passphrase=***</code></div>
            <div class="last-seen">${st.last_event||'--'}</div>
          </div>`;
        });
        html+=`</div>`;
      }else if(alive){
        html+=`<div style="color:#444;font-size:13px;padding:8px;">暂无推流</div>`;
      }else{
        html+=`<div style="color:#f87171;font-size:13px;padding:8px;">上报超时</div>`;
      }
      html+=`</div>`;
    }

    document.getElementById('servers').innerHTML=html||'<p style="color:#555;text-align:center;padding:40px;">等待 VPS 上报...</p>';
    document.getElementById('total-streams').textContent=`${total} 路推流`;
    document.getElementById('online-count').textContent=`${active} 活跃`;
    document.getElementById('update-time').textContent=new Date().toLocaleTimeString();
    const hb=document.getElementById('global-hb');
    hb.className='dot '+(allOk&&anyOk?'green':anyOk?'yellow':'red');
  }catch(e){}
},3000);
</script>
</body>
</html>"""

class HubHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/api/status":
            self._json({ "servers": SERVERS, "time": datetime.now().strftime("%H:%M:%S") })
        else:
            self._html(HTML)

    def do_POST(self):
        if self.path == "/api/report":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                report = json.loads(body)
                name = report.get("name", "unknown")
                SERVERS[name] = {
                    "host": report.get("host", "?"),
                    "port": report.get("port", "8890"),
                    "streams": report.get("streams", []),
                    "last_seen": time.time(),
                }
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"ok")
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode())

    def _html(self, content):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(content.encode())

    def log_message(self, format, *args):
        pass

def main():
    print(f"Hub started: http://0.0.0.0:{PORT}")
    server = http.server.HTTPServer(("0.0.0.0", PORT), HubHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

if __name__ == "__main__":
    main()
