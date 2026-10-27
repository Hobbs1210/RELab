"""Universal protocol workbench. External hardware/network mutation is deliberately absent."""
from __future__ import annotations
import base64,hashlib,hmac,json,os,re,sqlite3,urllib.request,urllib.error
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse,PlainTextResponse,JSONResponse
from fastapi_mcp import FastApiMCP
from engine import protocols,decode_bytes,infer,firmware_arch,compare_firmware,openapi_from_events,sdk_sources
from timeline import events as timeline_events
from hardware import enumerate_hardware
from firmware_download import download_firmware, DownloadError

app=FastAPI(title='Device RE Lab — Universal Protocol Workbench',docs_url=None)
TOKEN=os.environ.get('LAB_ADMIN_TOKEN','')
DB=Path(os.environ.get('DB_PATH','/data/requests.db'))
ANALYSIS=Path(os.environ.get('ANALYSIS_PATH','/analysis'))
FIRMWARE=Path(os.environ.get('FIRMWARE_PATH','/firmware'))
PROTOCOLS=Path(os.environ.get('PROTOCOLS_PATH','/protocols'))
OUTPUT=Path(os.environ.get('OUTPUT_PATH','/outputs'))
HARDWARE_LOG=OUTPUT/'hardware-events.jsonl'

@app.middleware('http')
async def auth(request:Request,call_next):
    if request.url.path.startswith('/v1/') and request.method in ('POST','PUT','PATCH','DELETE'):
        if not TOKEN or not hmac.compare_digest(TOKEN,request.headers.get('x-lab-token','')):
            return JSONResponse({'detail':'Mutation requires X-Lab-Token'},status_code=403)
    return await call_next(request)

def file_from(root:Path,name:str)->Path:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,120}',name) or name.startswith('.') or '..' in name:
        raise HTTPException(400,'A basename (no paths) is required')
    p=root/name
    if not p.is_file() or not p.resolve().is_relative_to(root.resolve()):raise HTTPException(404,'File not found')
    return p

def journal(max_rows:int=300)->list:
    if not DB.is_file():return []
    try:
        with sqlite3.connect(f'file:{DB}?mode=ro',uri=True) as conn:
            conn.row_factory=sqlite3.Row
            return [dict(r) for r in conn.execute('SELECT id,method,host,path,response_status,body_b64 FROM http_requests ORDER BY id DESC LIMIT ?',(min(max_rows,1000),))]
    except sqlite3.Error:return []

def sample_ids(ids:str)->list[bytes]:
    try:lookup=[int(s) for s in ids.split(',') if s.strip()]
    except ValueError:raise HTTPException(400,'ids must be comma-separated integers')
    if not lookup or len(lookup)>100:raise HTTPException(400,'1..100 event ids needed')
    rows={r['id']:r for r in journal(1000)}
    if any(i not in rows for i in lookup):raise HTTPException(404,'Event unavailable within latest 1000')
    return [base64.b64decode(rows[i]['body_b64']) for i in lookup]

@app.get('/',include_in_schema=False)
def ui():return HTMLResponse(Path(__file__).with_name('ui.html').read_text())

@app.get('/v1/health',operation_id='workbench_health')
def health():return {'status':'ok','profile':'general-purpose','write_control':'token-protected','safe_default':'passive'}

@app.get('/v1/protocols',operation_id='workbench_list_protocol_adapters')
def list_protocols():return {'adapters':protocols(PROTOCOLS)}

@app.get('/v1/decode',operation_id='workbench_decode_hex')
def decode(protocol:str='raw',hexdata:str=''):
    if len(hexdata)>131072:raise HTTPException(400,'Hex input too large')
    try:
        selected=protocols(PROTOCOLS)[protocol]
        return decode_bytes(bytes.fromhex(hexdata),selected)
    except KeyError:raise HTTPException(404,'Unknown protocol adapter')
    except ValueError as exc:raise HTTPException(400,str(exc))

@app.get('/v1/infer',operation_id='workbench_infer_http_samples')
def infer_ids(ids:str):
    try:return infer(sample_ids(ids))
    except ValueError as exc:raise HTTPException(400,str(exc))

@app.get('/v1/infer/hex',operation_id='workbench_infer_binary_hex')
def infer_hex(samples:str):
    if len(samples)>150000:raise HTTPException(400,'Input too large')
    try:return infer([bytes.fromhex(x.strip()) for x in samples.split(',') if x.strip()])
    except ValueError as exc:raise HTTPException(400,str(exc))

@app.post('/v1/hardware-events',operation_id='workbench_import_hardware_observation')
async def hardware_import(request:Request):
    payload=await request.json()
    if not isinstance(payload,dict) or payload.get('kind') not in ('ble','usb','serial'):
        raise HTTPException(400,'kind must be ble, usb, or serial')
    if not isinstance(payload.get('time'),str) or len(payload['time'])>40 or not isinstance(payload.get('fields',{}),dict):
        raise HTTPException(400,'time must be ISO8601, fields must be object')
    if len(json.dumps(payload))>8192:raise HTTPException(400,'Observation too large')
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with HARDWARE_LOG.open('a') as out:out.write(json.dumps(payload)+'\n')
    return {'imported':True,'source':'user-supplied','passive_capture':False}

@app.get('/v1/timeline',operation_id='workbench_unified_timeline')
def timeline(limit:int=200,src:str='',analysis_id:str=''):
    if len(src)>100 or len(analysis_id)>32:raise HTTPException(400,'Invalid filter')
    return timeline_events(DB,ANALYSIS,limit,src or None,analysis_id or None,HARDWARE_LOG)

@app.get('/v1/hardware',operation_id='workbench_hardware_inventory')
def hardware():return enumerate_hardware()

@app.get('/v1/hardware/usb',operation_id='workbench_usb_inventory')
def usb_inventory():return {'usb':enumerate_hardware()['usb'],'reads_only':True}

@app.get('/v1/hardware/serial',operation_id='workbench_serial_inventory')
def serial_inventory():return {'serial':enumerate_hardware()['serial'],'reads_only':True}

@app.get('/v1/firmware',operation_id='workbench_list_firmware')
def firmware_files():return {'files':[{'name':p.name,'size':p.stat().st_size} for p in sorted(FIRMWARE.iterdir())[:200] if p.is_file()] if FIRMWARE.exists() else []}

@app.post('/v1/firmware/download',operation_id='workbench_download_firmware')
async def firmware_download(request:Request):
    """Operator-approved write; deliberately excluded from the read-only MCP."""
    try:
        payload=await request.json()
        if not isinstance(payload,dict): raise DownloadError('Expected JSON object')
        result=download_firmware(payload.get('url'),FIRMWARE,
                                 filename=payload.get('filename'),
                                 expected_sha256=payload.get('sha256'))
        result['research_indexed']=False
        if os.environ.get('RESEARCH_HUB_URL'):
            try:
                request_body=json.dumps({'project_id':payload.get('project_id','default'),
                    'kind':'firmware','filename':result['filename']}).encode()
                req=urllib.request.Request(os.environ['RESEARCH_HUB_URL'].rstrip('/')+'/v1/artifacts/import',
                    data=request_body,headers={'Content-Type':'application/json','X-Lab-Token':TOKEN},method='POST')
                with urllib.request.urlopen(req,timeout=4) as res:
                    result['research_indexed']=res.status==200
            except (urllib.error.URLError,TimeoutError,KeyError):
                result['research_warning']='Research Hub unavailable; register the file later using /v1/artifacts/import'
        return result
    except DownloadError as exc:
        raise HTTPException(400,str(exc)) from exc


@app.get('/v1/firmware/{name}/architecture',operation_id='workbench_detect_firmware_architecture')
def arch(name:str):
    p=file_from(FIRMWARE,name)
    with p.open('rb') as f:data=f.read(2_000_000)
    return {'file':p.name,'size':p.stat().st_size,**firmware_arch(data)}

@app.get('/v1/firmware/compare',operation_id='workbench_compare_firmware_versions')
def compare(a:str,b:str):
    ap=file_from(FIRMWARE,a);bp=file_from(FIRMWARE,b)
    # Read at most 2 MiB from each untrusted file; hash full file incrementally.
    def whole_hash(p):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(65536),b''):h.update(chunk)
        return h.hexdigest()
    with ap.open('rb') as f:aa=f.read(2_000_000)
    with bp.open('rb') as f:bb=f.read(2_000_000)
    result=compare_firmware(aa,bb)
    result.update({'file_a':a,'file_b':b,'full_size_a':ap.stat().st_size,'full_size_b':bp.stat().st_size,'full_sha256_a':whole_hash(ap),'full_sha256_b':whole_hash(bp),
                   'compared_prefix_bytes':min(2_000_000,max(ap.stat().st_size,bp.stat().st_size)),
                   'partial_comparison':max(ap.stat().st_size,bp.stat().st_size)>2_000_000})
    return result

@app.get('/v1/contracts/openapi',operation_id='workbench_generate_candidate_openapi')
def contract():return openapi_from_events(journal())

@app.get('/v1/contracts/sdk/{language}',operation_id='workbench_generate_candidate_sdk')
def sdk(language:str):
    languages={'python','typescript','csharp'}
    if language not in languages:raise HTTPException(400,'Supported: python, typescript, csharp')
    result=sdk_sources(contract())
    return PlainTextResponse(result[language],headers={'X-Research-Warning':'Unverified candidate SDK'})

@app.post('/v1/protocols',operation_id='workbench_register_protocol_adapter')
async def register(request:Request):
    spec=await request.json()
    if not isinstance(spec,dict) or spec.get('framing') not in ('raw','length-prefix','delimiter','grpc','mqtt','coap'):
        raise HTTPException(400,'Only declarative framing adapters are allowed')
    name=spec.get('id')
    if not isinstance(name,str) or not re.fullmatch('[a-z0-9_-]{1,50}',name) or len(json.dumps(spec))>8000:
        raise HTTPException(400,'Invalid id or adapter size')
    # Decode a synthetic fixture before accepting adapter config
    try: decode_bytes(b'\x00\x00',spec)
    except (ValueError,OverflowError) as exc:raise HTTPException(400,str(exc))
    PROTOCOLS.mkdir(parents=True,exist_ok=True)
    dest=PROTOCOLS/(name+'.json')
    dest.write_text(json.dumps(spec,indent=2)+'\n')
    return {'registered':name,'executable_plugin':False}

@app.post('/v1/exports',operation_id='workbench_export_candidate_contracts')
def export():
    # Operator-approved export; writes to a dedicated output directory only.
    spec=contract();sources=sdk_sources(spec)
    OUTPUT.mkdir(parents=True,exist_ok=True)
    files={'candidate-openapi.json':json.dumps(spec,indent=2)+'\n','DeviceClient.py':sources['python'],
           'DeviceClient.ts':sources['typescript'],'DeviceClient.cs':sources['csharp']}
    for fname,content in files.items():
        tmp=OUTPUT/(fname+'.tmp');tmp.write_text(content);tmp.replace(OUTPUT/fname)
    return {'files':list(files),'operations':sources['operation_count'],'output_dir':'/outputs','verified_contract':False}

# Register only read operations in MCP, including USB/serial inventory; do not expose POST.
workbench_mcp=FastApiMCP(app,name='Universal Device Protocol Workbench',include_operations=[
 'workbench_health','workbench_list_protocol_adapters','workbench_decode_hex',
 'workbench_infer_http_samples','workbench_infer_binary_hex','workbench_unified_timeline','workbench_hardware_inventory',
 'workbench_usb_inventory','workbench_serial_inventory','workbench_list_firmware','workbench_detect_firmware_architecture',
 'workbench_compare_firmware_versions','workbench_generate_candidate_openapi',
 'workbench_generate_candidate_sdk'
])
workbench_mcp.mount_http(mount_path='/mcp')
