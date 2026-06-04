# Relay Monitor Integration Design

## Goal

Fix multi-stream additions so new MediaMTX paths authenticate correctly, and make each relay server report status to the central monitor without changing the SRT streaming path.

## Design

- Keep SRT publishing and reading behavior unchanged: same UDP port, SRT path names, passphrase model, latency settings, and `maxReaders`.
- When `scripts/manage.py` adds or deletes a stream path, keep `authInternalUsers[any].permissions` in sync with the `paths:` section.
- Enable the MediaMTX API on loopback only so local reporter code can poll `/v3/paths/list` without exposing the API publicly.
- Add a Python reporter in the relay repo that matches the monitor hub contract: POST `name`, `host`, `port`, and `streams[]` to `/api/report`.
- Add a start script that reads `.env`, builds reporter environment variables, and launches the reporter.

## Verification

- Unit-style tests cover YAML permission synchronization and reporter payload mapping.
- Rendered config must include API loopback settings and monitor credentials.
- Existing test publish/read URL construction remains unchanged.
