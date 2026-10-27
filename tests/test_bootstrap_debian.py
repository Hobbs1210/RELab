"""Offline checks for RELab's headless GitHub bootstrap flow.

These checks do not require root, Docker, network access or a Debian VM.
"""
import importlib
import os
import sys
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=['bootstrap-debian.sh','install-debian.sh','install-code-server.sh']


def _bash_cmd():
    if os.name == 'nt':
        git_bash = Path(os.environ.get('ProgramFiles', r'C:\Program Files')) / 'Git' / 'bin' / 'bash.exe'
        if git_bash.exists():
            return str(git_bash)
    return 'bash'


def test_debian_scripts_parse_and_have_help():
    bash = _bash_cmd()
    for name in SCRIPTS:
        path=ROOT/'scripts'/name
        subprocess.run([bash,'-n',str(path)],check=True)
        result=subprocess.run([bash,str(path),'--help'],capture_output=True,text=True,check=True)
        assert '--user' in result.stdout


def test_debian_scripts_create_re_user_with_passwordless_sudo():
    for name in ['bootstrap-debian.sh', 'install-debian.sh']:
        body = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
        assert 'id "re"' in body
        assert 'useradd -m -s /bin/bash' in body
        assert 're ALL=(ALL:ALL) NOPASSWD: ALL' in body
        assert '/etc/sudoers.d/re' in body
        assert '0440' in body


def test_debian_scripts_re_password_and_unattended_apt():
    for name in ['bootstrap-debian.sh', 'install-debian.sh', 'install-code-server.sh']:
        body = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
        assert '--force-confdef' in body
        assert '--force-confold' in body

    install_body = (ROOT / 'scripts/install-debian.sh').read_text(encoding='utf-8')
    assert 'chpasswd' in install_body
    assert 'ADGUARD_USERNAME' in install_body
    assert 'RELab Credentials & Access Summary' in install_body


def test_scripts_port_53_resolution_and_collision_check():
    for name in ['bootstrap-debian.sh', 'install-debian.sh', 'setup.sh']:
        body = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
        assert 'DNSStubListener=no' in body

    setup_body = (ROOT / 'scripts/setup.sh').read_text(encoding='utf-8')
    assert 'Notice [Port Check]' in setup_body


def test_safe_atomic_env_updates():
    for name in ['install-debian.sh', 'setup.sh']:
        body = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
        assert '.env.bak' in body
        assert 'os.replace' in body


def test_hardware_preflight_checks():
    for name in ['bootstrap-debian.sh', 'install-debian.sh']:
        body = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
        assert '/proc/meminfo' in body
        assert 'MemTotal:' in body
        assert 'NOTICE [Pre-flight]' in body


def test_bootstrap_clones_expected_public_repository_and_deploys():
    body=(ROOT/'scripts/bootstrap-debian.sh').read_text()
    assert 'https://github.com/Hobbs1210/RELab.git' in body
    assert 'git clone' in body
    assert 'git -C "$INSTALL_DIR" merge --ff-only' in body
    assert 'scripts/install-debian.sh' in body


def test_editor_is_loopback_and_opens_checkout():
    body=(ROOT/'scripts/install-code-server.sh').read_text()
    assert '127.0.0.1:$PORT' in body
    assert '--auth password $WORKSPACE' in body
    assert 'WorkingDirectory=$WORKSPACE' in body
    assert 'relab-code-server.service' in body


def test_documentation_contains_curl_bootstrap():
    body=(ROOT/'README.md').read_text()
    assert 'raw.githubusercontent.com/Hobbs1210/RELab/main/scripts/bootstrap-debian.sh' in body
    assert 'sudo bash /tmp/relab-bootstrap.sh --user "$USER"' in body
    assert '/opt/RELab' in body


def test_adguard_setup_redirect_handling():
    setup_body = (ROOT / 'scripts/setup.sh').read_text(encoding='utf-8')
    assert 'NoRedirect' in setup_body
    assert 'HTTPRedirectHandler' in setup_body
    assert 'e.code not in (404, 400, 302)' in setup_body


def test_ssh_key_provisioning_supported():
    for name in ['bootstrap-debian.sh', 'install-debian.sh']:
        body = (ROOT / 'scripts' / name).read_text(encoding='utf-8')
        assert '--ssh-key' in body
        assert 'authorized_keys' in body


def test_uninstall_script_parses_and_has_help():
    bash = _bash_cmd()
    path = ROOT / 'scripts/uninstall-debian.sh'
    assert path.is_file()
    subprocess.run([bash, '-n', str(path)], check=True)
    res = subprocess.run([bash, str(path), '--help'], capture_output=True, text=True, check=True)
    assert '--apply' in res.stdout
    assert '--purge-data' in res.stdout


def test_gateway_dns_supports_status_and_timeout():
    body = (ROOT / 'scripts/gateway-dns.sh').read_text(encoding='utf-8')
    assert 'status' in body
    assert '--timeout' in body


def test_labctl_status_and_profile_commands():
    body = (ROOT / 'scripts/labctl.py').read_text(encoding='utf-8')
    assert "'status'" in body
    assert "'set-profile'" in body


def test_download_firmware_supports_registration():
    body = (ROOT / 'scripts/download-firmware.py').read_text(encoding='utf-8')
    assert '--register' in body
    assert '_register_with_research_hub' in body


def test_setup_subcommands_supported():
    body = (ROOT / 'scripts/setup.sh').read_text(encoding='utf-8')
    assert 'backup)' in body
    assert 'status)' in body
    assert 'restart)' in body


def test_claude_registration_script():
    bash = _bash_cmd()
    path = ROOT / 'scripts/register-claude.sh'
    assert path.is_file()
    subprocess.run([bash, '-n', str(path)], check=True)
    body = path.read_text(encoding='utf-8')
    assert 'device-dns' in body
    assert 'device-research' in body
    assert 'device-workbench' in body


def test_stream_pcap_script():
    bash = _bash_cmd()
    path = ROOT / 'scripts/stream-pcap.sh'
    assert path.is_file()
    subprocess.run([bash, '-n', str(path)], check=True)
    res = subprocess.run([bash, str(path), '--help'], capture_output=True, text=True, check=True)
    assert '--host' in res.stdout
    assert '--filter' in res.stdout


def test_export_ca_script():
    bash = _bash_cmd()
    path = ROOT / 'scripts/export-ca.sh'
    assert path.is_file()
    subprocess.run([bash, '-n', str(path)], check=True)
    body = path.read_text(encoding='utf-8')
    assert 'device-mitm-ca.crt' in body
    assert 'android' in body


def test_correlate_traffic_anomalies_detection():
    sys.path.insert(0, str(ROOT / 'scripts'))
    correlate_traffic = importlib.import_module('correlate-traffic')

    dns_sample = [
        {'question': {'name': 'api.vendor.com'}, 'client': '192.0.2.10', 'answer': [{'value': '93.184.216.34'}]}
    ]
    flow_sample = [
        # Normal resolved flow
        {'client_conn': {'peername': ['192.0.2.10', 49152]}, 'server_conn': {'peername': ['93.184.216.34', 443]},
         'request': {'host': 'api.vendor.com', 'scheme': 'https', 'path': '/v1/config'}},
        # Direct IP connection (not in DNS)
        {'client_conn': {'peername': ['192.0.2.10', 49153]}, 'server_conn': {'peername': ['198.51.100.5', 443]},
         'request': {'host': '198.51.100.5', 'scheme': 'https', 'path': '/heartbeat'}},
        # DoH bypass attempt
        {'client_conn': {'peername': ['192.0.2.10', 49154]}, 'server_conn': {'peername': ['1.1.1.1', 443]},
         'request': {'host': 'cloudflare-dns.com', 'scheme': 'https', 'path': '/dns-query'}},
    ]
    report = correlate_traffic.correlate(dns_sample, flow_sample, target_ip='192.0.2.10')
    assert report['dns_query_count'] == 1
    assert report['observed_flows'] == 3
    assert report['anomalies_detected'] >= 2
    types = [a['type'] for a in report['anomalies']]
    assert 'DIRECT_IP_CONNECTION' in types
    assert 'ENCRYPTED_DNS_BYPASS' in types


def test_react_dashboard_bundle():
    ui_path = ROOT / 'api/ui.html'
    assert ui_path.is_file()
    content = ui_path.read_text(encoding='utf-8')
    assert 'RELab' in content
    assert 'root' in content
    assert len(content) > 50000  # Built single-file React bundle


