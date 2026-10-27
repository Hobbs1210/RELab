#!/usr/bin/env bash
# Install a loopback-bound code-server instance that ALWAYS opens the RELab Git checkout.
# This is NOT desktop VS Code; desktop VS Code connects from your laptop using Remote-SSH.
set -Eeuo pipefail
umask 077
TARGET_USER=''
WORKSPACE='/opt/RELab'
PORT=8443
usage() { echo 'Usage: sudo bash scripts/install-code-server.sh --user USER [--workspace /opt/RELab] [--port 8443]'; }
while (($#)); do
  case "$1" in
    --user) TARGET_USER="${2:?}"; shift 2 ;;
    --workspace) WORKSPACE="${2:?}"; shift 2 ;;
    --port) PORT="${2:?}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ $EUID -eq 0 ]] || { echo 'Root privileges required' >&2; exit 1; }
[[ -n $TARGET_USER && $TARGET_USER != root ]] || { echo '--user is required' >&2; exit 1; }
[[ -f $WORKSPACE/compose.yaml ]] || { echo "Not a RELab workspace: $WORKSPACE" >&2; exit 1; }
[[ $PORT =~ ^[0-9]+$ ]] && ((10#$PORT >= 1024 && 10#$PORT <= 65535)) || { echo 'Use an unprivileged TCP port' >&2; exit 1; }
[[ $WORKSPACE == /* && $WORKSPACE != *[[:space:]]* ]] || { echo 'Workspace must be an absolute path without whitespace' >&2; exit 1; }
[[ $TARGET_USER =~ ^[a-z_][a-z0-9_-]*[$]?$ ]] || { echo 'Unsupported username syntax for systemd unit' >&2; exit 1; }
account_entry=$(getent passwd "$TARGET_USER")
[[ -n $account_entry ]] || { echo 'Unknown user' >&2; exit 1; }
HOME_DIR=$(printf '%s' "$account_entry" | cut -d: -f6)
[[ -d $HOME_DIR && $HOME_DIR == /* && $HOME_DIR != *[[:space:]]* ]] || { echo 'Unsupported or missing user home directory' >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get install -y ca-certificates curl
if ! command -v code-server >/dev/null 2>&1; then
  tmp=$(mktemp -d)
  trap 'rm -rf "$tmp"' EXIT
  curl -fsSL --retry 3 https://code-server.dev/install.sh -o "$tmp/install-code-server.sh"
  # The vendor installation script is downloaded to disk (not piped directly to a shell).
  sh "$tmp/install-code-server.sh" --method=detect
fi
binary=$(command -v code-server)
[[ $binary == /* ]] || { echo 'code-server executable not found' >&2; exit 1; }

config_dir="$HOME_DIR/.config/relab-code-server"
config_file="$config_dir/config.yaml"
install -d -m 0700 -o "$TARGET_USER" -g "$(id -gn "$TARGET_USER")" "$config_dir"
if [[ ! -f $config_file ]]; then
  pass=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
  cat > "$config_file" <<CONF
bind-addr: 127.0.0.1:$PORT
auth: password
password: $pass
cert: false
CONF
fi
chown "$TARGET_USER:$(id -gn "$TARGET_USER")" "$config_file"
chmod 600 "$config_file"

# A dedicated unit prevents unrelated user code-server sessions from opening other folders.
cat > /etc/systemd/system/relab-code-server.service <<UNIT
[Unit]
Description=RELab browser editor (code-server)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$TARGET_USER
WorkingDirectory=$WORKSPACE
Environment=HOME=$HOME_DIR
ExecStart=$binary --config $config_file --bind-addr 127.0.0.1:$PORT --auth password $WORKSPACE
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now relab-code-server.service
systemctl is-active --quiet relab-code-server.service || { journalctl -u relab-code-server.service --no-pager -n 80; exit 1; }
printf '\nBrowser editor installed: http://127.0.0.1:%s (accessible through SSH port forwarding)\n' "$PORT"
printf 'Opening folder: %s\n' "$WORKSPACE"
printf 'Password: sudo cat %s (show only on trusted SSH terminal)\n' "$config_file"
