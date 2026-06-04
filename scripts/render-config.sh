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

REQUIRED_VARS=(PUBLIC_HOST STREAM_PATH SRT_PORT SRT_PUBLISH_LATENCY SRT_READ_LATENCY SRT_PUBLISH_PASSPHRASE SRT_READ_PASSPHRASE MUSIC_PATH MUSIC_PUBLISH_PASSPHRASE MUSIC_READ_PASSPHRASE)
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var:-}" ]; then
    echo "Missing env var: $var"
    exit 1
  fi
done

PYTHON_BIN=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" --version >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "Python 3 not found."
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import os, sys
from pathlib import Path
import shutil

template_file = Path("mediamtx.yml.template")
output_file = Path("mediamtx.yml")

if not template_file.exists():
    sys.exit("Template mediamtx.yml.template not found.")

for key in ["SRT_PUBLISH_PASSPHRASE", "SRT_READ_PASSPHRASE", "MUSIC_PUBLISH_PASSPHRASE", "MUSIC_READ_PASSPHRASE"]:
    value = os.environ[key]
    if not (20 <= len(value) <= 79):
        sys.exit(f"{key} must be 20-79 characters for SRT compatibility")

if output_file.exists():
    shutil.copy2(output_file, "mediamtx.yml.bak")

template = template_file.read_text(encoding="utf-8")

replacements = {
    "__STREAM_PATH__": os.environ["STREAM_PATH"],
    "__SRT_PORT__": os.environ["SRT_PORT"],
    "__SRT_PUBLISH_PASSPHRASE__": os.environ["SRT_PUBLISH_PASSPHRASE"],
    "__SRT_READ_PASSPHRASE__": os.environ["SRT_READ_PASSPHRASE"],
    "__MUSIC_PATH__": os.environ["MUSIC_PATH"],
    "__MUSIC_PUBLISH_PASSPHRASE__": os.environ["MUSIC_PUBLISH_PASSPHRASE"],
    "__MUSIC_READ_PASSPHRASE__": os.environ["MUSIC_READ_PASSPHRASE"],
}

for src, dst in replacements.items():
    template = template.replace(src, dst)

output_file.write_text(template, encoding="utf-8")
print("Rendered mediamtx.yml")
PY
