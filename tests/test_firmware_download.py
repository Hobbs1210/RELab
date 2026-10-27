"""No network operations. Synthetic HTTPS responses only."""
import hashlib
import importlib
import json
import socket
import sys
import types
from pathlib import Path
from unittest.mock import patch
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workbench'))
import firmware_download as d

class FakeResponse:
    def __init__(self,body=b'abc',status=200,headers=None):
        self.data=body
        self.status=status
        self.headers=headers or {}
        self.index=0
    def getheader(self,key):return self.headers.get(key)
    def read(self,size):
        chunk=self.data[self.index:self.index+size]
        self.index+=len(chunk)
        return chunk

class FakeConnection:
    response=FakeResponse()
    def __init__(self,host,port,addresses):
        self.host=host;self.addresses=addresses
    def request(self,method,path,headers):
        assert self.host=='firmware.example.com'
        assert method=='GET'
        assert path=='/firmware.bin?temporary=secret'
    def getresponse(self):return self.response
    def close(self):pass


def test_block_ssrf_and_insecure_urls(monkeypatch):
    def resolver(host,port,**kw):
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))]
    monkeypatch.setattr(d.socket,'getaddrinfo',resolver)
    for url in ('http://firmware.example.com/a.bin','https://127.0.0.1/admin',
                'https://firmware.example.com:8443/a.bin',
                'https://u:pass@firmware.example.com/a.bin','https://firmware.example.com/a.bin#secret'):
        with pytest.raises(d.DownloadError):d._resolve_public_https(url)
    with pytest.raises(d.DownloadError):d.download_firmware('https://firmware.example.com/firmware.bin',Path('/tmp'),filename='../x')


def test_validated_firmware_and_privacy(monkeypatch,tmp_path):
    def resolver(host,port,**kw):
        return [(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.215.14',443))]
    monkeypatch.setattr(d.socket,'getaddrinfo',resolver)
    monkeypatch.setattr(d,'PinnedHTTPSConnection',FakeConnection)
    FakeConnection.response=FakeResponse(b'abc',headers={'Content-Type':'application/octet-stream','Content-Length':'3'})
    digest=hashlib.sha256(b'abc').hexdigest()
    result=d.download_firmware('https://firmware.example.com/firmware.bin?temporary=secret',tmp_path,
                               filename='device-v1.bin',expected_sha256=digest)
    assert result['checksum_verified']
    assert result['sha256']==digest
    assert (tmp_path/'device-v1.bin').read_bytes()==b'abc'
    assert 'temporary=secret' not in (tmp_path/'device-v1.bin.json').read_text()
    assert result['source']=='https://firmware.example.com/firmware.bin'
    with pytest.raises(d.DownloadError):
        d.download_firmware('https://firmware.example.com/firmware.bin?temporary=secret',tmp_path,filename='device-v1.bin')


def test_mismatch_and_size_limits_remove_temporary(monkeypatch,tmp_path):
    monkeypatch.setattr(d.socket,'getaddrinfo',lambda *a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.215.14',443))])
    monkeypatch.setattr(d,'PinnedHTTPSConnection',FakeConnection)
    FakeConnection.response=FakeResponse(b'abcdef')
    with pytest.raises(d.DownloadError,match='SHA-256 mismatch'):
        d.download_firmware('https://firmware.example.com/firmware.bin?temporary=secret',tmp_path,
                            filename='no.bin',expected_sha256='a'*64)
    assert list(tmp_path.iterdir())==[]
    FakeConnection.response=FakeResponse(b'abcdef')
    with pytest.raises(d.DownloadError,match='maximum'):
        d.download_firmware('https://firmware.example.com/firmware.bin?temporary=secret',tmp_path,
                            filename='oversize.bin',max_bytes=4)
    assert list(tmp_path.iterdir())==[]


def test_workbench_token_required_and_mcp_stays_readonly(monkeypatch,tmp_path):
    from fastapi.testclient import TestClient
    monkeypatch.setenv('FIRMWARE_PATH',str(tmp_path/'firmware'))
    monkeypatch.setenv('LAB_ADMIN_TOKEN','test-only-token')
    class FakeMcp:
        def __init__(self,*a,**k):self.operations=k.get('include_operations',[])
        def mount_http(self,**k):pass
    monkeypatch.setitem(sys.modules,'fastapi_mcp',types.SimpleNamespace(FastApiMCP=FakeMcp))
    sys.modules.pop('main',None)
    module=importlib.import_module('main')
    client=TestClient(module.app)
    assert client.post('/v1/firmware/download',json={'url':'https://example.com/image.bin'}).status_code==403
    assert 'workbench_download_firmware' not in module.workbench_mcp.operations
    # Guarded API rejects malformed URL without networking.
    r=client.post('/v1/firmware/download',json={'url':'http://localhost/a.bin'},headers={'x-lab-token':'test-only-token'})
    assert r.status_code==400
    sys.modules.pop('main',None)
