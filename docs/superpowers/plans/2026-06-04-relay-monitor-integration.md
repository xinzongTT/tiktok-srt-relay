# Relay Monitor Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix added stream authentication and add monitor hub reporting support.

**Architecture:** `manage.py` owns local MediaMTX YAML edits and must synchronize path permissions atomically. MediaMTX API stays local-only, and `scripts/reporter.py` polls it and POSTs monitor-compatible JSON to the hub.

**Tech Stack:** Python 3 standard library, Bash, MediaMTX YAML text rendering, Docker Compose.

---

### Task 1: Regression Tests

**Files:**
- Create: `tests/test_manage_config.py`
- Create: `tests/test_reporter.py`

- [ ] Add tests that prove adding a stream also adds `publish/read` permissions.
- [ ] Add tests that prove deleting a stream removes its permissions.
- [ ] Add tests that prove reporter maps MediaMTX API path items into hub stream objects.

### Task 2: Manage Config Fix

**Files:**
- Modify: `scripts/manage.py`

- [ ] Add helper functions for permission insertion/removal in the `authInternalUsers` section.
- [ ] Call helpers from `add_stream` and `delete_stream`.
- [ ] Keep existing URL output and path defaults unchanged.

### Task 3: Monitor API Defaults

**Files:**
- Modify: `mediamtx.yml.template`
- Modify: `scripts/render-config.sh`
- Modify: `.env.example`

- [ ] Enable `api: true`.
- [ ] Bind API to `127.0.0.1:9997`.
- [ ] Add `admin:monitor` API permission user.
- [ ] Add reporter environment defaults.

### Task 4: Reporter

**Files:**
- Create: `scripts/reporter.py`
- Create: `scripts/reporter-start.sh`

- [ ] Add Python reporter compatible with `E:\tiktok-srt-monitor\hub.py`.
- [ ] Add a start script that reads `.env` and launches reporter with sane defaults.

### Task 5: Docs and Verification

**Files:**
- Modify: `README.md`

- [ ] Document `tkm` add stream behavior and monitor reporter startup.
- [ ] Run `python -m unittest discover tests -v`.
- [ ] Run `python -m py_compile scripts/manage.py scripts/reporter.py`.
- [ ] Run `bash scripts/render-config.sh` and inspect generated API/auth sections.
