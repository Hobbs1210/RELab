#!/usr/bin/env bash
# First-run bootstrap, ensures AdGuard is configured before its MCP starts.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Docker and Docker Compose required'; exit 1; }
command -v python3 >/dev/null || { echo 'Python 3 required'; exit 1; }

ACTION="${1:-start}"

case "$ACTION" in
  status)
    printf "=== RELab Docker Service Status ===\n"
    docker compose ps
    exit 0
    ;;
  stop)
    printf "Stopping RELab services...\n"
    docker compose stop
    exit 0
    ;;
  restart)
    printf "Restarting RELab services...\n"
    docker compose restart
    exit 0
    ;;
  logs)
    docker compose logs -f --tail=50 "${2:-}"
    exit 0
    ;;
  backup)
    printf "Backing up research database...\n"
    mkdir -p data/research/backups
    ts=$(date +%Y%m%d_%H%M%S 2>/dev/null || python3 -c 'import time; print(time.strftime("%Y%m%d_%H%M%S"))')
    backup_file="data/research/backups/research-db-${ts}.sql"
    if docker compose ps -q research-db >/dev/null 2>&1 && [[ -n $(docker compose ps -q research-db) ]]; then
      docker compose exec -T research-db pg_dump -U research -d research > "$backup_file"
      printf "Database backup saved to: %s\n" "$backup_file"
    else
      echo "Error: research-db container is not running." >&2
      exit 1
    fi
    exit 0
    ;;
  start|up|"")
    ;; # proceed with full setup / startup
  *)
    echo "Usage: scripts/setup.sh [start|stop|restart|status|logs|backup]" >&2
    exit 2
    ;;
esac

# [Port 53 Resolution] If systemd-resolved is active and stub listener is bound to port 53, disable stub
if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
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
fi

# [Safe Atomic .env Update with Backup]
python3 - <<'PY'
from pathlib import Path
import os, shutil, secrets, re

p = Path('.env')
bak = Path('.env.bak')
if p.exists():
    try:
        if bak.exists():
            bak.unlink(missing_ok=True)
        shutil.copy2(p, bak)
    except Exception:
        try:
            bak.write_text(p.read_text())
        except Exception:
            pass  # proceed even if backup file cannot be overwritten
    s = p.read_text()
else:
    s = Path('.env.example').read_text()

re_pass = None
for line in s.splitlines():
    if line.startswith('RE_USER_PASSWORD='):
        val = line.split('=', 1)[1].strip()
        if val: re_pass = val

if 'ADGUARD_USERNAME=' not in s:
    s += '\nADGUARD_USERNAME=re\n'
elif 'ADGUARD_USERNAME=admin' in s:
    s = s.replace('ADGUARD_USERNAME=admin', 'ADGUARD_USERNAME=re')

if 'ADGUARD_PASSWORD=' not in s:
    s += '\nADGUARD_PASSWORD=\n'

if re_pass:
    s = re.sub(r'(?m)^ADGUARD_PASSWORD=.*$', 'ADGUARD_PASSWORD=' + re_pass, s)
elif not re.search(r'(?m)^ADGUARD_PASSWORD=.+$', s):
    s = s.replace('ADGUARD_PASSWORD=\n', 'ADGUARD_PASSWORD=' + secrets.token_urlsafe(24) + '\n')

if 'LAB_ADMIN_TOKEN=' not in s: s += '\nLAB_ADMIN_TOKEN=\n'
if not re.search(r'(?m)^LAB_ADMIN_TOKEN=.+$', s):
    s = s.replace('LAB_ADMIN_TOKEN=\n', 'LAB_ADMIN_TOKEN=' + secrets.token_urlsafe(36) + '\n')

if 'RESEARCH_DB_PASSWORD=' not in s: s += '\nRESEARCH_DB_PASSWORD=\n'
if not re.search(r'(?m)^RESEARCH_DB_PASSWORD=.+$', s):
    s = s.replace('RESEARCH_DB_PASSWORD=\n', 'RESEARCH_DB_PASSWORD=' + secrets.token_urlsafe(32) + '\n')

# Keep bind-mounted output directories writable as the invoking host user.
target_uid = int(os.environ.get('LAB_UID_OVERRIDE', os.environ.get('SUDO_UID', str(os.getuid()))))
target_gid = int(os.environ.get('LAB_GID_OVERRIDE', os.environ.get('SUDO_GID', str(os.getgid()))))

for key, value in [('LAB_UID', str(target_uid)), ('LAB_GID', str(target_gid))]:
    s = re.sub(r'(?m)^' + key + r'=.*$', key + '=' + value, s)

tmp = Path('.env.tmp.' + str(os.getpid()))
tmp.write_text(s)
tmp.chmod(0o600)
os.replace(tmp, p)
if target_uid != 0 and hasattr(os, 'chown'):
    try:
        os.chown(p, target_uid, target_gid)
    except OSError:
        pass
    if bak.exists():
        try:
            os.chown(bak, target_uid, target_gid)
        except OSError:
            pass
PY

# [Port Collision Pre-check]
python3 - <<'PY'
import socket
ports = [(53, 'DNS (AdGuard)'), (3000, 'AdGuard Web UI'), (8090, 'Lab API'), (8310, 'Workbench'), (8320, 'Research Hub')]
conflicts = []
for p, desc in ports:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('127.0.0.1', p))
    except OSError:
        conflicts.append((p, desc))
    finally:
        s.close()
if conflicts:
    print('Notice [Port Check]: The following ports are active on host (normal on reruns):')
    for p, desc in conflicts:
        print(f'  - Port {p}: {desc}')
PY
mkdir -p data/{api,pcaps,mitm,ble,nginx,analysis,ghidra,workbench,firmware-extracted,sbom,emulation,fuzz,research,mobile,serial,research-imports} firmware certs config/adguard/{work,conf}

echo '[1/3] Starting DNS server (AdGuard Home)'
docker compose up -d dns
python3 - <<'PY'
import base64,json,time,urllib.request,urllib.error
from pathlib import Path
settings={}
for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.startswith('#'):
        k,v=line.split('=',1);settings[k]=v
base='http://127.0.0.1:3000'
header='Basic '+base64.b64encode((settings['ADGUARD_USERNAME']+':'+settings['ADGUARD_PASSWORD']).encode()).decode()

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(NoRedirect)

def fetch(path, payload=None, auth=False):
    headers={'Content-Type':'application/json'}
    if auth:headers['Authorization']=header
    data=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(base+path,data=data,headers=headers)
    try:
        with opener.open(req,timeout=5) as r:
            body=r.read()
            try:
                return json.loads(body) if body else {}
            except Exception:
                return {}
    except urllib.error.HTTPError as e:
        if path == '/control/install/configure' and e.code in (200, 302):
            return {}
        raise

for i in range(40):
    try:
        try:
            status=fetch('/control/status',auth=True)
            print('AdGuard already configured; verified admin credentials.')
            break
        except urllib.error.HTTPError as e:
            loc = e.headers.get('Location', '') if hasattr(e, 'headers') and e.headers else ''
            if e.code == 401 or (e.code == 302 and 'login' in loc):
                raise SystemExit('AdGuard already configured with DIFFERENT credentials. Restore the original .env or reset AdGuard manually.')
            if e.code not in (404, 400, 302):
                raise
        fetch('/control/install/get_addresses')
        payload={'web':{'ip':'0.0.0.0','port':3000},'dns':{'ip':'0.0.0.0','port':53},'username':settings['ADGUARD_USERNAME'],'password':settings['ADGUARD_PASSWORD']}
        fetch('/control/install/configure',payload)
        print('AdGuard installed on web port 3000 and DNS port 53.')
        break
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        if i == 39: raise
        time.sleep(1)
else:
    raise SystemExit('Unable to initialize AdGuard')
PY

echo '[2/3] Building and starting sixteen default MCP endpoints, analyzer and API emulator'
docker compose up -d --build

echo '[3/3] Service state'
docker compose ps
printf '\nOpen http://127.0.0.1:8090 for lab dashboard.\n'
printf 'See docs/MCP.md for research MCP endpoints plus optional Ghidra. Credentials are in private .env.\n'
