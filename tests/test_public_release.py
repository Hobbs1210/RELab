"""Static checks to avoid accidentally releasing sensitive local research artifacts."""
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def test_default_bindings_and_installer_files():
    env=(ROOT/'.env.example').read_text()
    assert 'DNS_BIND_IP=127.0.0.1' in env
    assert 'HTTPS_BIND_IP=127.0.0.1' in env
    install=(ROOT/'scripts/install-debian.sh').read_text()
    assert 'openssh-server' in install and 'docker.sources' in install
    assert '--grant-docker-access' in install
    assert 'config_file in rules.json scenarios.json owned-dns.json' in install
    assert (ROOT/'docs/DEBIAN_INSTALL.md').exists()
    assert (ROOT/'SECURITY.md').exists()
    assert (ROOT/'LICENSE').exists()


def test_source_release_excludes_local_files(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from importlib import import_module
    pack=import_module('package-release')
    assert not pack.allowed(ROOT/'.env')
    assert not pack.allowed(ROOT/'firmware/private.bin')
    assert not pack.allowed(ROOT/'data/pcaps/capture.pcap')
    dest=tmp_path/'public.zip'
    pack.package(dest)
    with zipfile.ZipFile(dest) as z:
        members=z.namelist()
        assert all('/.env' not in m or m.endswith('/.env.example') for m in members)
        assert 'RELab/LICENSE' in members
        assert 'RELab/scripts/install-debian.sh' in members
        assert 'RELab/docs/FIRMWARE_DOWNLOAD.md' in members
        assert not any(m.endswith('.pem') or m.endswith('.pcap') or m.endswith('.bin') for m in members)
