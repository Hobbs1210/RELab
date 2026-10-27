#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/dns-rewrite.py disable "${1:-$(sed -n 's/^TARGET_PROFILE=//p' .env | head -1)}"
