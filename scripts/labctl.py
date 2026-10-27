#!/usr/bin/env python3
"""CLI for repeatable Device experiments. No secrets printed or cached."""
from pathlib import Path
import argparse, json, os, re, shutil, sys, urllib.request, urllib.error

ROOT = Path(__file__).resolve().parents[1]
settings = {}
env_path = ROOT / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if '=' in line and not line.startswith('#'):
            a, b = line.split('=', 1)
            settings[a] = b

BASE = 'http://127.0.0.1:8090/__lab__/'


def request(path, method='GET', payload=None):
    headers = {'Content-Type': 'application/json'}
    if method != 'GET':
        headers['X-Lab-Token'] = settings.get('LAB_ADMIN_TOKEN', '')
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as err:
        raise SystemExit(f'HTTP {err.code}: {err.read(600).decode(errors="replace")}')


p = argparse.ArgumentParser(description='RELab local controller CLI')
sub = p.add_subparsers(dest='command', required=True)
sub.add_parser('health', help='Check Lab API health')
sub.add_parser('list', help='List active/past experiments')
sub.add_parser('analyses', help='List capture analyses')
sub.add_parser('firmware', help='List firmware files')
sub.add_parser('status', help='Display unified lab status dashboard')

start = sub.add_parser('start', help='Start a new hypothesis experiment')
start.add_argument('name')
start.add_argument('hypothesis')

finish = sub.add_parser('finish', help='Finish an experiment with results')
finish.add_argument('id')
finish.add_argument('result')

rollback = sub.add_parser('rollback', help='Rollback an experiment state')
rollback.add_argument('id')

compare = sub.add_parser('compare', help='Compare two analyses')
compare.add_argument('a')
compare.add_argument('b')

scan = sub.add_parser('scan', help='Scan a firmware image')
scan.add_argument('filename')

replay = sub.add_parser('replay', help='Replay a captured event')
replay.add_argument('event_id', type=int)

set_prof = sub.add_parser('set-profile', help='Switch active target device profile')
set_prof.add_argument('profile', help='Profile name (e.g. generic, stadia-original)')

args = p.parse_args()
cmd = args.command

if cmd == 'health':
    x = request('health')
elif cmd == 'list':
    x = request('experiments')
elif cmd == 'analyses':
    x = request('analyses')
elif cmd == 'firmware':
    x = request('firmware')
elif cmd == 'start':
    x = request('experiments', 'POST', {'name': args.name, 'hypothesis': args.hypothesis})
elif cmd == 'finish':
    x = request(f'experiments/{args.id}/finish', 'POST', {'result': args.result})
elif cmd == 'rollback':
    x = request(f'experiments/{args.id}/rollback', 'POST', {})
elif cmd == 'compare':
    x = request(f'compare?a={args.a}&b={args.b}')
elif cmd == 'scan':
    x = request(f'firmware/{args.filename}')
elif cmd == 'replay':
    x = request(f'replay/{args.event_id}')
elif cmd == 'status':
    status_report = {
        'profile': settings.get('TARGET_PROFILE', 'generic'),
        'lab_ip': settings.get('LAB_IP', '127.0.0.1'),
        'api_health': None,
        'dns_status': None,
        'active_experiments': None,
        'firmware_files': [],
        'pcap_count': 0
    }
    try:
        status_report['api_health'] = request('health')
    except Exception as e:
        status_report['api_health'] = f'Offline / unreachable ({e})'
    try:
        status_report['dns_status'] = request('dns')
    except Exception as e:
        status_report['dns_status'] = f'Offline / unreachable ({e})'
    try:
        status_report['active_experiments'] = request('experiments')
    except Exception:
        pass
    fw_dir = ROOT / 'firmware'
    if fw_dir.is_dir():
        status_report['firmware_files'] = [f.name for f in fw_dir.iterdir() if f.is_file() and not f.name.endswith('.json')]
    pcaps_dir = ROOT / 'data/pcaps'
    if pcaps_dir.is_dir():
        status_report['pcap_count'] = len([f for f in pcaps_dir.iterdir() if f.is_file() and f.suffix.lower() in ('.pcap', '.pcapng')])
    x = status_report
elif cmd == 'set-profile':
    prof_path = ROOT / 'profiles' / f'{args.profile}.json'
    if not prof_path.is_file():
        raise SystemExit(f'Error: Profile {args.profile} not found in {ROOT / "profiles"}.')
    # Update .env atomically
    if env_path.exists():
        content = env_path.read_text()
        if re.search(r'(?m)^TARGET_PROFILE=', content):
            content = re.sub(r'(?m)^TARGET_PROFILE=.*$', f'TARGET_PROFILE={args.profile}', content)
        else:
            content += f'\nTARGET_PROFILE={args.profile}\n'
        tmp = ROOT / f'.env.tmp.{os.getpid()}'
        tmp.write_text(content)
        tmp.chmod(0o600)
        os.replace(tmp, env_path)
    x = {'status': 'profile_updated', 'profile': args.profile, 'notice': 'Profile saved to .env.'}

print(json.dumps(x, indent=2))
