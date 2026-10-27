#!/usr/bin/env python3
"""Download a vendor's public HTTPS firmware URL into the local firmware directory.

Requires no third-party Python packages. Do not run as root; files belong to you.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'workbench'))
from firmware_download import download_firmware, DownloadError


def main():
    parser = argparse.ArgumentParser(description='Fetch authorized public HTTPS firmware (max 100 MiB)')
    parser.add_argument('url', help='Direct HTTPS URL for downloadable firmware bytes')
    parser.add_argument('--name', help='Destination basename; existing files are never replaced')
    parser.add_argument('--sha256', help='Expected SHA-256 hash; strongly recommended')
    args = parser.parse_args()
    try:
        print(json.dumps(download_firmware(args.url, ROOT / 'firmware',filename=args.name,expected_sha256=args.sha256),indent=2))
    except (DownloadError, OSError) as exc:
        parser.exit(1,f'Firmware download refused: {exc}\n')

if __name__ == '__main__':main()
