#!/usr/bin/env bash
# Decommission and clean up RELab deployment on Debian.
# Default mode is dry-run. Run with --apply to perform actual removal.
set -Eeuo pipefail

INSTALL_DIR='/opt/RELab'
APPLY=false
PURGE_DATA=false

usage() {
  cat <<'EOF'
Usage: sudo bash scripts/uninstall-debian.sh [options]
  --apply        Execute the uninstallation (default is dry-run)
  --purge-data   Also delete the RELab installation folder and database
  --install-dir  Path to RELab installation (default: /opt/RELab)
  --help         Show this text
EOF
}

while (($#)); do
  case "$1" in
    --apply) APPLY=true; shift ;;
    --purge-data) PURGE_DATA=true; shift ;;
    --install-dir) INSTALL_DIR="${2:?Missing --install-dir}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ $EUID -eq 0 ]] || { echo 'Run with sudo or as root.' >&2; exit 1; }

printf '=== RELab Decommission & Teardown ===\n'
printf 'Target installation directory: %s\n' "$INSTALL_DIR"
printf 'Mode: %s\n\n' "$([[ $APPLY == true ]] && echo 'LIVE APPLY' || echo 'DRY RUN (no changes made)')"

actions=(
  "Stop and remove all running RELab Docker containers"
  "Stop, disable, and remove relab-code-server.service systemd unit"
  "Remove /etc/sudoers.d/re"
  "Restore systemd-resolved port 53 stub listener configuration"
)
if [[ $PURGE_DATA == true ]]; then
  actions+=("Purge installation directory: $INSTALL_DIR (including captures & databases)")
fi

printf 'Planned teardown actions:\n'
for a in "${actions[@]}"; do
  printf '  - %s\n' "$a"
done

if [[ $APPLY == false ]]; then
  printf '\nDry run complete. To execute these changes, re-run with:\n'
  printf '  sudo bash %s --apply%s\n' "$0" "$([[ $PURGE_DATA == true ]] && echo ' --purge-data' || echo '')"
  exit 0
fi

printf '\nExecuting uninstallation...\n'

# 1. Stop Docker containers
if [[ -f "$INSTALL_DIR/compose.yaml" ]] && command -v docker >/dev/null 2>&1; then
  echo '[1/4] Stopping Docker containers...'
  docker compose -f "$INSTALL_DIR/compose.yaml" down 2>/dev/null || true
else
  echo '[1/4] No active Docker Compose deployment found.'
fi

# 2. Remove code-server service
echo '[2/4] Removing relab-code-server systemd unit...'
if systemctl is-active --quiet relab-code-server.service 2>/dev/null; then
  systemctl stop relab-code-server.service 2>/dev/null || true
fi
systemctl disable relab-code-server.service 2>/dev/null || true
rm -f /etc/systemd/system/relab-code-server.service
systemctl daemon-reload 2>/dev/null || true

# 3. Clean up sudoers and systemd-resolved port 53 stub
echo '[3/4] Cleaning system configurations...'
rm -f /etc/sudoers.d/re
if [[ -f /etc/systemd/resolved.conf.d/relab-stub.conf ]]; then
  rm -f /etc/systemd/resolved.conf.d/relab-stub.conf
  if systemctl is-active --quiet systemd-resolved 2>/dev/null; then
    systemctl restart systemd-resolved 2>/dev/null || true
  fi
  echo 'Restored systemd-resolved configuration.'
fi

# 4. Purge data directory if requested
if [[ $PURGE_DATA == true && -d "$INSTALL_DIR" ]]; then
  echo "[4/4] Purging installation directory: $INSTALL_DIR..."
  rm -rf "$INSTALL_DIR"
else
  echo '[4/4] Retaining workspace files and captures in '"$INSTALL_DIR"'.'
fi

printf '\nRELab decommission finished successfully.\n'

