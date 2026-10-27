#!/usr/bin/env python3
"""Cross-layer DNS and TLS traffic correlation for Device RE Lab.

Correlates AdGuard DNS queries with TLS ClientHello SNI and HTTP flows to detect:
  1. Direct IP connections (hardcoded IPs without DNS queries)
  2. Domain fronting & SNI mismatches
  3. DoH / DoT encrypted DNS bypass attempts

Tied with MCP:
  Outputs structured evidence to data/analysis/ for device-api and device-research MCPs.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Known public DoH / DoT resolver IPs
DOH_PROVIDERS = {
    '1.1.1.1': 'Cloudflare DoH/DoT',
    '1.0.0.1': 'Cloudflare DoH/DoT',
    '8.8.8.8': 'Google DoH/DoT',
    '8.8.4.4': 'Google DoH/DoT',
    '9.9.9.9': 'Quad9 DoH/DoT',
    '149.112.112.112': 'Quad9 DoH/DoT',
    '208.67.222.222': 'OpenDNS DoH',
    '208.67.220.220': 'OpenDNS DoH',
}


def load_env() -> dict:
    env_file = ROOT / '.env'
    settings = {}
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                settings[k.strip()] = v.strip()
    return settings


def fetch_adguard_queries(settings: dict, target_ip: str | None = None) -> list[dict]:
    base = 'http://127.0.0.1:3000'
    user = settings.get('ADGUARD_USERNAME', 're')
    pw = settings.get('ADGUARD_PASSWORD', '')
    if not pw:
        return []
    auth = 'Basic ' + base64.b64encode(f'{user}:{pw}'.encode()).decode()
    url = f'{base}/control/querylog?limit=500'
    if target_ip:
        url += f'&search={target_ip}'
    req = urllib.request.Request(url, headers={'Authorization': auth})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data.get('data', [])
    except Exception:
        return []


def fetch_mitmproxy_flows() -> list[dict]:
    url = 'http://127.0.0.1:8081/flows'
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return []


def correlate(dns_queries: list[dict], http_flows: list[dict], target_ip: str | None = None) -> dict:
    # Build DNS resolution map: domain -> set(resolved_ips)
    dns_map = {}
    resolved_ips_to_domains = {}
    for q in dns_queries:
        domain = q.get('question', {}).get('name', '').rstrip('.').lower()
        client = q.get('client', '')
        if target_ip and client and client != target_ip:
            continue
        answers = q.get('answer', [])
        ips = []
        for ans in answers:
            val = ans.get('value', '')
            if val:
                ips.append(val)
                resolved_ips_to_domains.setdefault(val, set()).add(domain)
        if domain:
            dns_map.setdefault(domain, []).append({
                'time': q.get('time'),
                'ips': ips,
                'status': q.get('status', 'resolved')
            })

    # Evaluate flows
    connections = []
    anomalies = []

    for flow in http_flows:
        req = flow.get('request', {})
        server_conn = flow.get('server_conn', {})
        dest_ip = server_conn.get('peername', [None])[0] if server_conn.get('peername') else None
        dest_port = server_conn.get('peername', [None, None])[1] if server_conn.get('peername') else None
        host = req.get('host', '').lower()
        client_ip = flow.get('client_conn', {}).get('peername', [None])[0] if flow.get('client_conn') else None

        if target_ip and client_ip and client_ip != target_ip:
            continue

        conn_entry = {
            'client': client_ip,
            'host': host,
            'dest_ip': dest_ip,
            'dest_port': dest_port,
            'scheme': req.get('scheme', 'http'),
            'path': req.get('path', '/'),
        }
        connections.append(conn_entry)

        # 1. Direct IP connection check (no prior DNS lookup)
        if dest_ip and dest_ip not in resolved_ips_to_domains:
            if not dest_ip.startswith('127.') and not dest_ip.startswith('10.') and not dest_ip.startswith('192.168.'):
                anomalies.append({
                    'type': 'DIRECT_IP_CONNECTION',
                    'severity': 'HIGH',
                    'detail': f'Target connected directly to IP {dest_ip}:{dest_port} with no prior DNS resolution (hardcoded fallback indicator)',
                    'dest_ip': dest_ip,
                    'port': dest_port,
                })

        # 2. DoH / DoT detection
        if dest_ip in DOH_PROVIDERS:
            anomalies.append({
                'type': 'ENCRYPTED_DNS_BYPASS',
                'severity': 'HIGH',
                'detail': f'Detected connection to known DoH/DoT resolver: {dest_ip} ({DOH_PROVIDERS[dest_ip]})',
                'dest_ip': dest_ip,
                'provider': DOH_PROVIDERS[dest_ip]
            })

        # 3. Domain fronting / SNI mismatch check
        if dest_ip and dest_ip in resolved_ips_to_domains:
            dns_domains = resolved_ips_to_domains[dest_ip]
            if host and host not in dns_domains:
                anomalies.append({
                    'type': 'SNI_DOMAIN_MISMATCH',
                    'severity': 'MEDIUM',
                    'detail': f'TLS/HTTP host "{host}" differs from resolved DNS domain(s): {list(dns_domains)} on IP {dest_ip}',
                    'host': host,
                    'dns_domains': list(dns_domains),
                    'dest_ip': dest_ip
                })

    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'target_filter': target_ip or 'all',
        'dns_query_count': len(dns_queries),
        'observed_flows': len(connections),
        'unique_domains_queried': list(dns_map.keys()),
        'anomalies_detected': len(anomalies),
        'anomalies': anomalies,
    }


def main():
    parser = argparse.ArgumentParser(description='Cross-layer DNS and TLS traffic correlation')
    parser.add_argument('--target', help='Filter analysis for a specific target device IPv4')
    parser.add_argument('--save', action='store_true', help='Save report to data/analysis/ for MCP evidence indexing')
    parser.add_argument('--json', action='store_true', help='Output raw JSON to stdout')
    args = parser.parse_args()

    settings = load_env()
    target_ip = args.target or settings.get('TARGET_IP')

    dns_queries = fetch_adguard_queries(settings, target_ip)
    http_flows = fetch_mitmproxy_flows()
    report = correlate(dns_queries, http_flows, target_ip)

    if args.save:
        out_dir = ROOT / 'data/analysis'
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        tgt_slug = (target_ip or 'all').replace('.', '_')
        out_file = out_dir / f'correlation_{tgt_slug}_{ts}.json'
        out_file.write_text(json.dumps(report, indent=2))
        report['saved_evidence_path'] = str(out_file)
        print(f"Evidence report saved to: {out_file}", file=sys.stderr)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    # Formatted terminal display
    print("=" * 65)
    print("         RELab Cross-Layer DNS & TLS Correlation")
    print("=" * 65)
    print(f"Target Filter       : {report['target_filter']}")
    print(f"DNS Queries Audited : {report['dns_query_count']}")
    print(f"HTTP/TLS Flows      : {report['observed_flows']}")
    print(f"Domains Queried     : {len(report['unique_domains_queried'])}")
    print(f"Anomalies Detected  : {report['anomalies_detected']}")
    print("-" * 65)

    if report['anomalies']:
        print("DETECTED ANOMALIES & EVASION ATTEMPTS:")
        for idx, a in enumerate(report['anomalies'], 1):
            print(f"  [{idx}] [{a['severity']}] {a['type']}")
            print(f"      {a['detail']}")
    else:
        print("No traffic evasion, DoH bypass, or direct IP connections detected.")
    print("=" * 65)


if __name__ == '__main__':
    main()
