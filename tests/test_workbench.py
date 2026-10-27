"""No Docker or attached hardware needed; synthetic data only."""
import base64,importlib,json,sqlite3,sys,types
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workbench'))
from engine import protocols,decode_bytes,infer,firmware_arch,compare_firmware,openapi_from_events,sdk_sources
from timeline import events
from hardware import enumerate_hardware

def test_protocol_registry_and_decoding():
    registry=protocols(ROOT/'protocols')
    assert {'mqtt','coap','grpc','example-len16'}<=set(registry)
    result=decode_bytes(b'\x00\x03abc\x00\x02de',registry['example-len16'])
    assert [f['hex'] for f in result['frames']]==['616263','6465']
    assert decode_bytes(b'\x30\x03abc',registry['mqtt'])['frames'][0]['packet_type']==3
    assert decode_bytes(b'\x00\x00\x00\x00\x03abc',registry['grpc'])['frames'][0]['hex']=='616263'
    with pytest.raises(ValueError):decode_bytes(bytes(65537),registry['raw'])

def test_binary_field_inference_and_firmware():
    r=infer([b'\x00\x03abc',b'\x00\x03xyz'])
    assert any(h['type']=='length-prefix' for h in r['candidate_fields'])
    assert r['sample_count']==2
    elf=bytearray(64);elf[:4]=b'\x7fELF';elf[5]=1;elf[18:20]=(183).to_bytes(2,'little')
    assert firmware_arch(bytes(elf))['candidates'][0]['architecture']=='AArch64'
    r=compare_firmware(b'abcdef',b'abZdef')
    assert r['changed_ranges_first_200']==[{'start':2,'end':3}]

def test_sdk_generation_is_not_certification():
    spec=openapi_from_events([{'id':4,'method':'GET','path':'/status?foo=3','response_status':200},
                              {'id':5,'method':'POST','path':'/start','response_status':201}])
    assert '/status' in spec['paths']
    s=sdk_sources(spec)
    for lang in ('python','typescript','csharp'):
        assert 'start' in s[lang]
    assert s['operation_count']==2
    assert 'unverified' in s['warning'].lower()

def test_timeline_correlation(tmp_path):
    db=tmp_path/'requests.db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE http_requests(id integer,ts text,source_ip text, method text, host text, path text, response_status int)')
        conn.execute("INSERT INTO http_requests VALUES(1,'2026-01-01T00:00:01+00:00','192.0.2.4','GET','example','/status',200)")
    d=tmp_path/'analysis'/'abcd123456781234';d.mkdir(parents=True)
    (d/'summary.json').write_text('{}')
    (d/'dns.log').write_text(json.dumps({'ts':1767225600,'query':'example','id.orig_h':'192.0.2.4'})+'\n')
    r=events(db,tmp_path/'analysis',limit=10)
    assert [row['kind'] for row in r['events']]==['dns','http']
    assert all(row['evidence'] for row in r['events'])

def test_workbench_api_mcp_only_reads(tmp_path,monkeypatch):
    monkeypatch.setenv('DB_PATH',str(tmp_path/'requests.db'))
    monkeypatch.setenv('FIRMWARE_PATH',str(tmp_path/'firmware'))
    monkeypatch.setenv('PROTOCOLS_PATH',str(tmp_path/'protocols'))
    monkeypatch.setenv('OUTPUT_PATH',str(tmp_path/'out'))
    monkeypatch.setenv('ANALYSIS_PATH',str(tmp_path/'analysis'))
    monkeypatch.setenv('LAB_ADMIN_TOKEN','test-token')
    (tmp_path/'firmware').mkdir();(tmp_path/'firmware'/'test.bin').write_bytes(b'abc')
    class FakeMcp:
        def __init__(self,*a,**k):self.operations=k.get('include_operations',[])
        def mount_http(self,**k):pass
    monkeypatch.setitem(sys.modules,'fastapi_mcp',types.SimpleNamespace(FastApiMCP=FakeMcp))
    sys.modules.pop('main',None)
    module=importlib.import_module('main')
    c=TestClient(module.app)
    assert c.get('/v1/health').json()['status']=='ok'
    assert c.get('/v1/firmware/test.bin/architecture').status_code==200
    assert c.get('/v1/firmware/../architecture').status_code in (404,400)
    assert c.post('/v1/exports').status_code==403
    assert c.post('/v1/exports',headers={'X-Lab-Token':'test-token'}).status_code==200
    assert (tmp_path/'out'/'DeviceClient.ts').exists()
    assert all(not name.startswith('workbench_register') for name in module.workbench_mcp.operations)
    sys.modules.pop('main',None)
