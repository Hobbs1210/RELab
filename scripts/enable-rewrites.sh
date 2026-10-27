#!/usr/bin/env bash
# Rewrites only the hosts listed in an explicitly selected device profile.
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/dns-rewrite.py enable "${1:?Usage: enable-rewrites.sh LAB_IP [PROFILE]}" "${2:-$(sed -n 's/^TARGET_PROFILE=//p' .env | head -1)}"
