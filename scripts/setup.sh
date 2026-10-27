#!/usr/bin/env bash
# First-run bootstrap, ensures AdGuard is configured before its MCP starts.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v docker >/dev/null || { echo 'Docker and Docker Compose required'; exit 1; }
command -v python3 >/dev/null || { echo 'Python 3 required'; exit 1; }
if [[ ! -f .env ]]; then cp .env.example .env; chmod 600 .env; fi
python3 - <<'PY'
from pathlib import Path
import secrets
p=Path('.env')
s=p.read_text()
if 'ADGUARD_PASSWORD=' not in s:
    s+='\nADGUARD_PASSWORD=\n'
s=s.replace('ADGUARD_PASSWORD=\n', 'ADGUARD_PASSWORD='+secrets.token_urlsafe(24)+'\n')
if 'LAB_ADMIN_TOKEN=' not in s:s+='\nLAB_ADMIN_TOKEN=\n'
s=s.replace('LAB_ADMIN_TOKEN=\n','LAB_ADMIN_TOKEN='+secrets.token_urlsafe(36)+'\n')
if 'RESEARCH_DB_PASSWORD=' not in s:s+='\nRESEARCH_DB_PASSWORD=\n'
s=s.replace('RESEARCH_DB_PASSWORD=\n','RESEARCH_DB_PASSWORD='+secrets.token_urlsafe(32)+'\n')
# Keep bind-mounted output directories writable as the invoking host user.
import os
for key,value in [('LAB_UID',os.environ.get('LAB_UID_OVERRIDE',str(os.getuid()))),('LAB_GID',os.environ.get('LAB_GID_OVERRIDE',str(os.getgid())))]:
    import re
    s=re.sub(r'(?m)^'+key+r'=.*$',key+'='+value,s)
p.write_text(s)
p.chmod(0o600)
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

def fetch(path, payload=None, auth=False):
    headers={'Content-Type':'application/json'}
    if auth:headers['Authorization']=header
    data=json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(urllib.request.Request(base+path,data=data,headers=headers),timeout=5) as r:
        body=r.read();return json.loads(body) if body else {}
for i in range(40):
    try:
        try:
            status=fetch('/control/status',auth=True)
            print('AdGuard already configured; verified admin credentials.')
            break
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise SystemExit('AdGuard already configured with DIFFERENT credentials. Restore the original .env or reset AdGuard manually.')
            if e.code not in (404, 400):
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

echo '[2/3] Building and starting seven default MCP endpoints, analyzer and API emulator'
docker compose up -d --build

echo '[3/3] Service state'
docker compose ps
printf '\nOpen http://127.0.0.1:8090 for lab dashboard.\n'
printf 'See docs/MCP.md for research MCP endpoints plus optional Ghidra. Credentials are in private .env.\n'
