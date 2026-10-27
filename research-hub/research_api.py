"""Device RE Lab integrated research API: only local trusted clients; mutations token-protected."""
from __future__ import annotations
import hmac,json,os,uuid,re
from contextlib import asynccontextmanager
from datetime import datetime,timezone,timedelta
from pathlib import Path
from fastapi import FastAPI,HTTPException,Request,Depends
from fastapi.responses import HTMLResponse,FileResponse,PlainTextResponse,JSONResponse
from sqlalchemy import select,func
import research_models as models
from research_models import Project,Device,Artifact,ProjectArtifact,Evidence,Relationship,Event,Job,Experiment,Approval,ClockOffset,AgentMemory,now
import research_core as core

TOKEN=os.environ.get('LAB_ADMIN_TOKEN','')

def session():
    if models.Session is None:models.configure()
    with models.Session() as s:yield s

@asynccontextmanager
async def lifespan(app):
    models.configure()
    yield

app=FastAPI(title='Device RE Lab Research Hub',version='0.4.0',lifespan=lifespan)

@app.middleware('http')
async def write_auth(request:Request,call_next):
    if request.url.path.startswith('/v1/') and request.method not in ('GET','HEAD','OPTIONS'):
        if not TOKEN or not hmac.compare_digest(TOKEN,request.headers.get('X-Lab-Token','')):
            return JSONResponse({'detail':'Write action requires X-Lab-Token'},status_code=403)
    return await call_next(request)

def ok(fn):
    try:return fn()
    except (ValueError,KeyError,TypeError,OverflowError) as e:raise HTTPException(400,str(e)) from e

def serialize(obj):
    d={k:v for k,v in vars(obj).items() if not k.startswith('_')}
    for k,v in d.items():
        if isinstance(v,datetime):d[k]=v.isoformat()
        if k in ('fields','locator','identity','body','params','result','evidence_ids'):
            try:d[k]=json.loads(v)
            except (TypeError,ValueError):pass
    return d

def parse_time(v):
    if not v:return now()
    when=datetime.fromisoformat(v.replace('Z','+00:00'))
    if when.tzinfo is None:raise ValueError('Timestamp needs an explicit time zone')
    return when

@app.get('/',include_in_schema=False)
def home():return HTMLResponse(Path(__file__).with_name('ui.html').read_text())

@app.get('/v1/health',operation_id='research_health')
def health():return {'status':'ok','service':'research-hub','database':os.getenv('RESEARCH_DATABASE_URL','sqlite').split(':',1)[0],
                     'jobs':'durable database queue','agent_tools':'read-only by default'}

@app.get('/v1/projects',operation_id='research_list_projects')
def projects(s=Depends(session)):
    return {'projects':[serialize(x) for x in s.scalars(select(Project).order_by(Project.id).limit(200))]}

@app.post('/v1/projects')
async def project_add(request:Request,s=Depends(session)):
    v=await request.json()
    r=ok(lambda:core.create_project(s,v['id'],v['name'],v.get('description','')))
    s.commit();return r

@app.get('/v1/devices',operation_id='research_list_devices')
def devices(project_id:str='default',s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    return {'devices':[serialize(x) for x in s.scalars(select(Device).where(Device.project_id==project_id).limit(200))]}

@app.post('/v1/devices')
async def device_add(request:Request,s=Depends(session)):
    v=await request.json();r=ok(lambda:core.register_device(s,v['project_id'],v['id'],v['name'],v.get('kind','unknown'),v.get('identity')))
    s.commit();return r

@app.get('/v1/artifacts',operation_id='research_list_artifacts')
def artifacts(project_id:str='default',s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    links=s.scalars(select(ProjectArtifact).where(ProjectArtifact.project_id==project_id).limit(500)).all()
    result=[]
    for link in links:
        a=s.get(Artifact,link.artifact_id)
        if a:result.append({**serialize(a),'device_id':link.device_id})
    return {'artifacts':result}

@app.post('/v1/artifacts/import')
async def artifacts_import(request:Request,s=Depends(session)):
    v=await request.json()
    r=ok(lambda:core.import_file(s,v.get('project_id','default'),v['kind'],v['filename'],v.get('device_id')))
    s.commit();return r

@app.post('/v1/evidence')
async def record_evidence(request:Request,s=Depends(session)):
    v=await request.json()
    def perform():return core.evidence(s,v.get('project_id','default'),v['kind'],v['summary'],fields=v.get('fields'),
        artifact_id=v.get('artifact_id'),device_id=v.get('device_id'),locator=v.get('locator'),
        confidence=v.get('confidence',1),observed_at=parse_time(v.get('observed_at')),
        clock_source=v.get('clock_source','server'))
    r=ok(perform);s.commit();return r

@app.get('/v1/evidence',operation_id='research_search_evidence')
def evidence(project_id:str='default',q:str='',kind:str='',limit:int=100,s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    if len(q)>200:raise HTTPException(400,'Search too long')
    stmt=select(Evidence).where(Evidence.project_id==project_id)
    if kind:stmt=stmt.where(Evidence.kind==kind)
    if q:stmt=stmt.where(Evidence.summary.ilike('%'+q.replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
    rows=s.scalars(stmt.order_by(Evidence.id.desc()).limit(max(1,min(limit,500)))).all()
    return {'evidence':[serialize(x) for x in rows]}

@app.post('/v1/relationships')
async def relationship_add(request:Request,s=Depends(session)):
    v=await request.json();p=v.get('project_id','default')
    def perform():
        core.require_project(s,p)
        if v.get('evidence_id'):
            e=s.get(Evidence,int(v['evidence_id']))
            if not e or e.project_id!=p:raise ValueError('Evidence must belong to project')
        r=Relationship(project_id=p,from_type=str(v['from_type'])[:40],from_id=str(v['from_id'])[:120],
                       to_type=str(v['to_type'])[:40],to_id=str(v['to_id'])[:120],relation=str(v['relation'])[:40],
                       evidence_id=v.get('evidence_id'))
        s.add(r);s.flush();core.emit(s,p,'relationship.recorded',{'id':r.id});return {'id':r.id}
    r=ok(perform);s.commit();return r

@app.get('/v1/topology',operation_id='research_device_topology')
def topology(project_id:str='default',s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    return core.topology(s,project_id,{})

@app.get('/v1/timeline',operation_id='research_evidence_timeline')
def timeline(project_id:str='default',limit:int=100,s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    offsets={}
    for off in s.scalars(select(ClockOffset).where(ClockOffset.project_id==project_id).order_by(ClockOffset.id)):
        offsets[off.source]=off
    records=s.scalars(select(Evidence).where(Evidence.project_id==project_id).order_by(Evidence.observed_at.desc()).limit(max(1,min(limit,500)))).all()
    result=[]
    for x in records:
        entry=serialize(x);off=offsets.get(x.clock_source)
        dt=x.observed_at
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        dt=dt+timedelta(milliseconds=off.offset_ms if off else 0)
        entry['normalized_time']=dt.isoformat()
        entry['clock_uncertainty_ms']=off.uncertainty_ms if off else None
        result.append(entry)
    result.sort(key=lambda r:r['normalized_time'])
    return {'events':result,'uncalibrated_clocks':[x['clock_source'] for x in result if x['clock_uncertainty_ms'] is None and x['clock_source']!='server']}

@app.post('/v1/clocks')
async def clock_offset(request:Request,s=Depends(session)):
    v=await request.json();p=v.get('project_id','default')
    def perform():
        core.require_project(s,p)
        offset=float(v['offset_ms']);uncertainty=float(v['uncertainty_ms'])
        if not -86_400_000<=offset<=86_400_000 or not 0<=uncertainty<=86_400_000:raise ValueError('Invalid clock calibration')
        o=ClockOffset(project_id=p,source=core.slug(v['source']),offset_ms=offset,uncertainty_ms=uncertainty)
        s.add(o);core.emit(s,p,'clock.calibrated',{'source':o.source,'offset_ms':offset,'uncertainty_ms':uncertainty})
        return {'source':o.source,'offset_ms':offset,'uncertainty_ms':uncertainty}
    r=ok(perform);s.commit();return r

@app.get('/v1/jobs',operation_id='research_list_jobs')
def jobs(project_id:str='default',limit:int=100,s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    return {'jobs':[serialize(x) for x in s.scalars(select(Job).where(Job.project_id==project_id).order_by(Job.created.desc()).limit(max(1,min(limit,200))))]}

@app.get('/v1/jobs/{job_id}',operation_id='research_job_status')
def job_status(job_id:str,s=Depends(session)):
    x=s.get(Job,job_id)
    if x is None:raise HTTPException(404,'Job not found')
    return serialize(x)

@app.post('/v1/jobs')
async def add_job(request:Request,s=Depends(session)):
    v=await request.json();r=ok(lambda:core.enqueue(s,v.get('project_id','default'),v['kind'],v.get('params')))
    s.commit();return r

@app.post('/v1/jobs/{job_id}/cancel')
def cancel_job(job_id:str,s=Depends(session)):
    x=s.get(Job,job_id)
    if not x:raise HTTPException(404,'Unknown job')
    if x.status not in ('queued','retry'):raise HTTPException(409,'Only pending jobs can be cancelled')
    x.status='cancelled';x.updated=now();core.emit(s,x.project_id,'job.cancelled',{'id':x.id});s.commit();return {'id':x.id,'status':x.status}

@app.get('/v1/recipes',operation_id='research_list_recipes')
def recipes():return {'recipes':core.RECIPES,'execution':'queued persistent jobs; handlers do not contact unknown devices'}

@app.get('/v1/events',operation_id='research_recent_events')
def events(project_id:str='default',limit:int=100,s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    return {'events':[serialize(x) for x in s.scalars(select(Event).where(Event.project_id==project_id).order_by(Event.id.desc()).limit(max(1,min(limit,200))))]}

@app.get('/v1/memory',operation_id='research_search_agent_memory')
def memories(project_id:str='default',q:str='',s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    if len(q)>120:raise HTTPException(400,'Search too long')
    stmt=select(AgentMemory).where(AgentMemory.project_id==project_id)
    if q:stmt=stmt.where(AgentMemory.text.ilike('%'+q.replace('%','\\%').replace('_','\\_')+'%',escape='\\'))
    return {'memories':[serialize(x) for x in s.scalars(stmt.order_by(AgentMemory.id.desc()).limit(100))]}

@app.post('/v1/memory')
async def add_memory(request:Request,s=Depends(session)):
    v=await request.json();p=v.get('project_id','default')
    def perform():
        core.require_project(s,p)
        ids=v.get('evidence_ids',[])
        if not isinstance(ids,list) or len(ids)>50:raise ValueError('Invalid evidence ids')
        for i in ids:
            e=s.get(Evidence,int(i))
            if not e or e.project_id!=p:raise ValueError('Cross-project evidence is prohibited')
        status=v.get('status','hypothesis')
        if status not in ('hypothesis','observed','verified','refuted'):raise ValueError('Invalid status')
        m=AgentMemory(project_id=p,text=str(v['text'])[:3000],evidence_ids=core.j(ids),status=status)
        s.add(m);s.flush();core.emit(s,p,'agent.memory.recorded',{'id':m.id,'status':status});return {'id':m.id,'status':status}
    r=ok(perform);s.commit();return r

@app.post('/v1/approvals')
async def propose_approval(request:Request,s=Depends(session)):
    v=await request.json();p=v.get('project_id','default')
    def perform():
        core.require_project(s,p)
        # Approval is recorded but NOT delegated to shell/Docker/DNS or physical hardware.
        if v.get('action') not in ('emulator-state-reset','experiment-restore','promote-hypothesis'):
            raise ValueError('Only allowlisted local research actions can be approved here')
        a=Approval(id=str(uuid.uuid4()),project_id=p,action=v['action'],params=core.j(v.get('params',{})))
        s.add(a);core.emit(s,p,'approval.requested',{'id':a.id,'action':a.action});return {'id':a.id,'status':'pending'}
    r=ok(perform);s.commit();return r

@app.post('/v1/approvals/{id}/decision')
async def decision(id:str,request:Request,s=Depends(session)):
    v=await request.json();a=s.get(Approval,id)
    if a is None:raise HTTPException(404,'Unknown approval')
    if a.status!='pending':raise HTTPException(409,'Approval already decided')
    if v.get('decision') not in ('approved','denied'):raise HTTPException(400,'Invalid decision')
    a.status=v['decision'];a.decision_at=now();core.emit(s,a.project_id,'approval.decided',{'id':id,'decision':a.status})
    s.commit();return {'id':id,'status':a.status,'executed':False}

@app.get('/v1/experiments',operation_id='research_list_experiments')
def experiments(project_id:str='default',s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    return {'experiments':[serialize(x) for x in s.scalars(select(Experiment).where(Experiment.project_id==project_id).order_by(Experiment.created.desc()).limit(200))]}

@app.post('/v1/experiments')
async def experiment_add(request:Request,s=Depends(session)):
    v=await request.json();p=v.get('project_id','default')
    def perform():
        core.require_project(s,p)
        kind=v.get('kind')
        if kind not in ('replay','emulator-test','mutate'):
            raise ValueError('Reproducible experiments run offline replay, emulator-test or mutate only')
        params=v.get('params',{})
        if len(core.j(params))>16000:raise ValueError('Experiment too large')
        x=Experiment(id=str(uuid.uuid4()),project_id=p,kind=kind,params=core.j(params),name=str(v.get('name',kind))[:120])
        s.add(x);core.emit(s,p,'experiment.created',{'id':x.id,'kind':kind})
        return {'id':x.id,'kind':kind,'immutable_input_snapshot':True}
    r=ok(perform);s.commit();return r

@app.post('/v1/experiments/{id}/reproduce')
def experiment_reproduce(id:str,s=Depends(session)):
    x=s.get(Experiment,id)
    if not x:raise HTTPException(404,'Unknown experiment')
    r=ok(lambda:core.enqueue(s,x.project_id,x.kind,core.parsed(x.params)))
    x.last_job=r['id'];core.emit(s,x.project_id,'experiment.reproduced',{'experiment':id,'job':r['id']})
    s.commit();return {'experiment':id,**r,'execution':'offline (no network or physical device)'}

@app.post('/v1/experiments/{id}/restore')
def experiment_restore(id:str,s=Depends(session)):
    x=s.get(Experiment,id)
    if not x:raise HTTPException(404,'Unknown experiment')
    # No persistent virtual device state: reproduction starts from this immutable snapshot.
    core.emit(s,x.project_id,'experiment.restored',{'id':id,'scope':'offline snapshot only'})
    s.commit()
    return {'experiment':id,'restored':'offline simulation initial state','physical_device_changed':False,
            'dns_rules_changed':False}

@app.get('/v1/plans',operation_id='research_research_plan')
def plan(project_id:str='default',s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    artifacts=s.scalars(select(ProjectArtifact).where(ProjectArtifact.project_id==project_id).limit(100)).all()
    found={s.get(Artifact,x.artifact_id).type for x in artifacts if s.get(Artifact,x.artifact_id)}
    has_evidence=s.scalar(select(func.count(Evidence.id)).where(Evidence.project_id==project_id)) or 0
    steps=[]
    if not artifacts:steps.append({'step':'import','reason':'No linked artifacts yet','requires_approval':True})
    if 'firmware' in found:steps.append({'step':'firmware-intelligence','reason':'Firmware import available for metadata scan','requires_approval':False})
    if has_evidence:
        steps += [{'step':'correlate','reason':'Cross-reference captured evidence and firmware strings','requires_approval':False},
                  {'step':'protocol-state','reason':'Generate candidate temporal transitions','requires_approval':False},
                  {'step':'report','reason':'Export cited findings','requires_approval':False}]
    else:steps.append({'step':'capture-or-import','reason':'No evidence recorded; observe an authorized device first','requires_approval':True})
    return {'project_id':project_id,'steps':steps,'planner':'deterministic evidence-based suggestions, not autonomous AI'}

@app.get('/v1/mcp/health',operation_id='research_mcp_last_handshake')
def mcp_health():
    p=core.ROOT/'mcp-health.json'
    if not p.is_file():return {'status':'unverified','detail':'Run scripts/check-mcp.py --json-out data/research/mcp-health.json'}
    try:return json.loads(p.read_text())
    except (OSError,ValueError):return {'status':'invalid-report'}

@app.get('/v1/approvals',operation_id='research_list_approvals')
def approvals(project_id:str='default',s=Depends(session)):
    ok(lambda:core.require_project(s,project_id))
    return {'approvals':[serialize(x) for x in s.scalars(select(Approval).where(Approval.project_id==project_id).order_by(Approval.created.desc()).limit(100))]}

@app.get('/v1/capabilities',operation_id='research_capability_registry')
def capabilities():
    return {'integrations':{'capture':'external tcpdump/Zeek and imported PCAP','firmware':'import + bounded inspection; Ghidra/Binwalk optional',
                            'protocol':'inference, candidate KSY/Lua/SDK, offline replay','hardware':'inventory/observations; physical tests require adapter',
                            'mcp':'read-only research APIs; third-party services separately configured'},
            'jobs':sorted(core.VALID_JOBS),'recipes':sorted(core.RECIPES),'mcp_handshakes':'not tested by this endpoint'}

@app.get('/v1/metrics',operation_id='research_operational_metrics')
def metrics(s=Depends(session)):
    jobs=s.execute(select(Job.status,func.count()).group_by(Job.status)).all()
    events=s.scalar(select(func.count(Event.id))) or 0
    return {'jobs':dict(jobs),'event_count':events,'pending_nats_delivery':s.scalar(select(func.count(Event.id)).where(Event.delivered==False)) or 0}

@app.get('/v1/exports/{name}')
def download_export(name:str):
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,60}-[a-f0-9]{10}\.zip',name):raise HTTPException(400,'Invalid export filename')
    root=core.ROOT/'exports';path=root/name
    if not path.is_file() or path.is_symlink():raise HTTPException(404,'Export missing')
    return FileResponse(path,media_type='application/zip',filename=name)

# A single coherent MCP connection for Codex and Antigravity. Deliberately read-only.
from fastapi_mcp import FastApiMCP
hub_mcp=FastApiMCP(app,name='Device RE Lab Research Hub',include_operations=[
    'research_health','research_list_projects','research_list_devices','research_list_artifacts',
    'research_search_evidence','research_device_topology','research_evidence_timeline',
    'research_list_jobs','research_job_status','research_list_recipes','research_recent_events',
    'research_search_agent_memory','research_list_approvals','research_list_experiments','research_research_plan','research_mcp_last_handshake',
    'research_capability_registry','research_operational_metrics'])
hub_mcp.mount_http(mount_path='/mcp')
