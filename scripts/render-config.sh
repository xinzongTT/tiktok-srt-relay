#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo ".env not found. Run scripts/setup.sh first."
  exit 1
fi

set -a
source .env
set +a

for var in PUBLIC_HOST STREAM_PATH SRT_PORT SRT_LATENCY_US SRT_PUBLISH_PASSPHRASE SRT_READ_PASSPHRASE; do
  if [ -z "${!var:-}" ]; then
    echo "Missing env var: $var"
    exit 1
  fi
done

python3 - <<'PY'
import os
from pathlib import Path

required = [
    "STREAM_PATH",
    "SRT_PORT",
    "SRT_PUBLISH_PASSPHRASE",
    "SRT_READ_PASSPHRASE",
]

for key in required:
    value = os.environ.get(key, "")
    if not value:
        raise SystemExit(f"Missing {key}")

for key in ["SRT_PUBLISH_PASSPHRASE", "SRT_READ_PASSPHRASE"]:
    value = os.environ[key]
    if not (20 <= len(value) <= 79):
        raise SystemExit(f"{key} must be 20-79 characters for this project and SRT compatibility")

template = Path("mediamtx.yml.template").read_text(encoding="utf-8")

replacements = {
    "__STREAM_PATH__": os.environ["STREAM_PATH"],
    "__SRT_PORT__": os.environ["SRT_PORT"],
    "__SRT_PUBLISH_PASSPHRASE__": os.environ["SRT_PUBLISH_PASSPHRASE"],
    "__SRT_READ_PASSPHRASE__": os.environ["SRT_READ_PASSPHRASE"],
}

for src, dst in replacements.items():
    template = template.replace(src, dst)

Path("mediamtx.yml").write_text(template, encoding="utf-8")
print("Rendered mediamtx.yml")
PY
