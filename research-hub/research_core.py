"""Bounded, evidence-centric operations, no arbitrary shell execution/network targets."""
from __future__ import annotations
import hashlib,json,os,re,shutil,uuid,zipfile,io
from urllib.parse import urlsplit
from pathlib import Path
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,or_
from research_models import Project,Device,Artifact,ProjectArtifact,Evidence,Relationship,Event,Job,Approval,ClockOffset,AgentMemory,now

ROOT=Path(os.environ.get('RESEARCH_ARTIFACTS','/research')).resolve()
INPUT=Path(os.environ.get('RESEARCH_INPUTS','/inputs')).resolve()
VALID_TYPES={'firmware','pcap','mobile-log','serial-log','ble-log','protocol','other'}
VALID_JOBS={'firmware-intelligence','protocol-state','correlate','report','kaitai','dissector','sdk','emulator-test','replay','mutate','bundle','recipe','mobile-analyze','topology'}
RECIPES={'firmware-intelligence':['firmware-intelligence','correlate','report'],
         'protocol-research':['protocol-state','correlate','kaitai','dissector','sdk','report'],
         'session-replay':['replay','emulator-test','report'],
         'full-research':['firmware-intelligence','mobile-analyze','protocol-state','correlate','topology','kaitai','dissector','sdk','report']}

def j(v):return json.dumps(v,sort_keys=True,separators=(',',':'),default=str)
def parsed(v):return json.loads(v or '{}')
def slug(v):
    if not isinstance(v,str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,59}',v):raise ValueError('Invalid ID')
    return v

def require_project(s,p):
    if not s.get(Project,slug(p)):raise ValueError('Unknown project')

def emit(s,p,kind,body):s.add(Event(project_id=p,kind=kind,body=j(body)))

def create_project(s,id,name,description=''):
    id=slug(id)
    if not isinstance(name,str) or not 1<=len(name)<=120:raise ValueError('Invalid project name')
    if s.get(Project,id):raise ValueError('Project exists')
    s.add(Project(id=id,name=name,description=str(description)[:2000]));emit(s,id,'project.created',{'name':name})
    return {'id':id,'name':name}

def register_device(s,p,id,name,kind='unknown',identity=None):
    require_project(s,p);id=slug(id)
    if s.get(Device,id):raise ValueError('Device ID exists')
    d=Device(id=id,project_id=p,name=str(name)[:120],kind=str(kind)[:60],identity=j(identity or {}))
    s.add(d);emit(s,p,'device.registered',{'id':id});return {'id':id,'project_id':p}

def import_file(s,p,kind,filename,device_id=None):
    require_project(s,p)
    if kind not in VALID_TYPES:raise ValueError('Invalid artifact kind')
    # Never accept absolute paths, traversal, symlinks, or host directories.
    if not isinstance(filename,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,180}',filename) or '..' in filename:
        raise ValueError('Only an input basename is allowed')
    if device_id:
        d=s.get(Device,slug(device_id))
        if not d or d.project_id!=p:raise ValueError('Unknown device for this project')
    folder={'firmware':'firmware','pcap':'pcaps','mobile-log':'mobile','serial-log':'serial','ble-log':'ble','protocol':'protocols','other':'other'}[kind]
    root=INPUT/folder;path=root/filename
    if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):raise ValueError('File not in allowed import folder')
    if path.stat().st_size>256*1024*1024:raise ValueError('File exceeds 256 MiB import limit')
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for chunk in iter(lambda:file.read(65536),b''):digest.update(chunk)
    sha=digest.hexdigest();target=ROOT/'objects'/sha[:2]/sha
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():
        with path.open('rb') as src, target.with_name(sha+'.part').open('wb') as dst:shutil.copyfileobj(src,dst)
        target.with_name(sha+'.part').replace(target)
    if not s.get(Artifact,sha):s.add(Artifact(id=sha,type=kind,size=path.stat().st_size,original_name=filename,source='import'))
    # Idempotent relink to one project.
    link=s.scalar(select(ProjectArtifact).where(ProjectArtifact.project_id==p,ProjectArtifact.artifact_id==sha,ProjectArtifact.device_id==device_id))
    if not link:s.add(ProjectArtifact(project_id=p,artifact_id=sha,device_id=device_id))
    emit(s,p,'artifact.imported',{'sha256':sha,'type':kind,'device_id':device_id,'filename':filename})
    return {'sha256':sha,'type':kind,'size':path.stat().st_size,'project_id':p}

def evidence(s,p,kind,summary,fields=None,artifact_id=None,device_id=None,locator=None,confidence=1.0,observed_at=None,clock_source='server',external_ref=None):
    require_project(s,p)
    if not 0<=float(confidence)<=1:raise ValueError('Confidence 0..1 required')
    if artifact_id:
        linked=s.scalar(select(ProjectArtifact).where(ProjectArtifact.project_id==p,ProjectArtifact.artifact_id==artifact_id))
        if not linked:raise ValueError('Artifact not linked to this project')
    e=Evidence(project_id=p,kind=str(kind)[:60],summary=str(summary)[:2000],fields=j(fields or {}),artifact_id=artifact_id,external_ref=external_ref,
               device_id=device_id,locator=j(locator or {}),confidence=confidence,clock_source=clock_source,
               observed_at=observed_at or now())
    s.add(e);s.flush();emit(s,p,'evidence.recorded',{'id':e.id,'kind':e.kind,'artifact':artifact_id})
    return {'id':e.id,'project_id':p,'kind':e.kind,'confidence':e.confidence}

def enqueue(s,p,kind,params=None):
    require_project(s,p)
    if kind not in VALID_JOBS:raise ValueError('Unsupported job type')
    v=params or {}
    if len(j(v))>16384:raise ValueError('Job parameters too large')
    ident=str(uuid.uuid4());s.add(Job(id=ident,project_id=p,kind=kind,params=j(v)))
    emit(s,p,'job.queued',{'id':ident,'kind':kind});return {'id':ident,'status':'queued','kind':kind}

def artifact_bytes(s,p,sha,limit=8_000_000):
    if not isinstance(sha,str) or not re.fullmatch('[0-9a-f]{64}',sha):raise ValueError('Invalid artifact sha256')
    rel=s.scalar(select(ProjectArtifact).where(ProjectArtifact.project_id==p,ProjectArtifact.artifact_id==sha))
    if not rel:raise ValueError('Artifact is not linked to project')
    path=ROOT/'objects'/sha[:2]/sha
    with path.open('rb') as f:return f.read(limit)

def firmware_intelligence(s,p,params):
    sha=params['sha256'];data=artifact_bytes(s,p,sha)
    if data[:4]==b'\x7fELF':format='ELF'
    elif data[:2]==b'PK':format='ZIP'
    elif data[:4]==b'\x27\x05\x19\x56':format='U-Boot uImage'
    else:format='unknown'
    # Conservative bounded ASCII extraction. Never extract secrets into agent results.
    found=set()
    for m in re.finditer(rb'(?i)\b(?:https?://|[a-z0-9_-]+\.)[a-z0-9.\-/_:?=]{4,170}',data):
        candidate=m.group().decode('ascii',errors='replace').rstrip('.,')
        if '.' in candidate and not any(x in candidate.lower() for x in ('token=','password=','secret=')):
            found.add(candidate)
        if len(found)>=150:break
    finding={'sha256':sha,'format':format,'prefix_bytes_scanned':len(data),'truncated':s.get(Artifact,sha).size>len(data),
             'network_strings':sorted(found),'confidence':'heuristic','external_tools':'Binwalk/Ghidra optional; not run by this job'}
    result=evidence(s,p,'firmware-intelligence',f'Firmware heuristic scan ({format})',finding,artifact_id=sha,confidence=0.5)
    for host in sorted(found)[:70]:
        hostname=urlsplit(host).hostname if '://' in host else host.split('/',1)[0]
        if not hostname:continue
        s.add(Relationship(project_id=p,from_type='artifact',from_id=sha,relation='contains-string',to_type='endpoint',to_id=hostname.lower(),evidence_id=result['id']))
    return finding

def mobile_analyze(s,p,params):
    sha=params['sha256'];data=artifact_bytes(s,p,sha,2_000_000)
    lines=data.decode('utf-8',errors='replace').splitlines()
    # Filter only metadata of hostnames/API paths, not account/token/body content.
    hosts=sorted({m.group(0) for ln in lines[:25000] for m in re.finditer(r'(?i)\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b',ln)})[:100]
    result={'line_count_sampled':len(lines),'hosts':hosts,'sdk_events':'logcat text only; no mobile emulator attached'}
    ev=evidence(s,p,'mobile-log','Mobile app log metadata extracted',result,artifact_id=sha,confidence=0.6)
    for host in hosts:s.add(Relationship(project_id=p,from_type='artifact',from_id=sha,relation='mentions',to_type='endpoint',to_id=host,evidence_id=ev['id']))
    return result

def discover_states(s,p,params):
    entries=s.scalars(select(Evidence).where(Evidence.project_id==p).order_by(Evidence.id).limit(500)).all()
    observations=[e for e in entries if e.kind in ('protocol-message','http','mobile-event','serial-event','ble-event')]
    transitions=[]
    for a,b in zip(observations,observations[1:]):
        if a.device_id and b.device_id and a.device_id!=b.device_id:continue
        transitions.append({'from':a.kind+':'+a.summary[:50],'to':b.kind+':'+b.summary[:50],
                            'evidence':[a.id,b.id],'confidence':'temporal-order-only'})
    return {'candidate_transitions':transitions[:150],'warning':'Temporal adjacency is not proof of a protocol state machine'}

def correlate(s,p,params):
    rels=s.scalars(select(Relationship).where(Relationship.project_id==p).limit(500)).all()
    known=s.scalars(select(Evidence).where(Evidence.project_id==p).limit(500)).all()
    domain_to_ids={}
    for e in known:
        f=parsed(e.fields)
        for key in ('hostname','host','domain','dns_name'):
            name=f.get(key)
            if isinstance(name,str):domain_to_ids.setdefault(name.lower(),[]).append(e.id)
    matches=[]
    for r in rels:
        if r.to_type=='endpoint' and r.to_id.lower() in domain_to_ids:
            matches.append({'endpoint':r.to_id,'firmware_evidence':r.evidence_id,'traffic_evidence':domain_to_ids[r.to_id.lower()],
                            'relation_id':r.id,'confidence':'matching hostname (not proof of function execution)'})
    return {'matches':matches[:250],'evidence_count':len(known),'relationship_count':len(rels)}

def kaitai(s,p,params):
    # The output is a candidate KSY for a selected framing type, not a verified decoder.
    fmt=params.get('framing','len16be')
    if fmt not in ('len16be','len32be','raw'):raise ValueError('Supported framing: len16be, len32be, raw')
    if fmt=='raw':seq='  - id: body\n    size-eos: true\n'
    else:
        width='u2be' if fmt=='len16be' else 'u4be'
        seq=f'  - id: length\n    type: {width}\n  - id: body\n    size: length\n'
    source='meta:\n  id: candidate_device_message\n  endian: be\nseq:\n'+seq.replace('      -','  -')
    return {'format':fmt,'ksy':source,'verified':False}

def dissector(s,p,params):
    port=int(params.get('tcp_port',0))
    if not 1024<=port<=65535:raise ValueError('Use explicit nonprivileged TCP port 1024..65535')
    name='candidate_device'
    lua=f'''-- Candidate length-framed device dissector, validate against captures before using.
local p=Proto("{name}","Candidate device protocol")
local length=ProtoField.uint16("{name}.length","Length",base.DEC)
p.fields={{length}}
function p.dissector(buf,pinfo,tree)
  if buf:len()<2 then return end
  local n=buf(0,2):uint()
  if n>buf:len()-2 then return end
  pinfo.cols.protocol="CANDIDATE"
  local t=tree:add(p,buf())
  t:add(length,buf(0,2))
end
DissectorTable.get("tcp.port"):add({port},p)
'''
    return {'lua':lua,'verified':False,'tcp_port':port}

def sdk(s,p,params):
    # Reuse candidate contract/codegen in existing workbench via decoupled shared implementation.
    endpoints=[]
    for e in s.scalars(select(Evidence).where(Evidence.project_id==p,Evidence.kind=='http').limit(200)):
        f=parsed(e.fields);path=f.get('path');method=f.get('method','GET')
        if isinstance(path,str) and re.fullmatch(r'/[\w/.-]{0,200}',path):endpoints.append({'path':path,'method':str(method).upper()})
    endpoints=list({(v['path'],v['method']):v for v in endpoints}.values())
    py='''# Generated candidate; verify operations and authentication before use.\nimport requests\nclass DeviceClient:\n    def __init__(self, base_url):self.base_url=base_url.rstrip('/')\n'''
    for e in endpoints:
        func=(e['method']+'_'+e['path']).replace('/','_').replace('-','_').replace('.','_').lower()
        func=re.sub(r'[^a-z0-9_]', '',func)[:70]
        py+=f'    def {func}(self):\n        return requests.request({e["method"]!r}, self.base_url+{e["path"]!r},timeout=5)\n'
    ts='// Candidate only. Verify authentication and schemas.\nexport class DeviceClient { constructor(public baseUrl:string) {}\n'
    for e in endpoints:ts+=f'  async {e["method"].lower()}_{re.sub("[^a-z0-9]","_",e["path"].lower())}() {{return fetch(this.baseUrl+{j(e["path"])},{{method:{j(e["method"])}}});}}\n'
    ts+='}\n'
    cs='// Candidate only: validate before use.\nusing System.Net.Http;\npublic sealed class DeviceClient { public HttpClient Http {get;} public DeviceClient(HttpClient http)=>Http=http; }\n'
    return {'openapi':{'openapi':'3.1.0','info':{'title':'Unverified device protocol','version':'0.0.0'},'paths':{e['path']:{e['method'].lower():{'responses':{'default':{'description':'Observed metadata only'}}}} for e in endpoints}},
            'python':py,'typescript':ts,'csharp':cs,'verified':False,'operations':len(endpoints)}

def emulate(s,p,params):
    """Offline declarative emulator: state transitions, no arbitrary code or outbound sockets."""
    rules=params.get('transitions',[]);actions=params.get('actions',[])
    if not isinstance(rules,list) or len(rules)>100 or not isinstance(actions,list) or len(actions)>1000:raise ValueError('Invalid emulator limits')
    state=str(params.get('initial','idle'))[:50];history=[]
    for action in actions:
        if not isinstance(action,str) or len(action)>80:raise ValueError('Invalid action')
        rule=next((r for r in rules if isinstance(r,dict) and r.get('from')==state and r.get('action')==action),None)
        after=str(rule['to'])[:50] if rule else state
        history.append({'action':action,'before':state,'after':after,'matched':bool(rule)})
        state=after
    return {'final_state':state,'history':history,'offline_only':True}

def mutate(s,p,params):
    # Deterministic mutations of an *offline input sample*. No physical-device targeting.
    sha=params['sha256'];data=artifact_bytes(s,p,sha,8192);max_cases=min(max(int(params.get('cases',10)),1),100)
    if not data:return {'cases':0,'mutations':[]}
    vectors=[]
    for i in range(max_cases):
        b=bytearray(data);pos=i%len(b);b[pos]^=1<<(i%8)
        vectors.append({'case':i,'offset':pos,'bit':i%8,'sha256':hashlib.sha256(b).hexdigest()})
    return {'cases':len(vectors),'mutations':vectors,'sent_to_device':False,'offline_only':True}

def topology(s,p,params):
    r=s.scalars(select(Relationship).where(Relationship.project_id==p).limit(1000)).all()
    edges=[{'from':{'type':x.from_type,'id':x.from_id},'to':{'type':x.to_type,'id':x.to_id},'relation':x.relation,'evidence_id':x.evidence_id} for x in r]
    return {'edges':edges,'inferred':True,'evidence_backed':True}

def report(s,p,params):
    items=s.scalars(select(Evidence).where(Evidence.project_id==p).order_by(Evidence.id).limit(1000)).all()
    lines=[f'# Device RE Lab research report — {p}','','Generated evidence index; no claims are automatically verified.','']
    for e in items:
        lines += [f'## Evidence #{e.id}: {e.kind}',f'- Summary: {e.summary}',f'- Confidence: {e.confidence:.2f}',f'- Artifact SHA-256: {e.artifact_id or "not linked"}',f'- Locator: `{e.locator}`','']
    return {'markdown':'\n'.join(lines),'evidence_count':len(items)}

def store_generated(s,p,job_id,result):
    """Store derived protocols/reports as hashes, not mutable temporary output paths."""
    content=(json.dumps(result,indent=2,sort_keys=True,default=str)+'\n').encode()
    if len(content)>500_000:return None
    sha=hashlib.sha256(content).hexdigest();path=ROOT/'objects'/sha[:2]/sha
    path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():path.write_bytes(content)
    if not s.get(Artifact,sha):s.add(Artifact(id=sha,size=len(content),type='protocol',original_name=f'job-{job_id}.json',source='generated'))
    if not s.scalar(select(ProjectArtifact).where(ProjectArtifact.project_id==p,ProjectArtifact.artifact_id==sha)):
        s.add(ProjectArtifact(project_id=p,artifact_id=sha))
    emit(s,p,'artifact.generated',{'sha256':sha,'job':job_id})
    return sha

def bundle(s,p,params):
    """Portable manifest/reports (does not export proprietary firmware or capture payloads by default)."""
    artifacts=s.scalars(select(ProjectArtifact).where(ProjectArtifact.project_id==p).limit(1000)).all()
    evidences=s.scalars(select(Evidence).where(Evidence.project_id==p).limit(1000)).all()
    data={'project':p,'artifacts':[{'sha256':x.artifact_id,'device':x.device_id} for x in artifacts],
          'evidence':[{'id':x.id,'kind':x.kind,'summary':x.summary,'artifact_sha256':x.artifact_id,'locator':parsed(x.locator),'confidence':x.confidence} for x in evidences]}
    buf=io.BytesIO()
    total_generated=0
    with zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',json.dumps(data,indent=2))
        z.writestr('report.md',report(s,p,{})['markdown'])
        for link in artifacts:
            art=s.get(Artifact,link.artifact_id)
            if art and art.source=='generated' and art.size<=200_000 and total_generated+art.size<=5_000_000:
                source=ROOT/'objects'/art.id[:2]/art.id
                if source.is_file() and not source.is_symlink():
                    z.writestr('generated/'+art.id+'.json',source.read_bytes())
                    total_generated+=art.size
    output=ROOT/'exports';output.mkdir(parents=True,exist_ok=True)
    dest=output/f'{p}-{uuid.uuid4().hex[:10]}.zip';dest.write_bytes(buf.getvalue())
    return {'export_name':dest.name,'bytes':dest.stat().st_size,'includes_raw_firmware':False,'includes_raw_pcaps':False}

def replay(s,p,params):
    # Replay previous evidence actions against in-process declarative emulator, never remote target.
    ids=params.get('evidence_ids',[])
    if not isinstance(ids,list) or len(ids)>500:raise ValueError('Invalid evidence ids')
    actions=[]
    for id in ids:
        e=s.get(Evidence,int(id))
        if not e or e.project_id!=p:raise ValueError('Evidence outside project')
        actions.append(parsed(e.fields).get('action',e.summary[:80]))
    sim=emulate(s,p,{'transitions':params.get('transitions',[]),'initial':params.get('initial','idle'),'actions':actions})
    return {'replayed_evidence_ids':ids,**sim,'network_io':False}

def run_job(s,job):
    p=job.project_id;kind=job.kind;params=parsed(job.params)
    fn={'firmware-intelligence':firmware_intelligence,'mobile-analyze':mobile_analyze,'protocol-state':discover_states,
        'correlate':correlate,'kaitai':kaitai,'dissector':dissector,'sdk':sdk,'emulator-test':emulate,
        'mutate':mutate,'topology':topology,'report':report,'bundle':bundle,'replay':replay}
    if kind=='recipe':
        recipe=params.get('name')
        if recipe not in RECIPES:raise ValueError('Unknown recipe')
        outputs=[]
        for step in RECIPES[recipe]:
            if step in ('firmware-intelligence','mobile-analyze') and not params.get('sha256'):
                outputs.append({'step':step,'status':'skipped','reason':'Provide a project-linked artifact sha256'});continue
            if step=='dissector' and not params.get('tcp_port'):
                outputs.append({'step':step,'status':'skipped','reason':'Specify protocol TCP port'});continue
            try:
                res=fn[step](s,p,params)
                outputs.append({'step':step,'status':'succeeded','result':res})
            except (ValueError,KeyError) as exc:
                outputs.append({'step':step,'status':'skipped','reason':str(exc)[:180]})
        return {'recipe':recipe,'steps':outputs}
    return fn[kind](s,p,params)
