from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def test_repository_metadata_present():
    readme=(ROOT/'README.md').read_text()
    assert 'https://github.com/Hobbs1210/RELab' in readme
    assert (ROOT/'docs/PUBLISHING.md').is_file()
    assert (ROOT/'.github/ISSUE_TEMPLATE/bug_report.yml').is_file()
    assert (ROOT/'.github/pull_request_template.md').is_file()


def test_full_source_archive_has_ide_dotfolders(tmp_path):
    sys.path.insert(0,str(ROOT/'scripts'))
    from importlib import import_module
    pack=import_module('package-release')
    output=tmp_path/'source.zip'
    pack.package(output)
    with zipfile.ZipFile(output) as f:
        names=set(f.namelist())
        for item in ('README.md','LICENSE','compose.yaml','scripts/install-debian.sh','docs/PUBLISHING.md','.github/workflows/validate.yml','.agents/mcp_config.json','.codex/config.toml','.vscode/mcp.json','.devcontainer/devcontainer.json','research-hub/research_api.py'):
            assert f'RELab/{item}' in names
        assert not any('/.env' in x and x!='RELab/.env.example' for x in names)
        assert not any(x.startswith('RELab/.git/') for x in names)
