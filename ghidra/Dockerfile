# Optional heavyweight firmware workbench. Downloads the official Ghidra binary
# at build time; review downloaded release and pin GHIDRA_RELEASE_URL in CI.
FROM eclipse-temurin:21-jdk-jammy
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-venv ca-certificates unzip binutils && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /venv && /venv/bin/pip install --no-cache-dir 'fastapi>=0.115,<1' 'uvicorn>=0.30,<1' 'fastapi-mcp==0.4.0'
ARG GHIDRA_RELEASE_URL=
RUN GHIDRA_RELEASE_URL="$GHIDRA_RELEASE_URL" python3 - <<'PY'
import json,os,urllib.request,pathlib,zipfile,shutil
url=os.environ.get('GHIDRA_RELEASE_URL')
if not url:
 req=urllib.request.Request('https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest',headers={'User-Agent':'device-re-lab-build'})
 data=json.load(urllib.request.urlopen(req,timeout=30))
 hits=[x['browser_download_url'] for x in data['assets'] if x['name'].endswith('.zip') and '_PUBLIC_' in x['name']]
 if not hits:raise SystemExit('Cannot identify official Ghidra PUBLIC zip in release')
 url=hits[0]
p=pathlib.Path('/tmp/ghidra.zip')
with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'device-re-lab-build'}),timeout=180) as r, p.open('wb') as f:shutil.copyfileobj(r,f)
with zipfile.ZipFile(p) as z:z.extractall('/opt')
root=next(x for x in pathlib.Path('/opt').iterdir() if x.is_dir() and x.name.startswith('ghidra_'))
root.rename('/opt/ghidra')
p.unlink()
PY
COPY headless.py /app/headless.py
COPY DumpFunctions.java /app/scripts/DumpFunctions.java
WORKDIR /app
ENV PATH=/venv/bin:$PATH
EXPOSE 8000
CMD ["uvicorn", "headless:app", "--host", "0.0.0.0", "--port", "8000"]
