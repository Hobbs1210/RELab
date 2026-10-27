#!/usr/bin/env bash
# Live Wireshark streaming pipe for RELab traffic inspection.
# Pipes live packets from local or remote Debian interface directly into desktop Wireshark.
set -euo pipefail

HOST=""
IFACE="any"
FILTER="not port 22 and not port 8443"
OUT_FILE=""
USE_TSHARK=false

usage() {
  cat <<'EOF'
Usage: bash scripts/stream-pcap.sh [options]
  --host USER@IP    Stream from remote RELab host via SSH (e.g. re@192.168.50.20)
  --interface IFACE Network interface to capture (default: any)
  --filter "EXPR"   BPF capture filter (default: "not port 22 and not port 8443")
  --out FILE.pcap   Save a copy of the stream to a local PCAP file
  --tshark          Use terminal tshark instead of Wireshark GUI
  -h, --help        Show this text

Examples:
  # Stream live packets from remote Debian lab into local Wireshark:
  bash scripts/stream-pcap.sh --host re@192.168.50.20

  # Stream specific IoT target traffic and save to data/pcaps:
  bash scripts/stream-pcap.sh --host re@192.168.50.20 --filter "host 192.0.2.10" --out data/pcaps/live.pcap
EOF
}

while (($#)); do
  case "$1" in
    --host) HOST="${2:?Missing --host}"; shift 2 ;;
    --interface) IFACE="${2:?Missing --interface}"; shift 2 ;;
    --filter) FILTER="${2:?Missing --filter}"; shift 2 ;;
    --out) OUT_FILE="${2:?Missing --out}"; shift 2 ;;
    --tshark) USE_TSHARK=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

VIEWER="wireshark"
if [[ $USE_TSHARK == true ]]; then
  VIEWER="tshark"
fi

if ! command -v "$VIEWER" >/dev/null 2>&1; then
  echo "Error: $VIEWER is not installed or not in PATH." >&2
  exit 1
fi

printf "=== RELab Live Capture Stream ===\n"
printf "Capture interface : %s\n" "$IFACE"
printf "BPF filter        : %s\n" "$FILTER"
printf "Viewer            : %s\n" "$VIEWER"
if [[ -n "$HOST" ]]; then
  printf "Source host       : %s (via SSH)\n" "$HOST"
else
  printf "Source host       : localhost (sudo tcpdump)\n"
fi
if [[ -n "$OUT_FILE" ]]; then
  printf "Output copy       : %s\n" "$OUT_FILE"
  mkdir -p "$(dirname "$OUT_FILE")"
fi
printf "=================================\n\n"

CAPTURE_CMD="sudo tcpdump -i '$IFACE' -U -s 0 -w - '$FILTER' 2>/dev/null"

if [[ -n "$HOST" ]]; then
  STREAM_SRC="ssh -C \"$HOST\" \"$CAPTURE_CMD\""
else
  STREAM_SRC="$CAPTURE_CMD"
fi

if [[ -n "$OUT_FILE" ]]; then
  if [[ "$VIEWER" == "wireshark" ]]; then
    eval "$STREAM_SRC" | tee "$OUT_FILE" | wireshark -k -i -
  else
    eval "$STREAM_SRC" | tee "$OUT_FILE" | tshark -r -
  fi
else
  if [[ "$VIEWER" == "wireshark" ]]; then
    eval "$STREAM_SRC" | wireshark -k -i -
  else
    eval "$STREAM_SRC" | tshark -r -
  fi
fi
