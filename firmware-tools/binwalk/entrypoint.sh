#!/bin/sh
set -eu
case "${1:-}" in
  ''|*/*|*'..'*) echo 'Usage: docker compose --profile firmware run --rm binwalk FIRMWARE_BASENAME [--extract]' >&2;exit 2;;
esac
name="$1";shift
test -f "/firmware/$name" || { echo "Firmware not present: $name" >&2;exit 2; }
mkdir -p /extracted/session
# Input copied into writable extraction directory; the originals remain read-only.
cp "/firmware/$name" /extracted/session/input.bin
cd /extracted/session
case "${1:-}" in
  --extract) exec binwalk -Me input.bin ;;
  '') exec binwalk input.bin ;;
  *) echo 'Only --extract optional flag is supported' >&2;exit 2;;
esac
