#!/usr/bin/env python3
"""Poll MediaMTX API and report relay status to the central monitor hub."""

import base64
import json
import os
import socket
import time
import urllib.request


DEFAULT_HUB = "http://23.238.118.221:9988/api/report"
DEFAULT_MTX_API = "http://127.0.0.1:9997/v3/paths/list"


def fetch_json(url, auth=None, timeout=5):
    headers = {}
    if auth:
        token = base64.b64encode(auth.encode()).decode()
        headers["Authorization"] = "Basic " + token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def post_json(url, payload, token="", timeout=5):
    data = json.dumps(payload, ensure_ascii=False).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Report-Token"] = token
    req = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()


def build_streams(api_payload, last_readers, reconnects, last_frames_error):
    streams = []
    for item in api_payload.get("items", []):
        name = item.get("name", "")
        if not name:
            continue
        source = item.get("source") or {}
        source_type = source.get("type", "")
        readers = len(item.get("readers") or [])
        publishing = source_type == "srtConn"
        frames_total = int(item.get("inboundFramesInError") or 0)

        previous_readers = last_readers.get(name, 0)
        if previous_readers > 0 and readers == 0:
            reconnects[name] = reconnects.get(name, 0) + 1
        last_readers[name] = readers

        previous_frames = last_frames_error.get(name, 0)
        frames_delta = frames_total - previous_frames if frames_total > previous_frames else 0
        last_frames_error[name] = frames_total

        if publishing:
            last_event = "publishing"
        elif readers > 0:
            last_event = "reading"
        else:
            last_event = "idle"

        streams.append(
            {
                "name": name,
                "publishing": publishing,
                "readers": readers,
                "frames_error": frames_delta,
                "reconnects": reconnects.get(name, 0),
                "last_event": last_event,
            }
        )
    return streams


def build_report(api_payload, name, host, port, state):
    return {
        "name": name,
        "host": host,
        "port": port,
        "streams": build_streams(
            api_payload,
            state["last_readers"],
            state["reconnects"],
            state["last_frames_error"],
        ),
        "time": int(time.time()),
    }


def main():
    hub = os.environ.get("HUB", DEFAULT_HUB)
    mtx_api = os.environ.get("MTX_API", DEFAULT_MTX_API)
    mtx_auth = os.environ.get("MTX_AUTH", "admin:monitor")
    name = os.environ.get("NAME", socket.gethostname())
    host = os.environ.get("SRT_HOST", os.environ.get("PUBLIC_HOST", "?"))
    port = os.environ.get("SRT_PORT", "8890")
    report_token = os.environ.get("REPORT_TOKEN", "")
    interval = int(os.environ.get("REPORT_INTERVAL", "5"))
    state = {"last_readers": {}, "reconnects": {}, "last_frames_error": {}}

    print(f"[reporter] hub={hub} api={mtx_api} name={name} srt={host}:{port}", flush=True)
    while True:
        try:
            api_payload = fetch_json(mtx_api, auth=mtx_auth)
        except Exception as exc:
            print(f"[reporter] MediaMTX API error: {exc}", flush=True)
            api_payload = {"items": []}

        report = build_report(api_payload, name, host, port, state)
        try:
            post_json(hub, report, token=report_token)
        except Exception as exc:
            print(f"[reporter] Hub post error: {exc}", flush=True)

        time.sleep(interval)


if __name__ == "__main__":
    main()
