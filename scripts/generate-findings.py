#!/usr/bin/env python3
"""Generate a local Markdown evidence report; never sends captures to AI/cloud."""
from pathlib import Path
import sqlite3,datetime,json
root=Path(__file__).resolve().parents[1]
db=root/'data/api/requests.db'; out=root/'research/EXPERIMENT_FINDINGS.md'
if not db.exists():raise SystemExit('No experiment DB yet. Start the lab first.')
con=sqlite3.connect(db);con.row_factory=sqlite3.Row
exp=con.execute('SELECT id,name,hypothesis,created_at,finished_at,status,result FROM experiments ORDER BY created_at').fetchall()
sections=['# Device RE Lab — Evidence report','','Generated '+datetime.datetime.now(datetime.timezone.utc).isoformat(),'','Only records local observations; hypotheses are not verified protocol descriptions.','']
for r in exp:
    sections.extend([f'## {r["name"]} — `{r["id"]}`','',f'- State: {r["status"]}',f'- Started: {r["created_at"]}',f'- Hypothesis: {r["hypothesis"]}',f'- Result: {r["result"] or "No conclusion"}',''])
sections+=['## Offline PCAP analyses','']
for p in sorted((root/'data/analysis').glob('*/summary.json')):
    try:
        d=json.loads(p.read_text());sections.append(f'- `{d["sha256"]}` — {d["file"]}, {d["bytes"]} bytes, protocol sample: {json.dumps(d.get("protocol_sample",{}))}')
    except Exception:pass
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text('\n'.join(sections)+'\n')
print(out)
