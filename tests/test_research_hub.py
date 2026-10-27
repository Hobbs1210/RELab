"""MVP integration tests exercise the actual research store and queue offline."""
from __future__ import annotations
import importlib,sys,json,sqlite3,types,io,zipfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture()
def research(tmp_path,monkeypatch):
    sys.path.insert(0,str(ROOT/'research-hub'))
    import research_models as models, research_core as core, research_ingest as ingest
    monkeypatch.setenv('RESEARCH_DATABASE_URL','sqlite:///'+str(tmp_path/'research.db'))
    monkeypatch.setenv('LAB_ADMIN_TOKEN','testing-private-token')
    monkeypatch.setattr(core,'ROOT',tmp_path/'store')
    monkeypatch.setattr(core,'INPUT',tmp_path/'inputs')
    monkeypatch.setattr(ingest,'INPUT',tmp_path/'inputs')
    models.configure()
    yield models,core,ingest,tmp_path


def test_projects_artifacts_and_evidence_are_separated(research):
    models,core,ingest,tmp=research
    (tmp/'inputs/firmware').mkdir(parents=True)
    (tmp/'inputs/firmware/sample.bin').write_bytes(b'\x7fELF data https://api.example.net/v1:Discover\x00')
    with models.Session.begin() as s:
        core.create_project(s,'project-a','Project A')
        core.create_project(s,'project-b','Project B')
        core.register_device(s,'project-a','sensor01','Sensor')
        art=core.import_file(s,'project-a','firmware','sample.bin','sensor01')
        sha=art['sha256']
        a=core.evidence(s,'project-a','http','GET /health',fields={'host':'api.example.net'},artifact_id=sha,confidence=.9)
        assert a['id']
        with pytest.raises(ValueError):core.evidence(s,'project-b','http','Wrong project',artifact_id=sha)
        with pytest.raises(ValueError):core.artifact_bytes(s,'project-b',sha)
        with pytest.raises(ValueError):core.import_file(s,'project-b','firmware','../secret')
    with models.Session.begin() as s:
        result=core.firmware_intelligence(s,'project-a',{'sha256':sha})
        assert result['format']=='ELF'
        assert any('example.net' in x for x in result['network_strings'])
        assert core.correlate(s,'project-a',{})['matches']
        # A manifest/report bundle must not contain proprietary firmware by default.
        exported=core.bundle(s,'project-a',{})
        with zipfile.ZipFile(core.ROOT/'exports'/exported['export_name']) as z:
            assert set(z.namelist())=={'manifest.json','report.md'}
            assert sha in z.read('manifest.json').decode()


def test_jobs_and_stored_replay_are_durable(research):
    models,core,ingest,tmp=research
    import worker
    with models.Session.begin() as s:
        e=core.evidence(s,'default','protocol-message','handshake',fields={'action':'hello'})
        r=core.enqueue(s,'default','replay',{'evidence_ids':[e['id']],
            'initial':'idle','transitions':[{'from':'idle','action':'hello','to':'ready'}]})
        job_id=r['id']
    assert worker.process_job()
    with models.Session() as s:
        j=s.get(models.Job,job_id)
        assert j.status=='succeeded'
        assert json.loads(j.result)['final_state']=='ready'
    assert not worker.process_job()
    with models.Session.begin() as s:
        v=core.enqueue(s,'default','recipe',{'name':'protocol-research'})
    assert worker.process_job()
    with models.Session() as s:
        job=s.get(models.Job,v['id'])
        assert job.status=='succeeded'
        output=json.loads(job.result)
        assert output['steps']
        assert any(x['step']=='kaitai' and x['status']=='succeeded' for x in output['steps'])


def test_research_kaitai_dissector_and_bounded_mutations(research):
    models,core,_,tmp=research
    (tmp/'inputs/firmware').mkdir(parents=True)
    (tmp/'inputs/firmware/x.bin').write_bytes(b'\x00\x03abc')
    with models.Session.begin() as s:
        sha=core.import_file(s,'default','firmware','x.bin')['sha256']
        import yaml
        ksy=yaml.safe_load(core.kaitai(s,'default',{'framing':'len16be'})['ksy'])
        assert ksy['seq'][0]['type']=='u2be'
        d=core.dissector(s,'default',{'tcp_port':8765})
        assert '8765' in d['lua']
        mutations=core.mutate(s,'default',{'sha256':sha,'cases':10000})
        assert mutations['cases']==100
        assert mutations['sent_to_device'] is False
        with pytest.raises(ValueError):core.dissector(s,'default',{'tcp_port':80})
        states=core.emulate(s,'default',{'initial':'idle','transitions':[{'from':'idle','action':'hello','to':'ready'}],
                                             'actions':['hello','unknown']})
        assert states['final_state']=='ready' and states['offline_only']


def test_legacy_http_and_zeek_observations_are_imported_once(research):
    models,core,ingest,tmp=research
    d=tmp/'inputs/api';d.mkdir(parents=True)
    with sqlite3.connect(d/'requests.db') as con:
        con.execute('CREATE TABLE http_requests(id integer,ts text,source_ip text,method text,host text,path text,response_status integer)')
        con.execute("INSERT INTO http_requests VALUES (1,'2026-10-27T14:00:00+00:00','192.0.2.9','GET','home.test','/api?token=sensitive',200)")
    logs=tmp/'inputs/analysis'/'batch-01';logs.mkdir(parents=True)
    (logs/'dns.log').write_text(json.dumps({'ts':1793110000,'query':'home.test','id.orig_h':'192.0.2.9'})+'\n')
    with models.Session.begin() as s:
        result=ingest.ingest(s)
        assert result=={'http':1,'zeek':1}
    with models.Session.begin() as s:assert ingest.ingest(s)=={'http':0,'zeek':0}
    with models.Session() as s:
        entries=s.scalars(select(models.Evidence).where(models.Evidence.project_id=='default')).all()
        assert len(entries)==2
        assert not any('sensitive' in (x.summary+x.fields) for x in entries)
        assert s.scalar(select(models.Relationship.id)) is not None


def test_api_requires_token_and_mcp_is_readonly(research,monkeypatch):
    models,core,ingest,tmp=research
    class FakeMcp:
        def __init__(self,*args,**kwargs):self.operations=kwargs.get('include_operations',[])
        def mount_http(self,**kwargs):pass
    monkeypatch.setitem(sys.modules,'fastapi_mcp',types.SimpleNamespace(FastApiMCP=FakeMcp))
    import research_api
    with TestClient(research_api.app) as client:
        assert client.get('/v1/projects').status_code==200
        assert client.post('/v1/projects',json={'id':'example','name':'Example'}).status_code==403
        h={'X-Lab-Token':'testing-private-token'}
        assert client.post('/v1/projects',json={'id':'example','name':'Example'},headers=h).status_code==200
        assert client.post('/v1/devices',json={'project_id':'example','id':'sensor','name':'Sensor'},headers=h).status_code==200
        exp=client.post('/v1/experiments',json={'project_id':'example','kind':'emulator-test','params':{'actions':['hello']}},headers=h)
        assert exp.status_code==200
        identifier=exp.json()['id']
        rep=client.post('/v1/experiments/'+identifier+'/reproduce',headers=h)
        assert rep.status_code==200
        assert client.get('/v1/plans?project_id=example').status_code==200
        restore=client.post('/v1/experiments/'+identifier+'/restore',headers=h).json()
        assert restore['dns_rules_changed'] is False
        assert all(not name.endswith(('import','create','change','restore')) for name in research_api.hub_mcp.operations)
        assert 'research_job_status' in research_api.hub_mcp.operations
