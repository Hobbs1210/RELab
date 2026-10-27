#!/usr/bin/env python3
"""CLI for repeatable Device experiments. No secrets printed or cached."""
from pathlib import Path
import argparse,json,sys,urllib.request,urllib.error
ROOT=Path(__file__).resolve().parents[1]
settings={}
for line in (ROOT/'.env').read_text().splitlines() if (ROOT/'.env').exists() else []:
    if '=' in line and not line.startswith('#'):
        a,b=line.split('=',1);settings[a]=b
BASE='http://127.0.0.1:8090/__lab__/'

def request(path,method='GET',payload=None):
    headers={'Content-Type':'application/json'}
    if method!='GET':headers['X-Lab-Token']=settings.get('LAB_ADMIN_TOKEN','')
    body=json.dumps(payload).encode() if payload is not None else None
    req=urllib.request.Request(BASE+path,data=body,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
    except urllib.error.HTTPError as err:
        raise SystemExit(f'HTTP {err.code}: {err.read(600).decode(errors="replace")}')

p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='command',required=True)
sub.add_parser('health');sub.add_parser('list');sub.add_parser('analyses');sub.add_parser('firmware')
start=sub.add_parser('start');start.add_argument('name');start.add_argument('hypothesis')
finish=sub.add_parser('finish');finish.add_argument('id');finish.add_argument('result')
rollback=sub.add_parser('rollback');rollback.add_argument('id')
compare=sub.add_parser('compare');compare.add_argument('a');compare.add_argument('b')
scan=sub.add_parser('scan');scan.add_argument('filename')
replay=sub.add_parser('replay');replay.add_argument('event_id',type=int)
args=p.parse_args()
cmd=args.command
if cmd=='health':x=request('health')
elif cmd=='list':x=request('experiments')
elif cmd=='analyses':x=request('analyses')
elif cmd=='firmware':x=request('firmware')
elif cmd=='start':x=request('experiments','POST',{'name':args.name,'hypothesis':args.hypothesis})
elif cmd=='finish':x=request(f'experiments/{args.id}/finish','POST',{'result':args.result})
elif cmd=='rollback':x=request(f'experiments/{args.id}/rollback','POST',{})
elif cmd=='compare':x=request(f'compare?a={args.a}&b={args.b}')
elif cmd=='scan':x=request(f'firmware/{args.filename}')
elif cmd=='replay':x=request(f'replay/{args.event_id}')
print(json.dumps(x,indent=2))
