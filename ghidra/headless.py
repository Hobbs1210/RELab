"""Small MCP facade around OFFLINE Ghidra analyzeHeadless. No firmware execution."""
import json,os,pathlib,re,subprocess,uuid
from fastapi import FastAPI,HTTPException
from fastapi_mcp import FastApiMCP

app=FastAPI(title='Device Ghidra firmware analysis',docs_url=None)
ROOT=pathlib.Path('/firmware');OUT=pathlib.Path('/reports');PROJ=pathlib.Path('/projects')

@app.get('/health',operation_id='ghidra_health')
def health():return {'ok':pathlib.Path('/opt/ghidra/support/analyzeHeadless').exists()}

@app.get('/files',operation_id='ghidra_firmware_files')
def files():return {'files':[p.name for p in ROOT.iterdir() if p.is_file()]}

@app.post('/analyze/{filename}',operation_id='ghidra_analyze_binary')
def analyze(filename:str):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,180}',filename):raise HTTPException(400,'Invalid filename')
    source=(ROOT/filename).resolve()
    if not source.is_relative_to(ROOT.resolve()) or not source.is_file():raise HTTPException(404,'File not found')
    if source.stat().st_size>150*1024*1024:raise HTTPException(413,'File too large')
    job=uuid.uuid4().hex[:16];OUT.mkdir(parents=True,exist_ok=True);PROJ.mkdir(parents=True,exist_ok=True)
    result=OUT/(job+'.json')
    cmd=['/opt/ghidra/support/analyzeHeadless',str(PROJ),'device_'+job,
         '-import',str(source),'-scriptPath','/app/scripts','-postScript','DumpFunctions.java',str(result),'-deleteProject']
    try: completed=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    except subprocess.TimeoutExpired:raise HTTPException(504,'Ghidra timed out after 300 seconds')
    report=json.loads(result.read_text()) if result.exists() else None
    return {'job':job,'exit_code':completed.returncode,'report':report,'stdout_tail':completed.stdout[-2500:], 'stderr_tail':completed.stderr[-2500:]}

@app.get('/reports/{job}',operation_id='ghidra_get_report')
def report(job:str):
    if not re.fullmatch('[0-9a-f]{16}',job):raise HTTPException(400,'Bad ID')
    p=OUT/(job+'.json')
    if not p.exists():raise HTTPException(404,'Report not found')
    return json.loads(p.read_text())

mcp=FastApiMCP(app,name='Device Ghidra offline research',include_operations=['ghidra_health','ghidra_firmware_files','ghidra_analyze_binary','ghidra_get_report'])
mcp.mount_http(mount_path='/mcp')
