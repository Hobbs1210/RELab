#!/usr/bin/env bash
# Optional, local authorized Android test device: never enables ADB over TCP.
set -Eeuo pipefail
umask 077
[[ $# -eq 1 ]] || { echo 'Usage: collect-logcat.sh DEVICE_SERIAL (must appear in adb devices)' >&2; exit 2; }
command -v adb >/dev/null || { echo 'Install Android platform-tools on your authorized workstation' >&2; exit 1; }
serial="$1"
[[ "$serial" =~ ^[a-zA-Z0-9._:-]{1,100}$ ]] || { echo 'Invalid ADB serial' >&2; exit 2; }
adb devices -l | grep -Fq "$serial " || { echo 'Device not authorized/connected in adb devices -l' >&2; exit 1; }
cd "$(dirname "$0")/../.."
mkdir -p data/mobile
file="data/mobile/logcat-$(date -u +%Y%m%dT%H%M%SZ)-${serial//:/_}.log"
adb -s "$serial" logcat -d -v epoch > "$file"
echo "Saved private Android logcat to $file. Review/redact before publishing."
echo "Then: python3 scripts/researchctl.py import mobile-log $(basename "$file")"
