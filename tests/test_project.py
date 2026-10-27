from pathlib import Path
import json
import tomllib

ROOT=Path(__file__).resolve().parents[1]

def test_nine_common_mcp_names():
    a=json.loads((ROOT/'.agents/mcp_config.json').read_text())['mcpServers']
    b=json.loads((ROOT/'.vscode/mcp.json').read_text())['servers']
    c=tomllib.loads((ROOT/'.codex/config.toml').read_text())['mcp_servers']
    assert len(a)==9
    assert set(a)==set(b)==set(c)


def test_five_agent_skills():
    skills=list((ROOT/'.agents/skills').glob('*/SKILL.md'))
    assert len(skills)>=5
    for skill in skills:
        assert f'name: {skill.parent.name}' in skill.read_text()


def test_edge_blocks_mcp_exposure():
    s=(ROOT/'nginx/default.conf').read_text()
    assert 'location = /mcp { return 404; }' in s
    assert 'location ^~ /mcp/ { return 404; }' in s


def test_emulator_mcp_mount_precedes_catchall():
    s=(ROOT/'api/main.py').read_text()
    assert s.index('lab_mcp.mount_http(mount_path="/mcp")') < s.index('@app.api_route("/{path:path}"')


def test_capture_tcpdump_single_command():
    import yaml
    d=yaml.safe_load((ROOT/'compose.yaml').read_text())
    assert "-w '/captures/" in d['services']['capture']['command'][-1]
