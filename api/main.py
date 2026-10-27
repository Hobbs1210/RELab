"""Device Reverse Engineering Lab API. User-defined response hypotheses only."""
from __future__ import annotations

import base64
import asyncio
import hmac
import secrets
import ipaddress
import urllib.request
import urllib.error
import urllib.parse
import json
import os
import re
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi_mcp import FastApiMCP
import research
from fastapi.responses import HTMLResponse, JSONResponse, Response

app = FastAPI(title="Device RE Lab", docs_url=None, redoc_url=None)
RULES_PATH = Path(os.environ.get("RULES_PATH", "/config/rules.json"))
DB_PATH = Path(os.environ.get("DB_PATH", "/data/requests.db"))
ADGUARD_URL = os.environ.get("ADGUARD_URL", "http://dns:3000").rstrip("/")
ADGUARD_USER = os.environ.get("ADGUARD_USERNAME", "admin")
ADGUARD_PASSWORD = os.environ.get("ADGUARD_PASSWORD", "")
UI_PATH = Path(__file__).with_name("ui.html")
LOCK = threading.Lock()
ADMIN_TOKEN = os.getenv('LAB_ADMIN_TOKEN', '')
SCENARIOS_PATH = Path(os.getenv('SCENARIOS_PATH', '/config/scenarios.json'))
OWNED_DNS_PATH = Path(os.getenv('OWNED_DNS_PATH','/config/owned-dns.json'))
ANALYSIS_PATH = Path(os.getenv('ANALYSIS_PATH','/analysis'))
FIRMWARE_PATH = Path(os.getenv('FIRMWARE_PATH','/firmware'))
PROFILE_DIR = Path(os.getenv('PROFILE_DIR','/profiles'))
TARGET_PROFILE = os.getenv('TARGET_PROFILE','generic')

@app.middleware('http')
async def protect_mutations(request: Request, call_next):
    # A write to the local control-plane is never permitted without a token.
    # MCP POST /mcp is not blocked, but the MCP tool list exposes GET-only operations.
    if request.url.path.startswith('/__lab__/') and request.method in ('POST','PUT','PATCH','DELETE'):
        given = request.headers.get('x-lab-token','')
        if not ADMIN_TOKEN or not hmac.compare_digest(ADMIN_TOKEN, given):
            return JSONResponse({'detail':'Write requires X-Lab-Token from .env'},status_code=403)
    return await call_next(request)



def db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("""CREATE TABLE IF NOT EXISTS http_requests(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL, source_ip TEXT, method TEXT, host TEXT,
      path TEXT, headers TEXT, body_b64 TEXT,
      response_status INTEGER, rule_name TEXT)""")
    research.initialize(conn)
    conn.commit()
    return conn


def rules() -> list[dict[str, Any]]:
    try:
        r = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    return r if isinstance(r, list) else []


def match_rule(method: str, host: str, path: str) -> dict[str, Any] | None:
    for rule in rules():
        if not isinstance(rule, dict) or not rule.get("enabled", True):
            continue
        match_method = str(rule.get("method", "*")).upper()
        match_host = str(rule.get("host", "*")).lower()
        if match_method not in ("*", method):
            continue
        if match_host not in ("*", host.split(":", 1)[0].lower()):
            continue
        try:
            if re.search(str(rule.get("path_regex", "^$")), path):
                return rule
        except re.error:
            continue
    return None


def observe(source_ip: str, method: str, host: str, path: str,
            headers: dict, body: bytes, response_status: int,
            rule_name: str | None) -> None:
    # Only retain 64 KB of each request body, avoiding runaway disk growth.
    encoded = base64.b64encode(body[:65536]).decode("ascii")
    # Header-level secret scrubbing; raw body capture remains opt-in lab research data.
    headers = {key: ('[REDACTED]' if key.lower() in
               ('authorization', 'proxy-authorization', 'cookie', 'set-cookie', 'x-api-key', 'x-lab-token')
               else value) for key, value in headers.items()}
    with LOCK:
        conn = db()
        try:
            conn.execute("""INSERT INTO http_requests
              (ts, source_ip, method, host, path, headers, body_b64, response_status, rule_name)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (datetime.now(timezone.utc).isoformat(), source_ip, method, host,
               path, json.dumps(headers), encoded, response_status, rule_name))
            conn.commit()
        finally:
            conn.close()


@app.get("/", include_in_schema=False)
async def dashboard(request: Request) -> Response:
    # Never show the research dashboard to devices using the public TLS edge.
    if request.headers.get("x-forwarded-proto") == "https":
        return await simulated_api("", request)
    return HTMLResponse(UI_PATH.read_text(encoding="utf-8"))


@app.get("/__lab__/health", operation_id="lab_health")
def health() -> dict:
    return {"status": "ok", "component": "device-re-lab", "mock_backend": True}


@app.get('/__lab__/profile',operation_id='lab_active_profile')
def active_profile() -> dict:
    """Read-only list of selectable device research profiles (no activation)."""
    selected=TARGET_PROFILE
    names=sorted(p.stem for p in PROFILE_DIR.glob('*.json') if re.fullmatch('[a-z0-9_-]{1,64}',p.stem))
    profile=None
    if selected in names:
        try:profile=json.loads((PROFILE_DIR/(selected+'.json')).read_text())
        except (ValueError,OSError):pass
    return {'active':selected,'profile':profile,'available':names,'automatic_dns_changes':False}


@app.get("/__lab__/events", operation_id="lab_events_list")
def events(limit: int = 100) -> dict:
    conn = db()
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM http_requests ORDER BY id DESC LIMIT ?",
            (min(max(limit, 1), 500),)).fetchall()
        return {"events": [dict(row) for row in rows]}
    finally:
        conn.close()


@app.delete("/__lab__/events", operation_id="lab_events_clear")
def clear_events() -> dict:
    with LOCK:
        conn = db()
        try:
            count = conn.execute("DELETE FROM http_requests").rowcount
            conn.commit()
        finally:
            conn.close()
    return {"deleted": count}


@app.get("/__lab__/rules", operation_id="lab_rules_list")
def get_rules() -> dict:
    return {"rules": rules()}


@app.put("/__lab__/rules", operation_id="lab_rules_replace")
async def put_rules(request: Request) -> dict:
    payload = await request.json()
    if not isinstance(payload, list) or len(payload) > 200:
        raise HTTPException(400, "Expected an array of up to 200 rules")
    for item in payload:
        if not isinstance(item, dict):
            raise HTTPException(400, "Each rule must be an object")
        try:
            re.compile(str(item.get("path_regex", "^$")))
        except re.error as exc:
            raise HTTPException(400, f"Invalid path_regex: {exc}") from exc
        if not 100 <= int(item.get("status", 501)) <= 599:
            raise HTTPException(400, "Rule status must be 100-599")
    RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    RULES_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"saved": len(payload)}


def adguard_call(endpoint: str, payload: dict | None = None) -> Any:
    """Use AdGuard Home's authenticated local management API."""
    url = ADGUARD_URL + "/control/" + endpoint
    credentials = base64.b64encode(f"{ADGUARD_USER}:{ADGUARD_PASSWORD}".encode()).decode()
    headers = {"Authorization": "Basic " + credentials}
    body = None
    if payload is not None:
        body = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, body, headers=headers, method="POST" if payload is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=5) as res:
            raw = res.read()
            return json.loads(raw) if raw else {}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        # Never leak credentials; report connection error only.
        raise HTTPException(502, f"AdGuard API unavailable: {type(exc).__name__}") from exc


def managed_dns() -> list[dict]:
    return research.read_json(OWNED_DNS_PATH, [])


def normalize_dns(hosts: str) -> list[dict]:
    if len(hosts)>65536: raise HTTPException(400,'DNS payload too large')
    desired={}
    for line in hosts.splitlines():
        line=line.strip()
        if not line or line.startswith('#'): continue
        parts=line.split()
        if len(parts)!=2: raise HTTPException(400,'Use one IP and hostname per line')
        try:
            addr=ipaddress.ip_address(parts[0])
            if addr.is_unspecified or addr.is_multicast: raise ValueError('Invalid destination')
        except ValueError as exc: raise HTTPException(400,'Invalid IP') from exc
        host=parts[1].lower().rstrip('.')
        if not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',host) or '..' in host:
            raise HTTPException(400,'Invalid hostname; wildcards are not allowed')
        desired[host]=str(addr)
    return [{'domain':d,'answer':a} for d,a in sorted(desired.items())]


def apply_managed_dns(desired: list[dict]) -> dict:
    # Only entries previously created by THIS lab may be deleted.
    existing=adguard_call('rewrite/list')
    if not isinstance(existing,list): raise HTTPException(502,'Invalid AdGuard response')
    all_rules={(e['domain'],e['answer']) for e in existing}
    prior={(e['domain'],e['answer']) for e in managed_dns()}
    new={(e['domain'],e['answer']) for e in desired}
    # Conflicting unrelated rewrite for the same hostname: refuse instead of overwriting it.
    unmanaged=all_rules-prior
    conflicts={d for d,a in unmanaged} & {d for d,a in new}
    if conflicts: raise HTTPException(409,f'Unmanaged DNS rewrite exists: {sorted(conflicts)}')
    for domain,answer in sorted(prior-new):
        if (domain,answer) in all_rules: adguard_call('rewrite/delete',{'domain':domain,'answer':answer})
    for domain,answer in sorted(new-all_rules):
        adguard_call('rewrite/add',{'domain':domain,'answer':answer})
    research.save_json(OWNED_DNS_PATH, desired)
    return {'saved':True,'managed_rewrites':len(desired),'unmanaged_preserved':len(unmanaged)}


@app.get('/__lab__/dns',operation_id='lab_dns_list')
def get_dns() -> dict:
    managed=managed_dns()
    all_items=adguard_call('rewrite/list')
    return {'hosts':''.join(f"{e['answer']} {e['domain']}\n" for e in managed),
            'rewrites':all_items,'managed':managed}


@app.put('/__lab__/dns',operation_id='lab_dns_replace')
async def put_dns(request: Request) -> dict:
    payload=await request.json()
    hosts=payload.get('hosts','') if isinstance(payload,dict) else ''
    if not isinstance(hosts,str):raise HTTPException(400,'Expected hosts string')
    return apply_managed_dns(normalize_dns(hosts))


@app.get('/__lab__/scenarios',operation_id='lab_scenarios_list')
def list_scenarios() -> dict:
    return {'scenarios':research.read_json(SCENARIOS_PATH,[])}


@app.put('/__lab__/scenarios',operation_id='lab_scenarios_replace')
async def replace_scenarios(request: Request) -> dict:
    content=await request.json()
    if not isinstance(content,list) or len(content)>40:raise HTTPException(400,'Expected <=40 scenarios')
    seen=set()
    for s in content:
        if not isinstance(s,dict) or not isinstance(s.get('id'),str) or not re.fullmatch('[A-Za-z0-9_-]{1,48}',s['id']) or s['id'] in seen:
            raise HTTPException(400,'Invalid/duplicate scenario id')
        seen.add(s['id'])
        if not isinstance(s.get('steps'),list) or len(s['steps'])>100:raise HTTPException(400,'Invalid steps')
        for step in s['steps']:
            if not isinstance(step,dict):raise HTTPException(400,'Invalid step')
            try:re.compile(step.get('path_regex','^$'))
            except re.error as exc:raise HTTPException(400,'Invalid regex') from exc
            status=int(step.get('status',200))
            if status<100 or status>599:raise HTTPException(400,'Invalid HTTP status')
    research.save_json(SCENARIOS_PATH,content)
    return {'saved':len(content)}


@app.post('/__lab__/scenarios/reset',operation_id='lab_scenarios_reset')
async def reset_scenarios(request:Request) -> dict:
    payload=await request.json()
    with db() as conn:
        count=research.reset_scenarios(conn,payload.get('session_key'))
    return {'reset':count}


@app.get('/__lab__/experiments',operation_id='device_experiments_list')
def experiments_list() -> dict:
    with db() as conn:return {'experiments':research.list_experiments(conn)}


@app.post('/__lab__/experiments',operation_id='device_start_experiment')
async def experiment_begin(request:Request) -> dict:
    data=await request.json()
    snapshot={'profile':TARGET_PROFILE,'rules':rules(),'scenarios':research.read_json(SCENARIOS_PATH,[]),'managed_dns':managed_dns()}
    with db() as conn:
        try:return research.begin(conn,data.get('name',''),data.get('hypothesis',''),snapshot)
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc


@app.post('/__lab__/experiments/{eid}/finish',operation_id='device_finish_experiment')
async def experiment_finish(eid:str,request:Request)->dict:
    payload=await request.json()
    with db() as conn:
        try:return research.finish(conn,eid,str(payload.get('result',''))[:4000])
        except (KeyError,ValueError) as exc:raise HTTPException(400,str(exc)) from exc


@app.get('/__lab__/experiments/{eid}',operation_id='device_experiment_details')
def experiment_detail(eid:str)->dict:
    with db() as conn:
        try:return research.get_experiment(conn,eid)
        except KeyError:raise HTTPException(404,'Experiment not found')


@app.get('/__lab__/compare',operation_id='device_compare_experiments')
def compare(a:str,b:str)->dict:
    with db() as conn:
        try:return research.compare_experiments(conn,a,b)
        except KeyError:raise HTTPException(404,'Experiment not found')


@app.post('/__lab__/experiments/{eid}/rollback',operation_id='device_rollback_experiment')
def experiment_rollback(eid:str)->dict:
    with db() as conn:
        try:old=research.get_experiment(conn,eid)
        except KeyError:raise HTTPException(404,'Experiment not found')
    snap=old['snapshot']
    # Apply DNS before modifying mock settings; on DNS conflict, leave other settings untouched.
    changes=apply_managed_dns(snap['managed_dns'])
    research.save_json(RULES_PATH,snap['rules'])
    research.save_json(SCENARIOS_PATH,snap['scenarios'])
    with db() as conn:
        research.reset_scenarios(conn)
    return {'restored_experiment':eid,**changes}


@app.get('/__lab__/analyses',operation_id='device_analyses_list')
def analyses_list()->dict:
    items=[]
    for p in sorted(ANALYSIS_PATH.glob('*/summary.json'))[-100:]:
        try:items.append(json.loads(p.read_text()))
        except (ValueError,OSError):continue
    return {'analyses':items}


@app.get('/__lab__/analyses/compare',operation_id='device_compare_pcaps')
def compare_analyses(a:str,b:str)->dict:
    if not re.fullmatch(r'[a-f0-9]{16}',a) or not re.fullmatch(r'[a-f0-9]{16}',b):
        raise HTTPException(400,'Expected analysis IDs')
    left=research.read_json(ANALYSIS_PATH/a/'summary.json',None)
    right=research.read_json(ANALYSIS_PATH/b/'summary.json',None)
    if not left or not right:raise HTTPException(404,'Analysis not found')
    old=left['protocol_sample'];new=right['protocol_sample']
    return {'before':a,'after':b,'new_protocols':{k:v for k,v in new.items() if k not in old},
            'removed_protocols':{k:v for k,v in old.items() if k not in new},
            'count_deltas':{k:new.get(k,0)-old.get(k,0) for k in new.keys()|old.keys()},
            'new_zeek_records':{k:right['zeek_records'].get(k,0)-left['zeek_records'].get(k,0) for k in right['zeek_records'].keys()|left['zeek_records'].keys()}}


@app.get('/__lab__/firmware',operation_id='device_firmware_list')
def firmware_list()->dict:
    FIRMWARE_PATH.mkdir(parents=True,exist_ok=True)
    return {'files':[{'name':f.name,'size':f.stat().st_size} for f in FIRMWARE_PATH.iterdir() if f.is_file()]}


@app.get('/__lab__/firmware/{filename}',operation_id='device_firmware_index')
def firmware_scan(filename:str)->dict:
    try:return research.firmware_index(FIRMWARE_PATH/filename,FIRMWARE_PATH)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc


@app.get('/__lab__/replay/{event_id}',operation_id='device_dry_run_replay')
def dry_run_replay(event_id:int)->dict:
    """Offline replay of rule matching, does not send traffic to third-party servers."""
    conn=db()
    try:
        row=conn.execute('SELECT method,host,path FROM http_requests WHERE id=?',(event_id,)).fetchone()
    finally:conn.close()
    if row is None:raise HTTPException(404,'Event not found')
    r=match_rule(*row)
    return {'event_id':event_id,'current_matching_rule':r.get('name') if r else None,
            'status':int(r.get('status',200)) if r else 501,'dry_run':True}


# The MCP handler must be registered BEFORE the catch-all simulator, otherwise
# FastAPI's first-match routing would turn /mcp into an HTTP 501 mock endpoint.
# Only explicit read-only operations are exposed via MCP. Mutations use token-guarded REST.
lab_mcp = FastApiMCP(
    app, name="Device lab emulator",
    include_operations=[
        "lab_health", "lab_active_profile", "lab_events_list", "lab_rules_list", "lab_dns_list",
        "lab_scenarios_list", "device_experiments_list", "device_experiment_details",
        "device_compare_experiments", "device_analyses_list", "device_compare_pcaps",
        "device_firmware_list", "device_firmware_index", "device_dry_run_replay",
    ],
)
lab_mcp.mount_http(mount_path="/mcp")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def simulated_api(path: str, request: Request) -> Response:
    method = request.method.upper()
    host = request.headers.get("host", "")
    route = "/" + path
    if request.url.query:
        route += "?" + request.url.query
    body = await request.body()
    source_ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
    with db() as conn:
        rule=research.scenario_match(conn,research.read_json(SCENARIOS_PATH,[]),method,host,route,source_ip)
    if rule is None:
        rule = match_rule(method, host, route)
    if rule is None:
        code = 501
        result = {"lab_status": "unimplemented", "message": "No response rule matched",
                  "host": host, "method": method, "path": route}
        content = json.dumps(result).encode("utf-8")
        headers = {"content-type": "application/json"}
        rule_name = None
    else:
        code = int(rule.get("status", 200))
        await asyncio.sleep(min(max(int(rule.get('delay_ms',0)),0),5000)/1000)
        raw = rule.get("body", "")
        content = (raw if isinstance(raw, str) else json.dumps(raw)).encode("utf-8")
        headers = {str(k): str(v) for k, v in rule.get("headers", {}).items()}
        headers.setdefault("content-type", "application/json")
        rule_name = str(rule.get("name", "unnamed"))
    forwarded_ip = request.headers.get("x-real-ip")
    source_ip = forwarded_ip or (request.client.host if request.client else "unknown")
    observe(source_ip, method, host, route, dict(request.headers), body, code, rule_name)
    return Response(content=content, status_code=code, headers=headers)
