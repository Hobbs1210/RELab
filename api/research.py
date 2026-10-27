"""Offline research store: deterministic experiment history and a stateful API emulator.
No external network calls, device writes or host command execution.
"""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text('utf8'))
    except FileNotFoundError:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf8')
    tmp.replace(path)


def initialize(conn: sqlite3.Connection) -> None:
    conn.execute('''CREATE TABLE IF NOT EXISTS experiments(
      id TEXT PRIMARY KEY, name TEXT NOT NULL, hypothesis TEXT NOT NULL,
      created_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
      baseline_event_id INTEGER NOT NULL, snapshot_json TEXT NOT NULL,
      result TEXT DEFAULT '', approved INTEGER DEFAULT 0)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS scenario_state(
      session_key TEXT PRIMARY KEY, scenario_id TEXT NOT NULL, position INTEGER NOT NULL,
      updated_at TEXT NOT NULL)''')
    conn.commit()


def begin(conn: sqlite3.Connection, name: str, hypothesis: str, snapshot: dict) -> dict:
    if not name.strip() or len(name) > 120 or len(hypothesis) > 4000:
        raise ValueError('Invalid name/hypothesis length')
    initialize(conn)
    experiment_id = uuid.uuid4().hex[:12]
    base = conn.execute('SELECT COALESCE(MAX(id),0) FROM http_requests').fetchone()[0]
    conn.execute('INSERT INTO experiments(id,name,hypothesis,created_at,status,baseline_event_id,snapshot_json) '
                 'VALUES(?,?,?,?,?,?,?)', (experiment_id,name,hypothesis,utc(),'running',base,json.dumps(snapshot)))
    conn.commit()
    return {'id':experiment_id,'name':name,'baseline_event_id':base,'status':'running'}


def get_experiment(conn: sqlite3.Connection, eid: str) -> dict:
    conn.row_factory=sqlite3.Row
    row=conn.execute('SELECT * FROM experiments WHERE id=?',(eid,)).fetchone()
    if row is None: raise KeyError(eid)
    obj=dict(row)
    obj['snapshot']=json.loads(obj.pop('snapshot_json'))
    return obj


def list_experiments(conn: sqlite3.Connection, limit: int=50) -> list[dict]:
    initialize(conn)
    conn.row_factory=sqlite3.Row
    return [dict(r) for r in conn.execute('SELECT id,name,hypothesis,created_at,finished_at,status,baseline_event_id,result FROM experiments ORDER BY created_at DESC LIMIT ?', (max(1,min(limit,200)),))]


def finish(conn: sqlite3.Connection, eid: str, result: str) -> dict:
    obj=get_experiment(conn,eid)
    if obj['status']!='running': raise ValueError('Experiment not running')
    end=conn.execute('SELECT COALESCE(MAX(id),0) FROM http_requests').fetchone()[0]
    rows=conn.execute('SELECT host,path,response_status,rule_name FROM http_requests WHERE id>? AND id<=?',(obj['baseline_event_id'],end)).fetchall()
    signatures=[dict(host=r[0],path=r[1],status=r[2],rule=r[3]) for r in rows]
    conn.execute('UPDATE experiments SET finished_at=?,status=?,result=? WHERE id=?', (utc(),'finished',result,eid))
    conn.commit()
    return {'id':eid,'status':'finished','event_count':len(rows),'last_event_id':end,'observed':signatures[:100]}


def compare_experiments(conn: sqlite3.Connection, a: str, b: str) -> dict:
    left=get_experiment(conn,a)
    right=get_experiment(conn,b)
    def signatures(exp):
        end=conn.execute('SELECT COALESCE(MIN(baseline_event_id), (SELECT COALESCE(MAX(id),0) FROM http_requests)) FROM experiments WHERE created_at>?',(exp['created_at'],)).fetchone()[0]
        rows=conn.execute('SELECT method,host,path,response_status,COUNT(*) FROM http_requests WHERE id>? AND id<=? GROUP BY 1,2,3,4', (exp['baseline_event_id'],end)).fetchall()
        return {f'{r[0]} {r[1]}{r[2]} => {r[3]}':r[4] for r in rows}
    l,r=signatures(left),signatures(right)
    return {'baseline':a,'candidate':b,'new':{k:v for k,v in r.items() if k not in l},'missing':{k:v for k,v in l.items() if k not in r},'changed_counts':{k:[l[k],r[k]] for k in l.keys()&r.keys() if l[k]!=r[k]}}


def scenario_match(conn: sqlite3.Connection, scenarios: list[dict], method: str, host: str, path: str, source_ip: str):
    """One active ordered scenario per source IP; only advances on exact step match.
    Mock responses are hypotheses, not verified descriptions of any vendor protocol.
    """
    initialize(conn)
    key=source_ip
    active=conn.execute('SELECT scenario_id,position FROM scenario_state WHERE session_key=?',(key,)).fetchone()
    candidates = [s for s in scenarios if s.get('enabled') and s.get('steps')]
    if active:
        candidates = [s for s in candidates if s.get('id')==active[0]]
    for scenario in candidates:
        idx=active[1] if active else 0
        steps=scenario.get('steps',[])
        if idx>=len(steps): continue
        step=steps[idx]
        if step.get('method','*').upper() not in ('*',method): continue
        if step.get('host','*').lower() not in ('*',host.split(':')[0].lower()): continue
        if not re.search(step.get('path_regex','^$'),path): continue
        conn.execute('INSERT OR REPLACE INTO scenario_state(session_key,scenario_id,position,updated_at) VALUES(?,?,?,?)', (key,scenario['id'],idx+1,utc()))
        conn.commit()
        return {'name':f"scenario:{scenario['id']}:{idx+1}",**step}
    return None


def reset_scenarios(conn: sqlite3.Connection, session_key: str | None=None) -> int:
    initialize(conn)
    if session_key:
        cur=conn.execute('DELETE FROM scenario_state WHERE session_key=?',(session_key,))
    else:
        cur=conn.execute('DELETE FROM scenario_state')
    conn.commit()
    return cur.rowcount


def firmware_index(path: Path, root: Path, limit=150) -> dict:
    """String extraction without executing firmware. Resolve filenames inside read-only input dir."""
    root=root.resolve()
    path=path.resolve()
    if not path.is_file() or not path.is_relative_to(root): raise ValueError('File outside firmware input directory')
    if path.stat().st_size > 150*1024*1024: raise ValueError('Firmware input exceeds 150MB')
    import re
    data=path.read_bytes()
    lines=re.findall(rb'[\x20-\x7e]{5,}',data)
    keys=(b'http',b'api',b'hostname',b'url',b'certificate',b'trust',b'auth',b'grpc',b'protobuf',b'webrtc',b'stun',b'mqtt',b'coap',b'bluetooth',b'pair',b'ble',b'tls',b'dns')
    hits=[s[:200].decode('ascii','replace') for s in lines if any(k in s.lower() for k in keys)]
    return {'file':path.name,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'strings_total':len(lines),'interesting':hits[:limit], 'truncated':len(hits)>limit}
