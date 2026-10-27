#!/usr/bin/env python3
"""Download a vendor's public HTTPS firmware URL into the local firmware directory.

Requires no third-party Python packages. Do not run as root; files belong to you.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workbench'))
from firmware_download import download_firmware, DownloadError


def _register_with_research_hub(filename: str, project_id: str) -> dict | None:
    hub_url = os.getenv('RESEARCH_HUB_URL', 'http://127.0.0.1:8320').rstrip('/')
    token = os.getenv('LAB_ADMIN_TOKEN', '')
    if not token:
        env_file = ROOT / '.env'
        if env_file.is_file():
            for line in env_file.read_text().splitlines():
                if line.startswith('LAB_ADMIN_TOKEN='):
                    token = line.partition('=')[2].strip()
                    break
    payload = json.dumps({'filename': filename, 'kind': 'firmware', 'project_id': project_id}).encode()
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['X-Lab-Token'] = token
    req = urllib.request.Request(f'{hub_url}/v1/artifacts/import', data=payload, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as exc:
        print(f"Notice: Could not register with Research Hub ({hub_url}): {exc}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description='Fetch authorized public HTTPS firmware (max 100 MiB)')
    parser.add_argument('url', help='Direct HTTPS URL for downloadable firmware bytes')
    parser.add_argument('--name', help='Destination basename; existing files are never replaced')
    parser.add_argument('--sha256', help='Expected SHA-256 hash; strongly recommended')
    parser.add_argument('--register', action='store_true', help='Automatically register downloaded firmware in Research Hub')
    parser.add_argument('--project', default='default', help='Research Hub project ID (default: "default")')
    args = parser.parse_args()
    try:
        print(f"Downloading from {args.url} ...", file=sys.stderr)
        result = download_firmware(args.url, ROOT / 'firmware', filename=args.name, expected_sha256=args.sha256)
        if args.register:
            hub_result = _register_with_research_hub(result['filename'], args.project)
            if hub_result:
                result['research_hub_registered'] = True
                result['research_hub'] = hub_result
        print(json.dumps(result, indent=2))
    except (DownloadError, OSError) as exc:
        parser.exit(1, f'Firmware download refused: {exc}\n')


if __name__ == '__main__':
    main()
