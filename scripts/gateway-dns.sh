#!/usr/bin/env bash
# Optional nftables redirect for ONE device on an isolated Linux lab gateway.
set -euo pipefail
ACTION="${1:-}"; TARGET="${2:-}"; LAB="${3:-}"; TABLE=device_re_lab_nat
if [[ "$ACTION" == remove ]]; then
  echo "Removing only lab-owned nft table ip $TABLE"
  if [[ "${2:-}" == --apply ]]; then sudo nft delete table ip "$TABLE"; fi
  exit 0
fi
if [[ "$ACTION" != plan && "$ACTION" != apply ]]; then
  echo 'Usage: gateway-dns.sh plan|apply TARGET_IPV4 LAB_IPV4 | remove --apply';exit 2
fi
python3 - "$TARGET" "$LAB" <<'PY'
import ipaddress,sys
try:
 target=ipaddress.IPv4Address(sys.argv[1]);lab=ipaddress.IPv4Address(sys.argv[2]);assert target.is_private and lab.is_private and target != lab
except Exception:raise SystemExit('Both addresses must be distinct private IPv4 addresses')
PY
RULES="table ip $TABLE {
 chain prerouting { type nat hook prerouting priority dstnat; policy accept;
 ip saddr $TARGET udp dport 53 dnat to $LAB:53
 ip saddr $TARGET tcp dport 53 dnat to $LAB:53
 }
}"
printf '%s\n' "$RULES"
if [[ "$ACTION" == apply ]]; then
  printf 'Applying ONE-device port-53 redirect; undo: gateway-dns.sh remove --apply\n'
  printf '%s\n' "$RULES" | sudo nft -f -
fi
