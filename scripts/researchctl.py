#!/usr/bin/env python3
"""Small localhost-first Research Hub CLI; never prints the private write token."""
import argparse,json,os,sys,time,urllib.request,urllib.error
from pathlib import Path
BASE=os.getenv('RESEARCH_HUB_URL','http://127.0.0.1:8320').rstrip('/')

def token():
    value=os.getenv('LAB_ADMIN_TOKEN','')
    if value:return value
    path=Path(__file__).resolve().parents[1]/'.env'
    if path.is_file():
        for l in path.read_text().splitlines():
            if l.startswith('LAB_ADMIN_TOKEN='):return l.partition('=')[2]
    return ''

def req(method,path,payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    headers={'Content-Type':'application/json'}
    if method!='GET':headers['X-Lab-Token']=token()
    with urllib.request.urlopen(urllib.request.Request(BASE+'/v1/'+path,data=data,headers=headers,method=method),timeout=15) as res:
        return json.loads(res.read())

parser=argparse.ArgumentParser(description='Research Hub local CLI; 127.0.0.1:8320 default')
sub=parser.add_subparsers(dest='command',required=True)
p=sub.add_parser('project');p.add_argument('id');p.add_argument('name')
p=sub.add_parser('device');p.add_argument('id');p.add_argument('name');p.add_argument('--project',default='default');p.add_argument('--kind',default='unknown')
p=sub.add_parser('import');p.add_argument('kind',choices=['firmware','pcap','mobile-log','serial-log','ble-log','protocol','other']);p.add_argument('filename');p.add_argument('--project',default='default')
p=sub.add_parser('job');p.add_argument('kind');p.add_argument('--project',default='default');p.add_argument('--params',default='{}')
p=sub.add_parser('recipe');p.add_argument('name');p.add_argument('--project',default='default');p.add_argument('--params',default='{}')
p=sub.add_parser('status');p.add_argument('id')
p=sub.add_parser('list');p.add_argument('what',choices=['projects','devices','artifacts','jobs','evidence','events','memory','recipes','timeline']);p.add_argument('--project',default='default')
a=parser.parse_args()
try:
    if a.command=='project':r=req('POST','projects',{'id':a.id,'name':a.name})
    elif a.command=='device':r=req('POST','devices',{'id':a.id,'name':a.name,'project_id':a.project,'kind':a.kind})
    elif a.command=='import':r=req('POST','artifacts/import',{'filename':a.filename,'kind':a.kind,'project_id':a.project})
    elif a.command in ('job','recipe'):
        params=json.loads(a.params)
        if a.command=='recipe':params['name']=a.name
        r=req('POST','jobs',{'kind':a.kind if a.command=='job' else 'recipe','project_id':a.project,'params':params})
    elif a.command=='status':r=req('GET','jobs/'+a.id)
    else:r=req('GET',a.what+('' if a.what in ('projects','recipes') else '?project_id='+a.project))
    print(json.dumps(r,indent=2))
except (ValueError,urllib.error.HTTPError,urllib.error.URLError) as e:
    print(f'Research Hub error: {e}',file=sys.stderr);sys.exit(1)
