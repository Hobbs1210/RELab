"""Read-only import of existing lab HTTP request journal and Zeek JSON logs into evidence."""
from __future__ import annotations
import hashlib,json,os,sqlite3
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import select
from research_models import Evidence,Relationship
import research_core as core
INPUT=Path(os.environ.get('RESEARCH_INPUTS','/inputs'))

def already(s,ref):return s.scalar(select(Evidence.id).where(Evidence.project_id=='default',Evidence.external_ref==ref)) is not None

def emit_observation(s,ref,kind,summary,fields,when,source):
    if already(s,ref):return False
    e=core.evidence(s,'default',kind,summary,fields=fields,confidence=1,observed_at=when,clock_source=source,external_ref=ref)
    host=fields.get('host') or fields.get('query') or fields.get('server_name')
    client=fields.get('source_ip')
    if host and client:
        s.add(Relationship(project_id='default',from_type='device-ip',from_id=str(client)[:120],relation='contacts',to_type='endpoint',to_id=str(host)[:120],evidence_id=e['id']))
    return True

def http_events(s,cap=100):
    source=INPUT/'api'/'requests.db'
    if not source.is_file():return 0
    try:
        with sqlite3.connect(f'file:{source}?mode=ro',uri=True,timeout=2) as conn:
            # Old database may be older than current expected columns; fail isolated.
            rows=conn.execute('SELECT id,ts,source_ip,method,host,path,response_status FROM http_requests ORDER BY id DESC LIMIT ?', (cap,)).fetchall()
    except (sqlite3.Error,OSError):return 0
    count=0
    for row in rows:
        id,ts,ip,method,host,path,status=row
        path=str(path or '').split('?',1)[0][:180] # Avoid query-string secrets.
        ref=f'http:{id}'
        try:dt=datetime.fromisoformat(str(ts).replace('Z','+00:00'))
        except ValueError:dt=datetime.now(timezone.utc)
        count+=emit_observation(s,ref,'http',f'{method} {host}{path}',{'host':str(host)[:120], 'source_ip':str(ip)[:80],
            'method':str(method)[:10],'path':path,'status':status},dt,'api')
    return count

def zeek_events(s,cap=150):
    base=INPUT/'analysis';count=0
    if not base.is_dir():return 0
    # Limit per loop, enumerate predictable known Zeek JSON output names.
    for file in sorted(base.glob('*/dns.log'),reverse=True)[:10]+sorted(base.glob('*/ssl.log'),reverse=True)[:10]+sorted(base.glob('*/conn.log'),reverse=True)[:10]:
        if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(base.resolve()) or file.stat().st_size>100*1024*1024:continue
        # Zeek logs can use TSV and JSON; only structured JSON lines are accepted.
        with file.open('rb') as f:
            for line_no,line in enumerate(f):
                if line_no>=cap or len(line)>12000:break
                try:v=json.loads(line)
                except (ValueError,UnicodeDecodeError):continue
                if not isinstance(v,dict):continue
                kind=file.stem
                ref='zeek:'+str(file.parent.name)+':'+kind+':'+str(line_no)
                client=v.get('id.orig_h','')
                host=v.get('query',v.get('server_name',v.get('id.resp_h','')))
                try:dt=datetime.fromtimestamp(float(v.get('ts',0)),timezone.utc)
                except (ValueError,TypeError,OverflowError):continue
                fields={'source_ip':str(client)[:80],'host':str(host)[:120],
                        'dest_ip':str(v.get('id.resp_h',''))[:80], 'transport':str(v.get('proto',''))[:20]}
                count+=emit_observation(s,ref,kind,f'{kind}: {client} -> {host}',fields,dt,'zeek')
    return count

def ingest(s):return {'http':http_events(s),'zeek':zeek_events(s)}
