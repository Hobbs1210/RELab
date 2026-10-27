"""FastAPI route smoke via stubbed MCP registration (real MCP handshake is a host test)."""
import importlib
import json
import sys
import types
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

@pytest.fixture
def app_module(tmp_path, monkeypatch):
    repo=Path(__file__).resolve().parents[1]
    monkeypatch.setenv('DB_PATH',str(tmp_path/'requests.db'))
    monkeypatch.setenv('RULES_PATH',str(tmp_path/'rules.json'))
    monkeypatch.setenv('SCENARIOS_PATH',str(tmp_path/'scenarios.json'))
    monkeypatch.setenv('OWNED_DNS_PATH',str(tmp_path/'owned.json'))
    monkeypatch.setenv('ANALYSIS_PATH',str(tmp_path/'analysis'))
    monkeypatch.setenv('FIRMWARE_PATH',str(tmp_path/'firmware'))
    monkeypatch.setenv('LAB_ADMIN_TOKEN','super-secret-test-token')
    class FakeMcp:
        def __init__(self,*args,**kwargs):pass
        def mount_http(self,*args,**kwargs):pass
    monkeypatch.setitem(sys.modules,'fastapi_mcp',types.SimpleNamespace(FastApiMCP=FakeMcp))
    sys.path.insert(0,str(repo/'api'))
    for m in ['main','research']:sys.modules.pop(m,None)
    app=importlib.import_module('main')
    yield app
    sys.path.remove(str(repo/'api'))
    for m in ['main','research']:sys.modules.pop(m,None)


def test_control_plane_auth_and_stateful_mock(app_module):
    c=TestClient(app_module.app)
    assert c.get('/__lab__/health').status_code==200
    assert c.put('/__lab__/scenarios',json=[]).status_code==403
    auth={'X-Lab-Token':'super-secret-test-token'}
    scenario=[{'id':'demo','enabled':True,'steps':[{'method':'POST','host':'example.com','path_regex':'^/start$','body':{'stage':1},'status':202}]}]
    assert c.put('/__lab__/scenarios',headers=auth,json=scenario).status_code==200
    eid=c.post('/__lab__/experiments',headers=auth,json={'name':'demo','hypothesis':'test'}).json()['id']
    response=c.post('/start',headers={'host':'example.com'})
    assert response.status_code==202 and response.json()=={'stage':1}
    assert c.post('/start',headers={'host':'example.com'}).status_code==501
    assert c.post('/__lab__/experiments/'+eid+'/finish',headers=auth,json={'result':'good'}).json()['event_count']==2
    assert c.post('/__lab__/experiments/'+eid+'/rollback',headers=auth,json={}).status_code in (200,502) # no live AdGuard


def test_secret_headers_redacted(app_module):
    c=TestClient(app_module.app)
    c.post('/sensitive',headers={'host':'example.com','Authorization':'Bearer sensitive-secret','Cookie':'secret=abc'})
    events=c.get('/__lab__/events').json()['events']
    h=json.loads(events[0]['headers'])
    assert h['authorization']=='[REDACTED]'
    assert h['cookie']=='[REDACTED]'


def test_dns_preserves_unmanaged(app_module,monkeypatch,tmp_path):
    server={('unrelated.example','192.0.2.1')}
    def fake(endpoint,payload=None):
        if endpoint=='rewrite/list':return [{'domain':d,'answer':a} for d,a in server]
        if endpoint=='rewrite/add':server.add((payload['domain'],payload['answer']))
        if endpoint=='rewrite/delete':server.discard((payload['domain'],payload['answer']))
        return {}
    monkeypatch.setattr(app_module,'adguard_call',fake)
    c=TestClient(app_module.app);h={'X-Lab-Token':'super-secret-test-token'}
    assert c.put('/__lab__/dns',headers=h,json={'hosts':'192.0.2.4 api.device.example.test'}).status_code==200
    assert ('unrelated.example','192.0.2.1') in server
    assert ('api.device.example.test','192.0.2.4') in server
    assert c.put('/__lab__/dns',headers=h,json={'hosts':''}).status_code==200
    assert server=={('unrelated.example','192.0.2.1')}
