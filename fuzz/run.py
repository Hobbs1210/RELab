"""Bounded, lab-only stateful boofuzz demonstration.

Network connection is deliberately fixed to Compose hostname `api`, not a user URL.
This fuzzes ONLY the Device RE Lab mock API on the isolated Docker network.
"""
import os
from pathlib import Path
from boofuzz import Session,Target,TCPSocketConnection,Request,Static,String

def main():
    host=os.environ.get('FUZZ_TARGET','api')
    port=int(os.environ.get('FUZZ_PORT','8000'))
    if host!='api' or port!=8000:raise SystemExit('FUZZ_TARGET must be api:8000; hardware or outside network targets are not allowed by this container')
    maximum=int(os.environ.get('FUZZ_MAX_CASES','100'))
    if not 1<=maximum<=1000:raise SystemExit('FUZZ_MAX_CASES must be 1..1000')
    Path('/results').mkdir(parents=True,exist_ok=True)
    sess=Session(target=Target(connection=TCPSocketConnection(host,port)),index_end=maximum,
                 sleep_time=0.02,web_port=None,keep_web_open=False,
                 db_filename='/results/boofuzz-results.db',restart_threshold=2,
                 receive_data_after_fuzz=True)
    # Two-state sequence: immutable setup followed by varied message. This is an example,
    # not automatic discovery of a vendor protocol.
    setup=Request('setup',children=(Static('setup_request', 'POST /__fuzz__/setup HTTP/1.1\r\nHost: lab.local\r\nContent-Length: 0\r\nConnection: close\r\n\r\n'),))
    action=Request('action',children=(Static('request_prefix', 'GET /__fuzz__/'),String('path_fragment',default_value='status',max_len=128),Static('request_suffix',' HTTP/1.1\r\nHost: lab.local\r\nConnection: close\r\n\r\n')))
    sess.connect(setup)
    sess.connect(setup,action)
    sess.fuzz(max_depth=1)
if __name__=='__main__':main()
