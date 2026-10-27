#!/usr/bin/env bash
# Deploy Device RE Lab onto a headless Debian 12/13 host using Docker's official apt repo.
# Usage: sudo bash scripts/install-debian.sh --user USER [--lab-ip 192.168.x.x]
set -Eeuo pipefail
umask 027
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUDO_USER:-}"
INSTALL_DIR=/opt/RELab
LAB_IP=127.0.0.1
GRANT_DOCKER=false
SKIP_START=false
SKIP_DOCKER=false
SKIP_CODE_SERVER=false
usage() {
  cat <<'EOF'
Usage: sudo bash scripts/install-debian.sh --user USER [options]
  --user USER             Existing non-root SSH developer account (required)
  --install-dir PATH      Destination, default /opt/RELab
  --lab-ip IPv4           IPv4 assigned to an isolated lab interface; default 127.0.0.1
  --grant-docker-access   Add developer to the root-equivalent docker group (explicit opt-in)
  --skip-docker-install   Require Docker Engine and Compose already installed
  --skip-code-server      Do not install browser-based VS Code (installed by default)
  --no-start              Install and validate, but do not launch containers
  --help                  Show this text
The installer does NOT configure an internet-facing firewall, SSH passwords, or router rules.
EOF
}
while (($#)); do
  case "$1" in
    --user) TARGET_USER="${2:?Missing --user}"; shift 2 ;;
    --install-dir) INSTALL_DIR="${2:?Missing --install-dir}"; shift 2 ;;
    --lab-ip) LAB_IP="${2:?Missing --lab-ip}"; shift 2 ;;
    --grant-docker-access) GRANT_DOCKER=true; shift ;;
    --skip-docker-install) SKIP_DOCKER=true; shift ;;
    --skip-code-server) SKIP_CODE_SERVER=true; shift ;;
    --no-start) SKIP_START=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unrecognized option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ $EUID == 0 ]] || { echo 'Run with sudo/root' >&2; exit 1; }
[[ -r /etc/os-release ]] || { echo 'Cannot identify operating system' >&2; exit 1; }
# shellcheck source=/dev/null
. /etc/os-release
[[ ${ID:-} == debian && ${VERSION_ID%%.*} =~ ^(12|13)$ ]] || { echo 'Only Debian 12/13 are supported' >&2; exit 1; }
[[ -n $TARGET_USER && $TARGET_USER != root ]] || { echo 'Specify --user EXISTING_NON_ROOT_ACCOUNT' >&2; exit 1; }
id "$TARGET_USER" >/dev/null 2>&1 || { echo "User $TARGET_USER not found" >&2; exit 1; }
[[ $INSTALL_DIR == /* && $INSTALL_DIR != / && $INSTALL_DIR != /opt ]] || { echo 'Install directory must be an absolute dedicated folder' >&2; exit 1; }
if [[ $LAB_IP != 127.0.0.1 ]]; then
  command -v python3 >/dev/null 2>&1 || { apt-get update; apt-get install -y python3; }
  # Require a private local IP, assigned to an interface, never an arbitrary external bind.
  python3 - "$LAB_IP" <<'PY'
import ipaddress,sys
try:
 p=ipaddress.IPv4Address(sys.argv[1]);assert p.is_private and not p.is_loopback and not p.is_link_local
except (ValueError,AssertionError):sys.exit('Use a private IPv4 address from a dedicated lab interface')
PY
  command -v ip >/dev/null 2>&1 || { apt-get update; apt-get install -y iproute2; }
  ip -4 -o addr show | grep -Fq "inet $LAB_IP/" || { echo "IP $LAB_IP is not assigned to a local interface" >&2; exit 1; }
fi
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl gnupg openssh-server python3 python3-venv git rsync iproute2
if [[ $SKIP_DOCKER == false ]] && ! { command -v docker >/dev/null && docker compose version >/dev/null 2>&1; }; then
  # Official Debian Docker repository, no curl|sh installer.
  install -m 0755 -d /etc/apt/keyrings
  curl --fail --silent --show-error --location https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: ${VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
  apt-get update
  if dpkg-query -W -f='${Status}' docker.io 2>/dev/null | grep -q 'install ok installed'; then
    echo 'Existing Debian docker.io package detected. Remove conflicting packages intentionally before installing official Docker.' >&2
    exit 1
  fi
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
command -v docker >/dev/null && docker compose version >/dev/null || { echo 'Docker Engine + Compose v2 required' >&2; exit 1; }
systemctl enable --now docker
systemctl enable --now ssh
sshd -t
if [[ $GRANT_DOCKER == true ]]; then
  usermod -aG docker "$TARGET_USER"
  echo 'WARNING: Docker group is effectively root-equivalent. Only trusted developers should have this permission.'
fi
OWNER_UID=$(id -u "$TARGET_USER")
OWNER_GID=$(id -g "$TARGET_USER")
if [[ "$(realpath -m "$SRC")" != "$(realpath -m "$INSTALL_DIR")" ]]; then
  mkdir -p "$INSTALL_DIR"
  # Keep every existing experiment configuration on repeat installation.
  runtime_excludes=()
  for config_file in rules.json scenarios.json owned-dns.json; do
    [[ ! -f "$INSTALL_DIR/config/$config_file" ]] || runtime_excludes+=("--exclude=config/$config_file")
  done
  rsync -a --exclude='.git/' --exclude='.env' --exclude='data/' --exclude='certs/' \
    --exclude='firmware/' --exclude='research/' \
    --exclude='config/adguard/conf/' --exclude='config/adguard/work/' \
    --exclude='.venv/' --exclude='__pycache__/' --exclude='.pytest_cache/' \
    "${runtime_excludes[@]}" "$SRC/" "$INSTALL_DIR/"
fi
chown -R "$OWNER_UID:$OWNER_GID" "$INSTALL_DIR"
cd "$INSTALL_DIR"
if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
fi
python3 - "$LAB_IP" <<'PY'
from pathlib import Path
import sys
p=Path('.env')
content=p.read_text()
for key,value in [('LAB_IP',sys.argv[1]),('DNS_BIND_IP',sys.argv[1]),('HTTPS_BIND_IP',sys.argv[1])]:
 lines=content.splitlines();matched=False
 for n,line in enumerate(lines):
  if line.startswith(key+'='):
   # Don't overwrite existing explicit lab configuration on reruns.
   if line.split('=',1)[1] in ('127.0.0.1','0.0.0.0','192.168.50.20'):
    lines[n]=key+'='+value
   matched=True;break
 if not matched:lines.append(key+'='+value)
 content='\n'.join(lines)+'\n'
p.write_text(content)
PY
chmod 600 .env
chown "$OWNER_UID:$OWNER_GID" .env
mkdir -p firmware data/workbench data/research data/mobile data/serial data/research-imports
chown -R "$OWNER_UID:$OWNER_GID" firmware data/workbench data/research data/mobile data/serial data/research-imports
python3 scripts/validate-project.py
if [[ $SKIP_CODE_SERVER == false ]]; then
  bash scripts/install-code-server.sh --user "$TARGET_USER" --workspace "$INSTALL_DIR" --port 8443
fi
if [[ $SKIP_START == false ]]; then
  LAB_UID_OVERRIDE="$OWNER_UID" LAB_GID_OVERRIDE="$OWNER_GID" bash scripts/setup.sh
else
  echo 'Containers were not started (--no-start). Run sudo bash scripts/setup.sh from installation folder.'
fi
chown "$OWNER_UID:$OWNER_GID" .env
cat <<EOF

Device RE Lab destination: $INSTALL_DIR
SSH service: enabled; account: $TARGET_USER
Desktop VS Code: install VS Code + Remote - SSH locally; SSH to $TARGET_USER@SERVER_IP and open $INSTALL_DIR
Browser VS Code: SSH -L 8443:127.0.0.1:8443 $TARGET_USER@SERVER_IP then open http://127.0.0.1:8443
Browser VS Code password: stored in $TARGET_USER's ~/.config/relab-code-server/config.yaml (mode 600).
Dashboards on server: 127.0.0.1:8090, 127.0.0.1:8310 and 127.0.0.1:8320
Firmware downloader: python3 $INSTALL_DIR/scripts/download-firmware.py https://vendor.example/firmware.bin
Access them remotely via VS Code forwarded ports or SSH -L (do not expose MCP publicly).
DNS/HTTPS listeners bound to: $LAB_IP (localhost unless --lab-ip was chosen)
EOF
if [[ $GRANT_DOCKER == false ]]; then
  echo 'Docker CLI access for SSH user NOT granted. Use sudo or rerun installer with --grant-docker-access after reviewing root-equivalent risk.'
fi
