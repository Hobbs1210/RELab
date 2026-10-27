#!/usr/bin/env python3
"""Wireshark extcap adapter: replay a chosen local PCAP as an external capture source.
Not a live radio capture and does not run privileged system commands.
"""
import argparse,os,sys,shutil
from pathlib import Path
p=argparse.ArgumentParser(add_help=False)
p.add_argument('--extcap-interfaces',action='store_true');p.add_argument('--extcap-dlts',action='store_true')
p.add_argument('--extcap-interface');p.add_argument('--extcap-config',action='store_true')
p.add_argument('--capture',action='store_true');p.add_argument('--fifo');p.add_argument('--pcap')
a,_=p.parse_known_args()
if a.extcap_interfaces:print('extcap {version=1.0}{help=https://www.wireshark.org/docs/wsug_html_chunked/ChapterCapture.html}\ninterface {value=device_re_saved}{display=Device RE Lab saved PCAP (offline replay)}')
elif a.extcap_dlts:print('dlt {number=1}{name=EN10MB}{display=Ethernet (requires compatible input PCAP)}')
elif a.extcap_config:print('arg {number=0}{call=--pcap}{display=Saved capture path}{type=fileselect}{required=true}')
elif a.capture:
    if a.extcap_interface!='device_re_saved' or not a.fifo or not a.pcap:sys.exit('Choose a saved PCAP and FIFO')
    inp=Path(a.pcap).resolve();root=Path(os.environ.get('DEVICE_RE_CAPTURE_DIR','/opt/RELab/data/pcaps')).resolve()
    if not inp.is_relative_to(root) or inp.suffix.lower()!='.pcap' or not inp.is_file() or inp.is_symlink() or inp.stat().st_size>256*1024*1024:sys.exit('Input PCAP not allowed')
    with inp.open('rb') as src,open(a.fifo,'wb',buffering=0) as dst:shutil.copyfileobj(src,dst,1024*1024)
