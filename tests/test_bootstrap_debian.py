"""Offline checks for RELab's headless GitHub bootstrap flow.

These checks do not require root, Docker, network access or a Debian VM.
"""
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=['bootstrap-debian.sh','install-debian.sh','install-code-server.sh']


def test_debian_scripts_parse_and_have_help():
    for name in SCRIPTS:
        path=ROOT/'scripts'/name
        subprocess.run(['bash','-n',str(path)],check=True)
        result=subprocess.run(['bash',str(path),'--help'],capture_output=True,text=True,check=True)
        assert '--user' in result.stdout


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
