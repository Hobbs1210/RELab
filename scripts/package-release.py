#!/usr/bin/env python3
"""Create a source release archive with no local capture/firmware/secret artifacts."""
import argparse
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
EXCLUDED_DIRS={'.git','.pytest_cache','.venv','__pycache__','dist'}
EXCLUDED_PARTS={('config','adguard','conf'),('config','adguard','work')}
EXCLUDED_EXTS={'.pem','.key','.p12','.pfx','.pcap','.pcapng','.db','.sqlite','.sqlite3','.mitm','.zip','.log','.part'}

def allowed(path:Path)->bool:
    parts=path.relative_to(ROOT).parts
    if any(part in EXCLUDED_DIRS for part in parts):return False
    if any(parts[:len(prefix)]==prefix for prefix in EXCLUDED_PARTS):return False
    if parts[0] in ('data','firmware','certs','research') and path.name!='.gitkeep':return False
    if path.name=='.env' or (path.name.startswith('.env.') and path.name!='.env.example'):return False
    if path.suffix.lower() in EXCLUDED_EXTS:return False
    if path.is_symlink():return False
    return True

def package(output:Path):
    output.parent.mkdir(parents=True,exist_ok=True)
    files=sorted(p for p in ROOT.rglob('*') if p.is_file() and allowed(p) and p.resolve()!=output.resolve())
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for path in files:
            name='RELab/'+path.relative_to(ROOT).as_posix()
            z.write(path,arcname=name)
    return files

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',default='/mnt/data/RELab-github-ready.zip')
    args=parser.parse_args()
    files=package(Path(args.output))
    print(f'Created {args.output} with {len(files)} source files')
