#!/usr/bin/env python3
"""Deterministic offline PCAP indexing; run inside analyzer with Zeek and TShark.
Never executes arbitrary shell strings; never sends packets.
"""
import argparse, hashlib, json, os, pathlib, subprocess, time
CAP=pathlib.Path('/captures'); OUT=pathlib.Path('/analysis')
MAX_BYTES=int(os.getenv('MAX_PCAP_BYTES','209715200'))

def run(cmd,cwd=None,timeout=120):
    return subprocess.run(cmd,cwd=cwd,timeout=timeout,check=False,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)

def analyze(pcap):
    p=pathlib.Path(pcap).resolve()
    if not p.is_relative_to(CAP.resolve()) or not p.is_file() or p.suffix.lower() not in ('.pcap','.pcapng'):
        raise ValueError('PCAP must be inside /captures')
    if p.stat().st_size>MAX_BYTES: raise ValueError('PCAP exceeds configured limit')
    digest=hashlib.sha256(p.read_bytes()).hexdigest()
    dest=OUT / digest[:16];dest.mkdir(parents=True,exist_ok=True)
    zeek=run(['zeek','-r',str(p),'LogAscii::use_json=T'],cwd=dest)
    fields=['frame.time_epoch','ip.src','ip.dst','_ws.col.Protocol','tcp.dstport','udp.dstport']
    tshark=run(['tshark','-r',str(p),'-T','fields', *sum((['-e',x] for x in fields),[]),'-c','2000'],timeout=120)
    (dest/'packets.tsv').write_text(tshark.stdout)
    stun=run(['tshark','-r',str(p),'-Y','stun || dtls || rtp || tls','-T','fields',
              '-e','frame.number','-e','_ws.col.Protocol','-e','ip.src','-e','ip.dst','-e','udp.dstport','-c','1000'],timeout=120)
    (dest/'transport.tsv').write_text(stun.stdout)
    sample=tshark.stdout.splitlines()[:2000]
    stats={}
    for line in sample:
        parts=line.split('\t'); protocol=parts[3] if len(parts)>3 else '?';stats[protocol]=stats.get(protocol,0)+1
    counts={}
    for name in ('conn','dns','ssl','http','weird','notice','files'):
        file=dest/f'{name}.log'
        if file.exists():
            counts[name]=len(file.read_text(errors='replace').splitlines())
    result={'file':p.name,'sha256':digest,'bytes':p.stat().st_size,'zeek_returncode':zeek.returncode,'zeek_error':zeek.stderr[-1500:], 'tshark_returncode':tshark.returncode,'protocol_sample':stats,'zeek_records':counts,'artifact_dir':digest[:16],'captured_rows_sampled':len(sample),'transport_rows_sampled':len(stun.stdout.splitlines()),'transport_tshark_returncode':stun.returncode}
    (dest/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    cli=argparse.ArgumentParser();cli.add_argument('mode',choices=['once','watch','file']);cli.add_argument('file',nargs='?');args=cli.parse_args()
    OUT.mkdir(exist_ok=True,parents=True)
    if args.mode=='file':
        print(json.dumps(analyze(args.file),indent=2));return
    while True:
        for p in sorted(CAP.glob('*')):
            if p.suffix.lower() not in ('.pcap','.pcapng') or not p.is_file():continue
            if time.time()-p.stat().st_mtime < 15: continue # skip active writers
            target=OUT/hashlib.sha256(p.read_bytes()).hexdigest()[:16]/'summary.json'
            if target.exists(): continue
            try: print(json.dumps(analyze(p)),flush=True)
            except Exception as e: print(f'PCAP skipped: {p.name}: {e}',flush=True)
        if args.mode=='once':break
        time.sleep(15)
if __name__=='__main__':main()
