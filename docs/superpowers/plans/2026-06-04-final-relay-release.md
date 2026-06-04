# Final Relay Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the relay repository as the final VPS SRT relay package with monitor hub code split out.

**Architecture:** This repository owns MediaMTX configuration, SRT stream management, and a lightweight reporter that posts status to the separate monitor hub. Hub pages, standalone monitor UI, and old log-parsing monitor scripts are removed from this repository.

**Tech Stack:** Bash, Python 3 standard library, MediaMTX, Docker Compose, unittest.

---

### Task 1: Repository Boundary

**Files:**
- Delete: `monitor-all.html`
- Delete: `scripts/hub.py`
- Delete: `scripts/monitor.py`
- Delete: `scripts/monitor-start.sh`
- Delete: `scripts/reporter.sh`
- Modify: `README.md`

- [ ] Remove old hub and standalone monitor artifacts from the relay package.
- [ ] Keep `scripts/reporter.py` and `scripts/reporter-start.sh` as the only monitor integration.

### Task 2: Manage Menu

**Files:**
- Modify: `scripts/manage.py`
- Modify: `tests/test_manage_config.py`

- [ ] Replace old Web monitor menu handling with reporter start/stop/status handling.
- [ ] Test that `manage.py` no longer references deleted monitor files.

### Task 3: Release Metadata

**Files:**
- Create: `VERSION`
- Modify: `README.md`

- [ ] Set version to `1.0.0`.
- [ ] Document that the monitor hub lives in `tiktok-srt-monitor`.

### Task 4: Verification

**Files:**
- Test: `tests/test_manage_config.py`
- Test: `tests/test_reporter.py`

- [ ] Run unit tests.
- [ ] Run Python compile checks.
- [ ] Run render-config smoke check.
- [ ] Commit and push final release.
