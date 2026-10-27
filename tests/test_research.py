"""Behavior tests for offline research; never open external sockets or require Docker."""
import importlib.util
import json
import sqlite3
import sys
import types
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('device_research',ROOT/'api/research.py')
r=importlib.util.module_from_spec(spec);sys.modules['device_research']=r;spec.loader.exec_module(r)

def init_db(path):
    conn=sqlite3.connect(path)
    conn.execute('CREATE TABLE http_requests(id INTEGER PRIMARY KEY,method TEXT,host TEXT,path TEXT,response_status INTEGER,rule_name TEXT)')
    r.initialize(conn)
    return conn

def test_experiment_rollback_snapshot(tmp_path):
    conn=init_db(tmp_path/'exp.db')
    snap={'rules':[{'name':'baseline'}], 'managed_dns':[], 'scenarios':[]}
    start=r.begin(conn,'TLS-test','Controller checks certificate chain',snap)
    assert start['baseline_event_id']==0
    conn.execute('INSERT INTO http_requests(method,host,path,response_status) VALUES(?,?,?,?)',('POST','api.device.example.test','/v1/discovery',501));conn.commit()
    out=r.finish(conn,start['id'],'Handshake verified')
    assert out['event_count']==1
    obj=r.get_experiment(conn,start['id'])
    assert obj['snapshot']==snap
    assert obj['status']=='finished'
    assert len(r.list_experiments(conn))==1

def test_scenario_state_machine(tmp_path):
    conn=init_db(tmp_path/'machine.db')
    scenarios=[{'id':'pair','enabled':True,'steps':[
        {'method':'POST','host':'api.device.example.test','path_regex':'^/start$','status':200,'body':{'step':1}},
        {'method':'POST','host':'api.device.example.test','path_regex':'^/next$','status':200,'body':{'step':2}},
    ]}]
    assert r.scenario_match(conn,scenarios,'POST','api.device.example.test','/next','192.0.2.10') is None
    assert r.scenario_match(conn,scenarios,'POST','api.device.example.test','/start','192.0.2.10')['body']['step']==1
    assert r.scenario_match(conn,scenarios,'POST','api.device.example.test','/start','192.0.2.10') is None
    assert r.scenario_match(conn,scenarios,'POST','api.device.example.test','/next','192.0.2.10')['body']['step']==2
    assert r.reset_scenarios(conn,'192.0.2.10')==1
    assert r.scenario_match(conn,scenarios,'POST','api.device.example.test','/start','192.0.2.10') is not None


def test_firmware_scan_rejects_parent_and_hashes(tmp_path):
    folder=tmp_path/'firmware';folder.mkdir();p=folder/'firmware.bin'
    p.write_bytes(b'hello https://api.device.example.test\x00random\x00')
    summary=r.firmware_index(p,folder)
    assert summary['sha256']
    assert any('http' in s for s in summary['interesting'])
    outside=tmp_path/'outside.bin';outside.write_bytes(b'whatever')
    import pytest
    with pytest.raises(ValueError):r.firmware_index(outside,folder)


def test_save_and_read_json(tmp_path):
    p=tmp_path/'a'/'b.json';r.save_json(p,{'test':1})
    assert r.read_json(p,None)=={'test':1}
