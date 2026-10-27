"""Device neutrality, rewrite scoping, generic skill and MCP-surface tests."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
profile=SourceFileLoader('device_profiles',str(ROOT/'scripts/device-profile.py')).load_module()
dns=SourceFileLoader('device_dns',str(ROOT/'scripts/dns-rewrite.py')).load_module()

def test_default_profile_has_no_interception():
    assert profile.load_profile('generic')['dns_candidates']==[]
    assert 'TARGET_PROFILE=generic' in (ROOT/'.env.example').read_text()

def test_optional_stadia_profile_is_explicit():
    sample=profile.load_profile('stadia-original')
    assert 'cloudcast-pa.googleapis.com' in sample['dns_candidates']
    assert 'cloudcast-pa.googleapis.com' not in (ROOT/'config/rules.json').read_text()

def test_profile_dns_scoped_and_reversible():
    managed=[{'domain':'otherdevice.example.test','answer':'192.168.2.7'},
             {'domain':'api.device.example.test','answer':'192.168.2.9'}]
    enabled=dns.plan('enable','example-local','192.168.2.20',managed)
    assert '192.168.2.20 api.device.example.test' in enabled
    assert '192.168.2.7 otherdevice.example.test' in enabled
    disabled=dns.plan('disable','example-local',None,managed)
    assert 'api.device.example.test' not in disabled
    assert 'otherdevice.example.test' in disabled

def test_generic_profile_refuses_bulk_enable():
    try:dns.plan('enable','generic','192.168.2.20',[])
    except ValueError as e:assert 'no DNS candidates' in str(e)
    else:raise AssertionError('Generic profile must never enable DNS rewrites')

def test_api_mcp_surface_contains_no_privileged_operations():
    text=(ROOT/'api/main.py').read_text()
    block=text.split('include_operations=[',1)[1].split('],',1)[0]
    for forbidden in ('lab_dns_replace','lab_rules_replace','lab_events_clear',
                      'device_rollback_experiment','device_start_experiment','lab_scenarios_replace'):
        assert forbidden not in block
    assert 'device_experiments_list' in block

def test_generic_skills_identical_across_clients():
    a=ROOT/'.agents/skills'
    skills=sorted(a.glob('*/SKILL.md'))
    assert len(skills)>=36
    for f in skills:
        assert 'Stadia' not in f.read_text()
        for root in ('skills','.claude/skills'):
            assert f.read_text()==(ROOT/root/f.parent.name/'SKILL.md').read_text()

def test_api_has_read_only_profile_endpoint():
    source=(ROOT/'api/main.py').read_text()
    assert "operation_id='lab_active_profile'" in source
    assert 'automatic_dns_changes' in source
    assert '"lab_active_profile"' in source.split('include_operations=[',1)[1]
