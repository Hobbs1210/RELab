"""Declarative, untrusted-data-only protocol adapters, inference and contract generation.

No input is evaluated or imported as code. Candidate protocol findings are hypotheses.
"""
from __future__ import annotations
import base64, collections, hashlib, json, math, re, struct
from pathlib import Path

DEFAULTS={
 'raw': {'framing':'raw','description':'opaque byte stream'},
 'length-be16': {'framing':'length-prefix','length_bytes':2,'byteorder':'big'},
 'length-le32': {'framing':'length-prefix','length_bytes':4,'byteorder':'little'},
 'delimiter-lf': {'framing':'delimiter','delimiter_hex':'0a'},
 'grpc': {'framing':'grpc','description':'gRPC 5-byte message header (not HTTP/2 decoding)'},
 'mqtt': {'framing':'mqtt','description':'MQTT fixed header and variable-length remaining length'},
 'coap': {'framing':'coap','description':'CoAP fixed header and token, not option parser'},
}

def protocols(directory:Path)->dict:
    result={key:{'id':key,**val} for key,val in DEFAULTS.items()}
    if directory.exists():
        for path in sorted(directory.glob('*.json')):
            try:
                item=json.loads(path.read_text()); name=item['id']
                if not re.fullmatch('[a-z0-9_-]{1,50}',name):continue
                if item.get('framing') not in ('raw','length-prefix','delimiter','grpc','mqtt','coap'):continue
                result[name]=item
            except (ValueError, KeyError, OSError, TypeError):continue
    return result

def decode_bytes(data:bytes,spec:dict,max_frames:int=100)->dict:
    if len(data)>65536:raise ValueError('Input exceeds 64 KiB')
    framing=spec.get('framing','raw');offset=0;items=[]
    def emit(pos:int, size:int,meta:dict):
        if size<0 or pos+size>len(data):return False
        chunk=data[pos:pos+size]
        items.append({'offset':pos,'size':size,'hex':chunk[:256].hex(),'truncated':size>256,**meta});return True
    if framing=='raw': emit(0,len(data),{})
    elif framing=='delimiter':
        sep=bytes.fromhex(spec.get('delimiter_hex','0a'))
        if not sep:raise ValueError('Delimiter cannot be empty')
        for part in data.split(sep)[:max_frames]:
            emit(offset,len(part),{'delimiter_hex':sep.hex()});offset+=len(part)+len(sep)
    elif framing in ('length-prefix','grpc'):
        n=5 if framing=='grpc' else int(spec.get('length_bytes',2))
        if n not in (1,2,4,5):raise ValueError('Length prefix must use 1, 2 or 4 bytes')
        while offset+n<=len(data) and len(items)<max_frames:
            compressed=data[offset] if framing=='grpc' else None
            length=int.from_bytes(data[offset+1:offset+5],'big') if framing=='grpc' else int.from_bytes(data[offset:offset+n],spec.get('byteorder','big'))
            if length>65536 or offset+n+length>len(data):break
            emit(offset+n,length,{'declared_length':length,'compressed':compressed} if framing=='grpc' else {'declared_length':length})
            offset+=n+length
    elif framing=='mqtt':
        while offset<len(data) and len(items)<max_frames:
            begin=offset;ctrl=data[offset];offset+=1;remaining=0;shift=0
            for i in range(4):
                if offset>=len(data):return {'framing':framing,'frames':items,'unparsed_bytes':len(data)-begin}
                digit=data[offset];offset+=1;remaining+=(digit&127)<<shift;shift+=7
                if not digit&128:break
            else:break
            if remaining>65536 or offset+remaining>len(data):break
            emit(offset,remaining,{'packet_type':ctrl>>4,'flags':ctrl&15,'declared_length':remaining});offset+=remaining
    elif framing=='coap':
        if len(data)>=4:
            token_size=data[0]&15
            if token_size<=8 and len(data)>=4+token_size:
                emit(4+token_size,len(data)-4-token_size,{'version':data[0]>>6,'type':(data[0]>>4)&3,'code':data[1],'message_id':int.from_bytes(data[2:4],'big'),'token_hex':data[4:4+token_size].hex(),'note':'Options/payload not individually parsed'})
    else:raise ValueError('Unknown framing')
    return {'framing':framing,'frames':items,'unparsed_bytes':len(data)-min(offset,len(data)) if framing!='raw' else 0}

def infer(samples:list[bytes])->dict:
    if not samples or len(samples)>100:raise ValueError('Provide 1..100 samples')
    if any(len(s)>65536 for s in samples):raise ValueError('Max 64 KiB each')
    lengths=[len(s) for s in samples]
    common=0
    for vals in zip(*samples):
        if len(set(vals))!=1:break
        common+=1
    counts=collections.Counter(byte for sample in samples for byte in sample)
    total=sum(counts.values())
    entropy=-sum((n/total)*math.log2(n/total) for n in counts.values()) if total else 0.0
    hypotheses=[]
    if all(s.startswith(b'{') or s.startswith(b'[') for s in samples):
        try:
            values=[json.loads(s) for s in samples]
            hypotheses.append({'type':'json','confidence':'medium','basis':'All samples parse as JSON','top_level_types':[type(v).__name__ for v in values]})
        except (ValueError,UnicodeDecodeError):pass
    for width in (2,4):
        for endian in ('big','little'):
            hits=sum(1 for s in samples if len(s)>=width and int.from_bytes(s[:width],endian)==len(s)-width)
            if hits>=max(1,math.ceil(len(samples)*0.8)):
                hypotheses.append({'type':'length-prefix','width':width,'byteorder':endian,'matches':hits,'confidence':'medium'})
    if common: hypotheses.append({'type':'fixed-prefix','hex':samples[0][:min(common,64)].hex(),'bytes':common,'confidence':'medium'})
    for sep in (b'\n',b'\0'):
        hits=sum(sep in s for s in samples)
        if hits: hypotheses.append({'type':'delimiter','hex':sep.hex(),'matches':hits,'confidence':'low'})
    return {'sample_count':len(samples),'lengths':lengths,'common_prefix_hex':samples[0][:min(common,128)].hex(),
            'entropy_bits_per_byte':round(entropy,3),'candidate_fields':hypotheses,
            'warning':'Heuristic only. No field type, checksum, or protocol is verified without controlled tests.'}

def compare_firmware(a:bytes,b:bytes)->dict:
    if len(a)>2_000_000 or len(b)>2_000_000: raise ValueError('Comparison reads at most 2 MiB each; use hashes for larger images')
    changed=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
    groups=[]
    for offset in changed:
        if not groups or offset>groups[-1]['end']:groups.append({'start':offset,'end':offset+1})
        else:groups[-1]['end']=offset+1
    return {'size_a':len(a),'size_b':len(b),'sha256_a':hashlib.sha256(a).hexdigest(),
            'sha256_b':hashlib.sha256(b).hexdigest(),'changed_byte_count_common_region':len(changed),
            'changed_ranges_first_200':groups[:200], 'added_or_removed_tail_bytes':abs(len(a)-len(b))}

def firmware_arch(data:bytes)->dict:
    candidates=[]
    if data[:4]==b'\x7fELF' and len(data)>=20:
        endian='little' if data[5]==1 else 'big'
        machine=int.from_bytes(data[18:20],endian)
        names={3:'x86',8:'MIPS',20:'PowerPC',40:'ARM',62:'x86_64',183:'AArch64',243:'RISC-V'}
        candidates.append({'format':'ELF','architecture':names.get(machine,'unknown'),'machine':machine,'confidence':'high'})
    if data[:2]==b'MZ':candidates.append({'format':'PE/DOS (candidate)','architecture':'unknown','confidence':'medium'})
    if data[:4] in (b'\x00asm',):candidates.append({'format':'WebAssembly','architecture':'wasm','confidence':'high'})
    for magic,fmt in [(b'hsqs','SquashFS little-endian'),(b'sqsh','SquashFS'),(b'UBI#','UBI'),(b'\x27\x05\x19\x56','uImage')]:
        p=data.find(magic)
        if p>=0:candidates.append({'format':fmt,'offset':p,'confidence':'medium'})
    return {'candidates':candidates,'warning':'Raw MCU images generally require external CPU/board knowledge; signatures are not proof of executable architecture'}

def openapi_from_events(events:list[dict])->dict:
    paths={}
    for e in events:
        method=str(e.get('method','GET')).lower()
        path=str(e.get('path','/')).split('?')[0]
        if method not in ('get','put','post','delete','patch','head','options'):continue
        if len(path)>200 or not path.startswith('/') or any(c in path for c in ('{','}')):continue
        if len(paths)>=100 and path not in paths:break
        item=paths.setdefault(path,{})
        item[method]={'operationId':f'observed_{method}_{hashlib.sha1(path.encode()).hexdigest()[:10]}',
                      'summary':'Observed request; semantics unverified',
                      'responses':{str(e.get('response_status',501)):{'description':'Observed status; response schema unknown'}},
                      'x-research-evidence':{'request_ids':[e.get('id')],'observation_only':True}}
    return {'openapi':'3.1.0','info':{'title':'Candidate device API','version':'0.0.0-research','description':'Unverified endpoints inferred from observations. Manually validate.'},'paths':paths}

def sdk_sources(spec:dict)->dict:
    """Lightweight standalone SDK source for simple JSON GET/POST endpoints; no code execution."""
    paths=spec.get('paths',{})
    operations=[]
    for path,methods in paths.items():
        if not re.fullmatch(r'/[a-zA-Z0-9_./-]{0,180}',path):continue
        for method in methods:
            if method not in ('get','post','put','patch','delete'):continue
            safe=re.sub('[^A-Za-z0-9_]','_',method+'_'+path).strip('_')[:80]
            operations.append((method.upper(),path,safe))
    py=['"""Generated research SDK. Verify endpoints and authentication before using."""','import json','import urllib.request', 'class DeviceClient:', '    def __init__(self, base_url): self.base_url = base_url.rstrip("/")']
    ts=['// Generated research SDK. Endpoint contracts are unverified.','export class DeviceClient {','  constructor(public readonly baseUrl: string) {}']
    cs=['// Generated research SDK. Endpoint contracts are unverified.','using System.Net.Http;','using System.Text;','namespace DeviceResearch;','public sealed class DeviceClient(HttpClient http, string baseUrl) {']
    for method,path,name in operations:
        py.extend([f'    def {name}(self, body=None):',f'        data = None if body is None else json.dumps(body).encode("utf-8")',f'        req = urllib.request.Request(self.base_url + {path!r}, data=data, method={method!r}, headers={{"Content-Type":"application/json"}})', '        with urllib.request.urlopen(req, timeout=10) as r: return r.read()'])
        ts.append(f'  async {name}(body?: unknown): Promise<Response> {{ return fetch(this.baseUrl + {json.dumps(path)}, {{ method: {json.dumps(method)}, headers: {{"Content-Type": "application/json"}}, body: body === undefined ? undefined : JSON.stringify(body) }}); }}')
        cs.append(f'  public System.Threading.Tasks.Task<HttpResponseMessage> {name}(string? json = null) => http.SendAsync(new HttpRequestMessage(HttpMethod.{method.title() if method not in ("PATCH",) else "Patch"}, baseUrl + {json.dumps(path)}) {{ Content = json is null ? null : new StringContent(json, Encoding.UTF8, "application/json") }});')
    ts.append('}');cs.append('}')
    return {'python':'\n'.join(py)+'\n','typescript':'\n'.join(ts)+'\n','csharp':'\n'.join(cs)+'\n','operation_count':len(operations),
            'warning':'Unverified: generated from observed endpoints only; no proven models, auth, framing, or semantics.'}
