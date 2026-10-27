#!/usr/bin/env python3
"""Apply only explicitly-selected device profile's candidate DNS names.

Default generic profile has NO rewrites. Unrelated lab-managed and unmanaged records
are preserved; the API itself tracks rewrite ownership.
"""
from __future__ import annotations
import ipaddress
import json
import os
import sys
from pathlib import Path
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from importlib.machinery import SourceFileLoader
load_profile=SourceFileLoader('profile_cli',str(ROOT/'scripts/device-profile.py')).load_module().load_profile
BASE='http://127.0.0.1:8090/__lab__/dns'

def settings():
    d={}
    if (ROOT/'.env').exists():
        for line in (ROOT/'.env').read_text().splitlines():
            if '=' in line and not line.strip().startswith('#'):
                k,v=line.split('=',1);d[k.strip()]=v.strip()
    return d

def call(method='GET',payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    h={'Content-Type':'application/json'}
    if method!='GET':h['X-Lab-Token']=settings().get('LAB_ADMIN_TOKEN','')
    with urlopen(Request(BASE,data,headers=h,method=method),timeout=12) as res:return json.load(res)

def plan(action:str,profile_name:str,ip:str|None,managed:list[dict])->str:
    names={x.lower() for x in load_profile(profile_name)['dns_candidates']}
    if action=='enable' and not names:
        raise ValueError('Selected profile has no DNS candidates. Create/select a named profile or add rewrites manually.')
    existing={e['domain'].lower():e['answer'] for e in managed}
    for name in names:existing.pop(name,None)
    if action=='enable':
        if ip is None:raise ValueError('A destination LAB_IP is required')
        addr=ipaddress.ip_address(ip)
        if addr.is_unspecified or addr.is_multicast or addr.is_loopback or addr.is_link_local:
            raise ValueError('Use the isolated lab LAN address, not a special address')
        existing.update({name:str(addr) for name in names})
    return ''.join(f'{addr} {host}\n' for host,addr in sorted(existing.items()))

def main():
    if len(sys.argv)<2 or sys.argv[1] not in ('enable','disable'):
        sys.exit('Usage: dns-rewrite.py enable LAB_IP [PROFILE] | disable [PROFILE]')
    action=sys.argv[1];d=settings()
    if action=='enable':
        if len(sys.argv) not in (3,4):sys.exit('Usage: dns-rewrite.py enable LAB_IP [PROFILE]')
        addr=sys.argv[2];profile=sys.argv[3] if len(sys.argv)==4 else d.get('TARGET_PROFILE','generic')
    else:
        if len(sys.argv) not in (2,3):sys.exit('Usage: dns-rewrite.py disable [PROFILE]')
        addr=None;profile=sys.argv[2] if len(sys.argv)==3 else d.get('TARGET_PROFILE','generic')
    current=call().get('managed',[])
    updated=plan(action,profile,addr,current)
    result=call('PUT',{'hosts':updated})
    print(json.dumps({'operation':action,'profile':profile,'managed_rewrites':result.get('managed_rewrites')},indent=2))
if __name__=='__main__':
    try:main()
    except ValueError as exc:sys.exit(str(exc))
