#!/usr/bin/env python3
"""Offline cross-client MCP/Compose/Skills validation. Does not launch Docker."""
from __future__ import annotations
import json
import sys
import tomllib
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
errors=[]

def require(test,msg):
    if not test:errors.append(msg)

def jsonfile(path):
    try:return json.loads((ROOT/path).read_text())
    except Exception as exc:
        errors.append(f'{path}: {exc}');return {}

names={'device-dns':'8301','device-mitm':'8302','device-pcap':'8303',
       'device-ble':'8304','device-docker':'8305','device-api':'8090','device-ghidra':'8306','device-workbench':'8310','device-research':'8320',
       'device-binwalk':'8307','device-radare':'8308','device-yara':'8309','device-zeek':'8311','device-nmap':'8312','device-adb':'8313','device-filesystem':'8314','device-db':'8315'}
ide=jsonfile('.agents/mcp_config.json').get('mcpServers',{})
vscode=jsonfile('.vscode/mcp.json').get('servers',{})
portable=jsonfile('.mcp.json').get('mcpServers',{})
cursor=jsonfile('.cursor/mcp.json').get('mcpServers',{})
try:codex=tomllib.loads((ROOT/'.codex/config.toml').read_text()).get('mcp_servers',{})
except Exception as exc:errors.append(f'Codex TOML invalid: {exc}');codex={}
require(set(ide)==set(names),f'Antigravity server names do not match expected ({len(names)})')
require(set(vscode)==set(names),f'VS Code server names do not match expected ({len(names)})')
require(set(codex)==set(names),f'Codex server names do not match expected ({len(names)})')
require(set(portable)==set(names),f'Portable MCP server names do not match expected ({len(names)})')
require(set(cursor)==set(names),f'Cursor server names do not match expected ({len(names)})')
for name,port in names.items():
    entries=[('Antigravity',ide.get(name,{}).get('serverUrl')),
             ('VS Code',vscode.get(name,{}).get('url')),
             ('Codex',codex.get(name,{}).get('url')),
             ('Portable',portable.get(name,{}).get('url')),
             ('Cursor',cursor.get(name,{}).get('url'))]
    for client,url in entries:
        require(bool(url) and urlparse(url).hostname=='127.0.0.1' and str(urlparse(url).port)==port,
                f'{client}: {name} expected localhost:{port}, got {url!r}')
    require(vscode.get(name,{}).get('type')=='http',f'VS Code {name} must use HTTP')
    require(codex.get(name,{}).get('enabled') is True,f'Codex {name} not enabled')
require((ROOT/'api/main.py').read_text().find('lab_mcp.mount_http(mount_path="/mcp")') < (ROOT/'api/main.py').read_text().find('@app.api_route("/{path:path}"'), 'MCP route must be registered before catch-all simulator')
for f in ['README.md','AGENTS.md','GEMINI.md','docs/IDE.md','docs/MCP.md','docs/EXPERIMENTS.md',
          'api/main.py','workbench/main.py','workbench/engine.py','docs/ADVANCED_RESEARCH.md','docs/WORKBENCH_API.md','config/rules.json','nginx/default.conf','scripts/check-mcp.py',
          'scripts/setup.sh','scripts/smoke-test.sh','scripts/dns-rewrite.py']:
    require((ROOT/f).is_file(),f'Missing required file: {f}')
skills=sorted((ROOT/'.agents/skills').glob('*/SKILL.md'))
require(len(skills)>=35,'Need at least thirty-five included agent skills')
for f in skills:
    s=f.read_text()
    require(s.startswith('---\n') and f'name: {f.parent.name}' in s and '\ndescription:' in s,
            f'Invalid SKILL.md frontmatter: {f}')
try:
    import yaml
    compose=yaml.safe_load((ROOT/'compose.yaml').read_text())
    services=compose.get('services',{})
    for service in ['dns','mcp-dns','api','cert-init','https-edge','mitm','mcp-wireshark','mcp-ble','docker-socket-proxy','mcp-docker','analyzer','ghidra','workbench','fuzz','fuzz-serial','binwalk','syft','grype','qemu','renode','research-hub','research-worker','research-db','research-events',
                    'mcp-binwalk','mcp-radare','mcp-yara','mcp-zeek','mcp-nmap','mcp-adb','mcp-filesystem','mcp-database']:
        require(service in services,f'Compose missing {service}')
    for service in ['mcp-dns','mitm','mcp-wireshark','mcp-ble','mcp-docker','workbench','research-hub',
                    'mcp-binwalk','mcp-radare','mcp-yara','mcp-zeek','mcp-nmap','mcp-adb','mcp-filesystem','mcp-database']:
        require(any('127.0.0.1:' in str(x) or 'LAB_BIND_IP' in str(x) or '0.0.0.0:' in str(x) for x in services[service].get('ports',[])),
                f'Compose MCP {service} should expose loopback or LAB_BIND_IP')
    cmd=''.join(services['capture']['command'][-1])
    require('tcpdump' in cmd and "-w '/captures/" in cmd,'Capture tcpdump command incomplete')
except ImportError:
    print('WARN: PyYAML not installed; skipped parsing compose.yaml (pip install pyyaml)')
except Exception as exc: errors.append(f'Invalid compose.yaml: {exc}')

for f in (ROOT/'.vscode').glob('*.json'):jsonfile(str(f.relative_to(ROOT)))
try:
    import py_compile
    for f in [ROOT/'api/main.py',ROOT/'workbench/main.py',ROOT/'workbench/engine.py',ROOT/'workbench/timeline.py',ROOT/'research-hub/research_api.py',ROOT/'research-hub/research_models.py',ROOT/'research-hub/research_core.py',ROOT/'research-hub/worker.py',ROOT/'research-hub/research_ingest.py',ROOT/'fuzz/run.py',ROOT/'scripts/check-mcp.py',ROOT/'scripts/dns-rewrite.py',
              ROOT/'mcp/binwalk/server.py',ROOT/'mcp/radare/server.py',ROOT/'mcp/yara/server.py',ROOT/'mcp/zeek/server.py',ROOT/'mcp/nmap/server.py',ROOT/'mcp/adb/server.py',ROOT/'mcp/filesystem/server.py',ROOT/'mcp/database/server.py']:
        py_compile.compile(str(f),doraise=True)
except Exception as exc:errors.append(f'Python syntax error: {exc}')

if errors:
    for e in errors:print('FAIL',e)
    sys.exit(f'Static validation failed with {len(errors)} error(s)')
print(f'PASS static validation: {len(names)} MCPs across Antigravity, Codex, VS Code, Cursor, portable; {len(skills)} agent skills')
print('NOTE: Does not establish Docker images started or MCP live tool lists. Run scripts/check-mcp.py on host.')
