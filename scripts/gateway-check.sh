#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .env
printf 'Selected profile: %s\n' "${TARGET_PROFILE:-generic}"
python3 scripts/device-profile.py show "${TARGET_PROFILE:-generic}"
printf '\nDNS smoke test (.test name, not a vendor hostname):\n'
dig +time=2 +tries=1 @127.0.0.1 device.example.test || true
printf '\nLab nft table (if running on gateway):\n'
sudo nft list table ip device_re_lab_nat || true
printf '\nCaptures:\n'
find data/pcaps -maxdepth 1 -name '*.pcap' -printf '%TY-%Tm-%Td %TH:%TM %s %f\n' | tail -8
printf '\nDocker services:\n'
docker compose ps
