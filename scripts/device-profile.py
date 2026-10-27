#!/usr/bin/env python3
"""List/show/validate device research profiles. No DNS changes or network access."""
from __future__ import annotations
import argparse
import ipaddress
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROFILES=ROOT/'profiles'

def load_profile(name:str)->dict:
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',name):
        raise ValueError('Invalid profile name')
    path=PROFILES/(name+'.json')
    if not path.exists():raise ValueError('Profile does not exist: '+name)
    profile=json.loads(path.read_text())
    if profile.get('id')!=name:raise ValueError('Profile ID must match filename')
    names=profile.get('dns_candidates',[])
    if not isinstance(names,list) or len(names)>100:raise ValueError('Invalid DNS candidates')
    if any(not isinstance(s,str) or len(s)>253 or not re.fullmatch(r'[a-zA-Z0-9](?:[a-zA-Z0-9.-]*[a-zA-Z0-9])?',s) or '..' in s for s in names):
        raise ValueError('DNS hostname invalid (wildcards not supported)')
    if len(set(x.lower() for x in names))!=len(names):raise ValueError('Duplicate hostname')
    return profile

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    p=parser.add_subparsers(dest='action',required=True)
    p.add_parser('list')
    for op in ('show','validate'):p.add_parser(op).add_argument('name')
    args=parser.parse_args()
    if args.action=='list':
        for path in sorted(PROFILES.glob('*.json')):
            profile=load_profile(path.stem)
            print(f"{profile['id']:<25} {profile['display_name']}")
    else:
        profile=load_profile(args.name)
        print(json.dumps(profile,indent=2) if args.action=='show' else f'PASS profile {args.name} ({len(profile["dns_candidates"])} DNS candidates)')
if __name__=='__main__':
    try:main()
    except (ValueError,json.JSONDecodeError) as e:raise SystemExit(str(e))
