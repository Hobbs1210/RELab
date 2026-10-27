#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Standalone batch process of completed PCAPs with Zeek and tshark.
docker compose run --rm --no-deps analyzer python3 /opt/lab/analyze.py once
