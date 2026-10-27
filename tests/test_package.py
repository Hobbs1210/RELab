"""Static tests: deliberately do not require Docker or pull dependencies."""
from __future__ import annotations
import json
from pathlib import Path
import unittest
import yaml
ROOT=Path(__file__).resolve().parents[1]

class PackageTests(unittest.TestCase):
    def test_compose(self):
        c=yaml.safe_load((ROOT/'compose.yaml').read_text())
        self.assertEqual(c['name'],'device-re-lab')
        s=c['services']
        for service in ('dns','mcp-dns','mitm','mcp-wireshark','mcp-ble','mcp-docker','api','https-edge','docker-socket-proxy'):
            self.assertIn(service,s)
            self.assertNotIn('profiles',s[service],f'{service} should be enabled in standard compose')
        # No separate 'mcp-xyz' port published beyond host loopback.
        for name in ('mcp-dns','mitm','mcp-wireshark','mcp-ble','mcp-docker','api'):
            for port in s[name].get('ports',[]):
                self.assertTrue(port.startswith('127.0.0.1:'),f'Bad MCP exposure for {name}: {port}')
        self.assertEqual(s['mcp-docker']['environment']['DOCKER_MCP_SERVER_READONLY'],'true')
        self.assertEqual(s['docker-socket-proxy']['environment']['POST'],'0')
        self.assertEqual(s['mcp-ble']['environment']['BLE_MCP_ALLOW_WRITES'],'${BLE_MCP_ALLOW_WRITES:-false}')

    def test_files_mounted_exist(self):
        c=yaml.safe_load((ROOT/'compose.yaml').read_text())
        for service, spec in c['services'].items():
            if 'build' in spec:
                self.assertTrue((ROOT/(spec['build'] if isinstance(spec['build'],str) else spec['build']['context'])/'Dockerfile').exists(),service)
            for vol in spec.get('volumes',[]):
                source=vol.split(':')[0] if isinstance(vol,str) else ''
                if source.startswith('./'):
                    self.assertTrue((ROOT/source).exists(),f'{service}: {source}')

    def test_mcp_clients_and_skills(self):
        expected={
            'device-dns':'8301','device-mitm':'8302',
            'device-pcap':'8303','device-ble':'8304',
            'device-docker':'8305','device-api':'8090','device-ghidra':'8306','device-workbench':'8310','device-research':'8320'
        }
        config=json.loads((ROOT/'.mcp.json').read_text())['mcpServers']
        self.assertEqual(set(config),set(expected))
        for name,port in expected.items():
            self.assertIn(':'+port,config[name]['url'])
        for target in (ROOT/'.cursor/mcp.json',ROOT/'.vscode/mcp.json'):
            self.assertTrue(target.exists())
            json.loads(target.read_text())
        skills=sorted((ROOT/'skills').glob('*/SKILL.md'))
        self.assertGreaterEqual(len(skills),10)
        for path in skills:
            self.assertTrue(path.read_text().startswith('---\nname:'))
            self.assertEqual(path.read_text(),(ROOT/'.claude/skills'/path.parent.name/'SKILL.md').read_text())
            self.assertEqual(path.read_text(),(ROOT/'.agents/skills'/path.parent.name/'SKILL.md').read_text())

if __name__=='__main__': unittest.main()
