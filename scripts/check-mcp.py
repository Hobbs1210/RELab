#!/usr/bin/env python3
"""MCP handshake / tool list smoke check; doesn't need the mcp Python package."""
from __future__ import annotations
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
import urllib.error
import urllib.request

SERVERS = {
    "AdGuard DNS": "http://127.0.0.1:8301/",
    "mitmproxy": "http://127.0.0.1:8302/mcp",
    "Wireshark": "http://127.0.0.1:8303/mcp",
    "BLE": "http://127.0.0.1:8304/mcp",
    "Docker": "http://127.0.0.1:8305/mcp",
    "Device API": "http://127.0.0.1:8090/mcp",
    "Ghidra (optional)": "http://127.0.0.1:8306/mcp",
    "Universal workbench": "http://127.0.0.1:8310/mcp",
    "Research Hub": "http://127.0.0.1:8320/mcp",
    "Binwalk (optional)": "http://127.0.0.1:8307/mcp",
    "Radare2 (optional)": "http://127.0.0.1:8308/mcp",
    "YARA (optional)": "http://127.0.0.1:8309/mcp",
    "Zeek (optional)": "http://127.0.0.1:8311/mcp",
    "Nmap (optional)": "http://127.0.0.1:8312/mcp",
    "ADB (optional)": "http://127.0.0.1:8313/mcp",
    "Filesystem (optional)": "http://127.0.0.1:8314/mcp",
    "Database (optional)": "http://127.0.0.1:8315/mcp",
}

def invoke(url, method, params, session=None):
    body = json.dumps({"jsonrpc": "2.0", "id": 1 if method == "initialize" else 2,
                       "method": method, "params": params}).encode()
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
               "MCP-Protocol-Version": "2025-06-18"}
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(url, body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=10) as result:
        response = result.read(512 * 1024).decode(errors="replace")
        session_id = result.headers.get("Mcp-Session-Id")
        # Streamable HTTP may reply with JSON or text/event-stream.
        if response.lstrip().startswith("{"):
            doc = json.loads(response)
        else:
            events = [json.loads(line[5:].strip()) for line in response.splitlines()
                      if line.startswith("data:") and line[5:].strip().startswith("{")]
            doc = next((d for d in events if "result" in d or "error" in d), None)
            if doc is None:
                raise RuntimeError("No MCP JSON-RPC reply in HTTP/SSE response")
        if "error" in doc:
            raise RuntimeError(str(doc["error"]))
        return doc["result"], session_id

failures = 0
results = {}
for name,url in SERVERS.items():
    if "(optional)" in name and '--all' not in sys.argv:
        results[name]={'status':'not_started_optional'}
        print(f'SKIP {name} (optional profile; pass --all to include)')
        continue
    try:
        result, session = invoke(url, "initialize", {
            "protocolVersion":"2025-06-18",
            "capabilities":{},
            "clientInfo":{"name":"device-lab-smoke","version":"1.0"}
        })
        # servers may require initialized notification; fall back if unsupported.
        try:
            req=urllib.request.Request(url,b'{"jsonrpc":"2.0","method":"notifications/initialized"}',
                {"Content-Type":"application/json","Accept":"application/json, text/event-stream",
                 "Mcp-Session-Id":session or "", "MCP-Protocol-Version":"2025-06-18"}, method="POST")
            with urllib.request.urlopen(req,timeout=3):pass
        except Exception: pass
        tools, _ = invoke(url,"tools/list",{},session)
        items = tools.get("tools", [])
        if not items:
            raise RuntimeError("MCP initialized, but tools/list was empty")
        results[name]={"status":"verified","tool_count":len(items)}
        print(f"OK {name:20} {len(items):3} tools: {url}")
    except Exception as ex:
        failures += 1
        results[name]={"status":"failed","reason":type(ex).__name__}
        print(f"FAIL {name:20} {url} | {type(ex).__name__}: {ex}")
opt_count = sum(1 for k in SERVERS if "(optional)" in k)
checked_count = len(SERVERS) if "--all" in sys.argv else (len(SERVERS) - opt_count)
print(f'Checked {checked_count} MCP servers; failed: {failures}')
if '--json-out' in sys.argv:
    idx=sys.argv.index('--json-out')
    if idx+1>=len(sys.argv):sys.exit('--json-out requires an output path')
    dest=Path(sys.argv[idx+1]);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps({'checked_at':datetime.now(timezone.utc).isoformat(),
                                'services':results,'failures':failures},indent=2)+'\n')
sys.exit(bool(failures))
