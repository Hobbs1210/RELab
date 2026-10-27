#!/usr/bin/env bash
# RELab one-shot bootstrap for headless Debian 12/13.
# Download this file from the public RELab GitHub repository, review it, then run with sudo.
# Example:
#   curl -fsSLo /tmp/relab-bootstrap.sh https://raw.githubusercontent.com/Hobbs1210/RELab/main/scripts/bootstrap-debian.sh
#   sudo bash /tmp/relab-bootstrap.sh --user "$USER"
set -Eeuo pipefail
umask 027

REPO_URL='https://github.com/Hobbs1210/RELab.git'
BRANCH='main'
INSTALL_DIR='/opt/RELab'
TARGET_USER="${SUDO_USER:-re}"
[[ $TARGET_USER != root ]] || TARGET_USER='re'
LAB_IP=''
GRANT_DOCKER=false
SKIP_CODE_SERVER=false
SKIP_START=false
SKIP_DOCKER=false
SKIP_UPDATE=false
RE_PASSWORD=''

usage() {
  cat <<'USAGE'
RELab headless Debian bootstrap (fetches the repository and deploys it)
Usage: sudo bash relab-bootstrap.sh [--user USER] [options]
  --user USER             Linux/SSH account (default: re or SUDO_USER)
  --re-password PASS      Password for re user & lab apps (default: securely generated)
  --install-dir PATH      Git working tree and deployment path (default /opt/RELab)
  --lab-ip PRIVATE_IP     Enable DNS/HTTPS listener on this assigned lab-interface IPv4
  --grant-docker-access   Add account & re user to Docker group (opt-in)
  --skip-code-server      Do not install the local browser VS Code editor
  --skip-update           Do not git fetch/fast-forward an existing clone
  --skip-docker-install   Use an already installed Docker Engine and Compose
  --no-start              Install dependencies and workspace without starting containers
  --help                  Print help
The bootstrap does not configure a public reverse proxy, firewall, Wi-Fi, or router DNS.
USAGE
}
while (($#)); do
  case "$1" in
    --user) TARGET_USER="${2:?Expected username after --user}"; shift 2 ;;
    --re-password) RE_PASSWORD="${2:?Expected password after --re-password}"; shift 2 ;;
    --install-dir) INSTALL_DIR="${2:?Expected directory after --install-dir}"; shift 2 ;;
    --lab-ip) LAB_IP="${2:?Expected IPv4 after --lab-ip}"; shift 2 ;;
    --grant-docker-access) GRANT_DOCKER=true; shift ;;
    --skip-code-server) SKIP_CODE_SERVER=true; shift ;;
    --skip-update) SKIP_UPDATE=true; shift ;;
    --skip-docker-install) SKIP_DOCKER=true; shift ;;
    --no-start) SKIP_START=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'Unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ $EUID -eq 0 ]] || { echo 'Run as root using sudo (or root shell).' >&2; exit 1; }
[[ -f /etc/os-release ]] || { echo 'Cannot determine Linux distribution.' >&2; exit 1; }
# shellcheck source=/dev/null
. /etc/os-release
[[ ${ID:-} == debian && ${VERSION_ID%%.*} =~ ^(12|13)$ ]] || { echo 'Supported on Debian 12/13 only.' >&2; exit 1; }

# [Pre-flight Hardware Checks]
if [[ -r /proc/meminfo ]]; then
  mem_kb=$(awk '/MemTotal:/ {print $2}' /proc/meminfo)
  if (( mem_kb < 3900000 )); then
    echo "NOTICE [Pre-flight]: Host has $(( mem_kb / 1024 )) MB RAM. 4+ GB RAM recommended (8+ GB for Ghidra)."
  fi
fi
free_disk_kb=$(df -k "$(dirname "$INSTALL_DIR")" 2>/dev/null | awk 'NR==2 {print $4}' || true)
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

[[ -n $TARGET_USER && $TARGET_USER != root ]] || { echo 'Provide --user for a non-root SSH account.' >&2; exit 1; }
id "$TARGET_USER" >/dev/null || { echo "Account $TARGET_USER does not exist" >&2; exit 1; }
[[ $INSTALL_DIR == /* && $INSTALL_DIR != / && $INSTALL_DIR != /opt && $INSTALL_DIR != *[[:space:]]* ]] || {
  echo 'Use a dedicated, absolute path without whitespace for --install-dir.' >&2; exit 1;
}

export DEBIAN_FRONTEND=noninteractive
APT_OPTS=(-y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold")
printf '[RELab 1/3] Installing Git and initial Debian requirements\n'
apt-get update
apt-get install "${APT_OPTS[@]}" ca-certificates curl git python3 sudo

uid=$(id -u "$TARGET_USER")
gid=$(id -g "$TARGET_USER")
if [[ -e $INSTALL_DIR && ! -d $INSTALL_DIR ]]; then
  echo "Destination is not a directory: $INSTALL_DIR" >&2; exit 1
fi
if [[ -d $INSTALL_DIR && ! -d $INSTALL_DIR/.git ]]; then
  echo "Refusing to overwrite existing non-Git directory: $INSTALL_DIR" >&2
  echo 'Choose --install-dir pointing to a new directory.' >&2
  exit 1
fi

printf '[RELab 2/3] Fetching %s\n' "$REPO_URL"
if [[ ! -d $INSTALL_DIR/.git ]]; then
  mkdir -p "$(dirname "$INSTALL_DIR")"
  install -d -m 0750 -o "$TARGET_USER" -g "$(id -gn "$TARGET_USER")" "$INSTALL_DIR"
  # Git must be owned by the SSH developer so subsequent VS Code edits and pulls work.
  runuser -u "$TARGET_USER" -- git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$INSTALL_DIR"
else
  current_remote=$(runuser -u "$TARGET_USER" -- git -C "$INSTALL_DIR" remote get-url origin)
  if [[ $current_remote != "$REPO_URL" ]]; then
    echo "Existing checkout origin does not match $REPO_URL; refusing to update." >&2; exit 1
  fi
  current_branch=$(runuser -u "$TARGET_USER" -- git -C "$INSTALL_DIR" branch --show-current)
  [[ $current_branch == "$BRANCH" ]] || { echo "Expected branch $BRANCH, got $current_branch" >&2; exit 1; }
  if [[ $SKIP_UPDATE == false ]]; then
    if [[ -n $(runuser -u "$TARGET_USER" -- git -C "$INSTALL_DIR" status --porcelain --untracked-files=no) ]]; then
      echo 'Tracked files have local edits. Commit/stash them or use --skip-update; no files were overwritten.' >&2
      exit 1
    fi
    runuser -u "$TARGET_USER" -- git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    runuser -u "$TARGET_USER" -- git -C "$INSTALL_DIR" merge --ff-only FETCH_HEAD
  else
    echo 'Existing checkout preserved (--skip-update).'
  fi
fi

printf '[RELab 3/3] Installing Docker, SSH, browser IDE, and RELab services\n'
args=(--user "$TARGET_USER" --install-dir "$INSTALL_DIR")
[[ -z $RE_PASSWORD ]] || args+=(--re-password "$RE_PASSWORD")
[[ -z $LAB_IP ]] || args+=(--lab-ip "$LAB_IP")
[[ $GRANT_DOCKER == false ]] || args+=(--grant-docker-access)
[[ $SKIP_CODE_SERVER == false ]] || args+=(--skip-code-server)
[[ $SKIP_DOCKER == false ]] || args+=(--skip-docker-install)
[[ $SKIP_START == false ]] || args+=(--no-start)
bash "$INSTALL_DIR/scripts/install-debian.sh" "${args[@]}"

printf '\nRELab Git working tree: %s (owned by %s, UID %s/GID %s)\n' "$INSTALL_DIR" "$TARGET_USER" "$uid" "$gid"
echo 'To edit with desktop VS Code, use Remote-SSH and open the same folder.'
echo 'To use browser VS Code, SSH-forward port 8443 (when code-server is enabled).'
