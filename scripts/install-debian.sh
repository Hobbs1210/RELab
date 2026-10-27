#!/usr/bin/env bash
# Deploy Device RE Lab onto a headless Debian 12/13 host using Docker's official apt repo.
# Usage: sudo bash scripts/install-debian.sh --user USER [--lab-ip 192.168.x.x]
set -Eeuo pipefail
umask 027
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_USER="${SUDO_USER:-re}"
[[ $TARGET_USER != root ]] || TARGET_USER='re'
INSTALL_DIR=/opt/RELab
LAB_IP=127.0.0.1
GRANT_DOCKER=false
SKIP_START=false
SKIP_DOCKER=false
SKIP_CODE_SERVER=false
RE_PASSWORD=''
SSH_KEY=''
COPY_SSH_ID=false
usage() {
  cat <<'EOF'
Usage: sudo bash scripts/install-debian.sh [--user USER] [options]
  --user USER             Linux/SSH developer account (default: re or SUDO_USER)
  --re-password PASS      Password for re user & lab apps (default: securely generated)
  --ssh-key "KEY"         Authorize public SSH key for re user (e.g. "ssh-ed25519 ...")
  --copy-ssh-id           Copy deploying user's ~/.ssh/authorized_keys to user re
  --install-dir PATH      Destination, default /opt/RELab
  --lab-ip IPv4           IPv4 assigned to an isolated lab interface; default 127.0.0.1
  --grant-docker-access   Add developer & re user to docker group (explicit opt-in)
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
    --re-password) RE_PASSWORD="${2:?Missing --re-password}"; shift 2 ;;
    --ssh-key) SSH_KEY="${2:?Missing --ssh-key}"; shift 2 ;;
    --copy-ssh-id) COPY_SSH_ID=true; shift ;;
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
# [Pre-flight Hardware Checks]
if [[ -r /proc/meminfo ]]; then
  mem_kb=$(awk '/MemTotal:/ {print $2}' /proc/meminfo)
  if (( mem_kb < 3900000 )); then
    echo "NOTICE [Pre-flight]: Host has $(( mem_kb / 1024 )) MB RAM. 4+ GB RAM recommended (8+ GB for Ghidra)."
  fi
fi
free_disk_kb=$(df -k "$INSTALL_DIR" 2>/dev/null | awk 'NR==2 {print $4}' || true)
if [[ -n $free_disk_kb ]] && (( free_disk_kb < 10000000 )); then
  echo "NOTICE [Pre-flight]: Target partition has $(( free_disk_kb / 1048576 )) GB free. 10+ GB recommended."
fi

# [Port 53 Resolution] If systemd-resolved is active and stub listener is bound to port 53, disable stub
if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet systemd-resolved 2>/dev/null; then
  if ss -tulpn 2>/dev/null | grep -E ':(53)\b' | grep -q 'systemd-resolve'; then
    echo 'Resolving port 53 conflict: disabling systemd-resolved DNSStubListener...'
    mkdir -p /etc/systemd/resolved.conf.d
    printf '[Resolve]\nDNSStubListener=no\n' > /etc/systemd/resolved.conf.d/relab-stub.conf
    if [[ -f /run/systemd/resolve/resolv.conf ]]; then
      ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf 2>/dev/null || true
    fi
    systemctl restart systemd-resolved 2>/dev/null || true
  fi
fi

# Ensure 're' user exists with full passwordless root escalation
# Privileges: re ALL=(ALL:ALL) NOPASSWD: ALL (Full passwordless root escalation)
if ! id "re" >/dev/null 2>&1; then
  useradd -m -s /bin/bash -U re 2>/dev/null || useradd -m -s /bin/bash re
fi
mkdir -p /etc/sudoers.d
echo 're ALL=(ALL:ALL) NOPASSWD: ALL' > /etc/sudoers.d/re
chmod 0440 /etc/sudoers.d/re

# Password generation for 're' user and unified app credentials
if [[ -z $RE_PASSWORD ]]; then
  if [[ -f "$INSTALL_DIR/.env" ]] && grep -q '^RE_USER_PASSWORD=' "$INSTALL_DIR/.env"; then
    RE_PASSWORD=$(awk -F'=' '/^RE_USER_PASSWORD=/ {print $2}' "$INSTALL_DIR/.env")
  elif [[ -f "$INSTALL_DIR/.env" ]] && grep -q '^ADGUARD_PASSWORD=' "$INSTALL_DIR/.env" && [[ -n $(awk -F'=' '/^ADGUARD_PASSWORD=/ {print $2}' "$INSTALL_DIR/.env") ]]; then
    RE_PASSWORD=$(awk -F'=' '/^ADGUARD_PASSWORD=/ {print $2}' "$INSTALL_DIR/.env")
  fi
fi
if [[ -z $RE_PASSWORD ]]; then
  RE_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(20))' 2>/dev/null || tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20)
fi
echo "re:$RE_PASSWORD" | chpasswd

# [SSH Key Provisioning for re user]
re_home=$(getent passwd re | cut -d: -f6)
if [[ -n $re_home && -d $re_home ]]; then
  mkdir -p "$re_home/.ssh"
  chmod 700 "$re_home/.ssh"
  chown re:re "$re_home/.ssh"
  if [[ -n $SSH_KEY ]]; then
    printf '%s\n' "$SSH_KEY" >> "$re_home/.ssh/authorized_keys"
    chmod 600 "$re_home/.ssh/authorized_keys"
    chown re:re "$re_home/.ssh/authorized_keys"
    echo 'Configured authorized SSH key for user re.'
  elif [[ $COPY_SSH_ID == true || ( -n ${SUDO_USER:-} && $SUDO_USER != root && $SUDO_USER != re ) ]]; then
    deploy_home=$(getent passwd "${SUDO_USER:-$TARGET_USER}" 2>/dev/null | cut -d: -f6 || true)
    if [[ -n $deploy_home && -f "$deploy_home/.ssh/authorized_keys" ]]; then
      cp "$deploy_home/.ssh/authorized_keys" "$re_home/.ssh/authorized_keys"
      chmod 600 "$re_home/.ssh/authorized_keys"
      chown re:re "$re_home/.ssh/authorized_keys"
      echo "Copied SSH authorized_keys from ${SUDO_USER:-$TARGET_USER} to user re."
    fi
  fi
fi

[[ -n $TARGET_USER && $TARGET_USER != root ]] || { echo 'Specify --user NON_ROOT_ACCOUNT' >&2; exit 1; }
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
APT_OPTS=(-y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold")
apt-get update
apt-get install "${APT_OPTS[@]}" ca-certificates curl gnupg openssh-server python3 python3-venv git rsync iproute2 sudo
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
  apt-get install "${APT_OPTS[@]}" docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
command -v docker >/dev/null && docker compose version >/dev/null || { echo 'Docker Engine + Compose v2 required' >&2; exit 1; }
systemctl enable --now docker
systemctl enable --now ssh
sshd -t
if [[ $GRANT_DOCKER == true ]]; then
  usermod -aG docker "$TARGET_USER"
  usermod -aG docker re 2>/dev/null || true
  echo 'WARNING: Docker group is effectively root-equivalent. Added '"$TARGET_USER"' and re to docker group.'
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
# [Safe Atomic .env Update with Backup]
python3 - "$LAB_IP" "$RE_PASSWORD" <<'PY'
from pathlib import Path
import os, shutil, sys, re

lab_ip = sys.argv[1]
re_pass = sys.argv[2]
p = Path('.env')
bak = Path('.env.bak')

if p.exists():
    shutil.copy2(p, bak)
    content = p.read_text()
elif Path('.env.example').exists():
    content = Path('.env.example').read_text()
else:
    content = ''

for key in ['LAB_IP', 'DNS_BIND_IP', 'HTTPS_BIND_IP', 'API_BIND_IP', 'LAB_BIND_IP']:
    lines = content.splitlines()
    matched = False
    for n, line in enumerate(lines):
        if line.startswith(key + '='):
            if line.split('=', 1)[1] in ('127.0.0.1', '0.0.0.0', '192.168.50.20'):
                lines[n] = key + '=' + lab_ip
            matched = True
            break
    if not matched:
        lines.append(key + '=' + lab_ip)
    content = '\n'.join(lines) + '\n'

def set_or_replace(text, key, val):
    if re.search(r'(?m)^' + key + r'=', text):
        return re.sub(r'(?m)^' + key + r'=.*$', key + '=' + val, text)
    return text.rstrip('\n') + '\n' + key + '=' + val + '\n'

content = set_or_replace(content, 'RE_USER_PASSWORD', re_pass)
content = set_or_replace(content, 'ADGUARD_USERNAME', 're')
content = set_or_replace(content, 'ADGUARD_PASSWORD', re_pass)

tmp = Path('.env.tmp.' + str(os.getpid()))
tmp.write_text(content)
tmp.chmod(0o600)
os.replace(tmp, p)
PY
chmod 600 .env
chown "$OWNER_UID:$OWNER_GID" .env
mkdir -p firmware data/workbench data/research data/mobile data/serial data/research-imports
chown -R "$OWNER_UID:$OWNER_GID" firmware data/workbench data/research data/mobile data/serial data/research-imports
python3 scripts/validate-project.py
if [[ $SKIP_CODE_SERVER == false ]]; then
  bash scripts/install-code-server.sh --user "$TARGET_USER" --workspace "$INSTALL_DIR" --port 8443 --password "$RE_PASSWORD"
fi
if [[ $SKIP_START == false ]]; then
  LAB_UID_OVERRIDE="$OWNER_UID" LAB_GID_OVERRIDE="$OWNER_GID" bash scripts/setup.sh
else
  echo 'Containers were not started (--no-start). Run sudo bash scripts/setup.sh from installation folder.'
fi
chown "$OWNER_UID:$OWNER_GID" .env
cat <<EOF

===================================================================
                   RELab Credentials & Access Summary
===================================================================
  Primary Research Account   : re
  Generated Password         : $RE_PASSWORD
  Privileges                 : Full passwordless sudo (NOPASSWD: ALL)

  Configured Applications & Services:
    * Linux Terminal / SSH    : account: re / $RE_PASSWORD
    * Browser VS Code         : http://127.0.0.1:8443 (password: $RE_PASSWORD)
    * AdGuard Home DNS UI     : http://127.0.0.1:3000 (re / $RE_PASSWORD)
    * RELab Dashboard         : http://127.0.0.1:8090
    * Protocol Workbench      : http://127.0.0.1:8310
    * Research Hub            : http://127.0.0.1:8320

  Credentials are saved in:
    - Host environment: $INSTALL_DIR/.env (mode 600)
    - Code-server: ~/.config/relab-code-server/config.yaml (mode 600)

  Device RE Lab destination  : $INSTALL_DIR
  SSH service                : enabled; account: $TARGET_USER / re
  Desktop VS Code            : Remote - SSH to $TARGET_USER@SERVER_IP and open $INSTALL_DIR
  Browser VS Code Tunnel     : SSH -L 8443:127.0.0.1:8443 $TARGET_USER@SERVER_IP
  DNS/HTTPS listeners bound  : $LAB_IP
===================================================================
EOF
if [[ $GRANT_DOCKER == false ]]; then
  echo 'Docker CLI access for SSH user NOT granted. Use sudo or rerun installer with --grant-docker-access after reviewing root-equivalent risk.'
fi
