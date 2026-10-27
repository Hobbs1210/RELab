"""Merge saved HTTP events and Zeek JSON logs with bounded memory, sortable UTC timestamps."""
import json,sqlite3
from datetime import datetime,timezone
from pathlib import Path

def events(db_file:Path,analysis_dir:Path,limit=300,src=None,analysis_id=None,hardware_log:Path|None=None):
    limit=max(1,min(int(limit),1000)); out=[]
    if db_file.exists():
        try:
            with sqlite3.connect(f'file:{db_file}?mode=ro',uri=True) as conn:
                conn.row_factory=sqlite3.Row
                for row in conn.execute('SELECT id,ts,source_ip,method,host,path,response_status FROM http_requests ORDER BY id DESC LIMIT 1500'):
                    if src and src not in (row['source_ip'],row['host']):continue
                    out.append({'time':row['ts'],'kind':'http','source':'emulator','evidence':f'http_requests:{row["id"]}','fields':dict(row)})
        except sqlite3.Error:pass
    dirs=sorted(analysis_dir.glob('*/summary.json'))[-12:]
    for summary in dirs:
        if analysis_id and summary.parent.name!=analysis_id:continue
        for log in ('dns.log','conn.log','ssl.log','http.log','weird.log'):
            target=summary.parent/log
            if not target.is_file():continue
            with target.open(errors='replace') as fh:
                for n,line in enumerate(fh):
                    if n>=2000:break
                    try:rec=json.loads(line)
                    except ValueError:continue
                    if src and src not in (str(rec.get('id.orig_h','')),str(rec.get('id.resp_h','')),str(rec.get('query',''))):continue
                    ts=rec.get('ts')
                    if not isinstance(ts,(int,float)):continue
                    out.append({'time':datetime.fromtimestamp(ts,timezone.utc).isoformat(),'kind':log.removesuffix('.log'),
                                'source':'zeek','evidence':f'{summary.parent.name}/{log}:{n+1}',
                                'fields':{k:v for k,v in rec.items() if k in ('id.orig_h','id.resp_h','query','qtype_name','server_name','proto','service','status_code','uid','duration','resp_p')}})
    if hardware_log and hardware_log.is_file():
        # Optional operator-imported BLE, USB or serial observation events. This does
        # not imply a live sniffer or automatic hardware capture.
        with hardware_log.open(errors='replace') as fh:
            for index,line in enumerate(fh):
                if index>=3000:break
                try:rec=json.loads(line)
                except ValueError:continue
                if not isinstance(rec,dict) or rec.get('kind') not in ('ble','usb','serial') or not isinstance(rec.get('time'),str):continue
                if src and src not in str(rec.get('source','')):continue
                out.append({'time':rec['time'],'kind':rec['kind'],'source':rec.get('source','hardware-import'),
                            'evidence':f'hardware-events.jsonl:{index+1}', 'fields':rec.get('fields',{})})
    out.sort(key=lambda x:x['time'])
    return {'events':out[-limit:],'total_before_limit':len(out),'sources':['emulator','zeek'],
            'limitations':'Cross-source clock synchronization, packet loss and capture vantage point affect correlation.'}
