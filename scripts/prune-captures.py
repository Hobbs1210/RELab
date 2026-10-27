#!/usr/bin/env python3
"""Dry-run by default; local storage retention on owner-approved data only."""
from pathlib import Path
import argparse,time
root=Path(__file__).resolve().parents[1]/'data/pcaps'
p=argparse.ArgumentParser();p.add_argument('--older-than-days',type=int,default=14);p.add_argument('--apply',action='store_true');args=p.parse_args()
if not 1<=args.older_than_days<=3650:raise SystemExit('Allowed days: 1..3650')
if not root.exists():raise SystemExit('Capture folder not created')
files=[f for f in root.iterdir() if f.is_file() and f.suffix.lower() in ('.pcap','.pcapng')]
expired=[f for f in files if time.time()-f.stat().st_mtime>args.older_than_days*86400]
print(f'{len(expired)} expired capture(s); {sum(f.stat().st_size for f in expired)} bytes; apply={args.apply}')
for f in expired:
    print(f.name)
    if args.apply:f.unlink()
