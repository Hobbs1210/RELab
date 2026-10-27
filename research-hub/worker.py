"""Recoverable durable DB queue, transactional outbox + optional NATS JetStream publisher."""
from __future__ import annotations
import asyncio,json,os,time,traceback
import research_models as models
from research_models import Job,Event,now
from sqlalchemy import select
import research_core as core
import research_ingest as observability

NATS_URL=os.environ.get('NATS_URL','nats://events:4222')

def process_job():
    with models.Session.begin() as s:
        stmt=select(Job).where(Job.status.in_(['queued','retry'])).order_by(Job.created).limit(1)
        if s.bind.dialect.name=='postgresql':stmt=stmt.with_for_update(skip_locked=True)
        job=s.scalar(stmt)
        if not job:return False
        job.status='running';job.attempts+=1;job.updated=now()
        job_id=job.id
    # Marked running jobs are retried by restart recovery, not left indefinitely.
    try:
        with models.Session.begin() as s:
            job=s.get(Job,job_id)
            result=core.run_job(s,job)
            # Candidate parsers/SDKs/reports become deduplicated project artifacts.
            if job.kind in ('kaitai','dissector','sdk','report','protocol-state','correlate','recipe','topology'):
                generated=core.store_generated(s,job.project_id,job.id,result)
                if generated:result['generated_artifact_sha256']=generated
            # No unbounded result blobs in DB.
            compact=core.j(result)
            if len(compact)>512_000:
                compact=core.j({'truncated':True,'preview':compact[:500_000]})
            job.result=compact;job.status='succeeded';job.updated=now()
            core.emit(s,job.project_id,'job.succeeded',{'id':job.id,'kind':job.kind})
    except Exception as exc:
        with models.Session.begin() as s:
            job=s.get(Job,job_id)
            job.error=f'{type(exc).__name__}: {str(exc)[:300]}'
            job.status='retry' if job.attempts<job.max_attempts else 'failed'
            job.updated=now()
            core.emit(s,job.project_id,'job.'+job.status,{'id':job.id,'kind':job.kind})
    return True

def automate_events():
    count=0
    with models.Session.begin() as s:
        stmt=select(Event).where(Event.automation_done==False).order_by(Event.id).limit(50)
        if s.bind.dialect.name=='postgresql':stmt=stmt.with_for_update(skip_locked=True)
        for ev in s.scalars(stmt).all():
            payload=core.parsed(ev.body)
            if ev.kind=='artifact.imported':
                if payload.get('type')=='firmware':core.enqueue(s,ev.project_id,'firmware-intelligence',{'sha256':payload['sha256']})
                if payload.get('type')=='mobile-log':core.enqueue(s,ev.project_id,'mobile-analyze',{'sha256':payload['sha256']})
            ev.automation_done=True;count+=1
    return count

async def publish_pending():
    try:
        import nats
        nc=await nats.connect(NATS_URL,connect_timeout=1,max_reconnect_attempts=0)
        js=nc.jetstream()
        try:await js.add_stream(name='RESEARCH',subjects=['research.>'],max_msgs=250000)
        except Exception:pass # stream likely already exists
        with models.Session() as s:
            items=[(e.id,e.project_id,e.kind,e.body) for e in s.scalars(select(Event).where(Event.delivered==False).order_by(Event.id).limit(100))]
        for id,p,kind,body in items:
            await js.publish('research.'+kind,json.dumps({'id':id,'project':p,'data':json.loads(body)}).encode(),headers={'Nats-Msg-Id':str(id)})
            with models.Session.begin() as s:s.get(Event,id).delivered=True
        await nc.drain()
    except Exception as exc:
        # Outbox remains durable in the DB until a later successful delivery.
        if os.environ.get('RESEARCH_DEBUG')=='1':print('NATS delivery pending:',type(exc).__name__)

def recover():
    with models.Session.begin() as s:
        for job in s.scalars(select(Job).where(Job.status=='running')):
            job.status='retry' if job.attempts<job.max_attempts else 'failed';job.updated=now()
            core.emit(s,job.project_id,'job.recovered',{'id':job.id,'status':job.status})

def run_once():
    with models.Session.begin() as s:
        observability.ingest(s)
    automate_events()
    worked=process_job()
    asyncio.run(publish_pending())
    return worked

if __name__=='__main__':
    models.configure();recover()
    print('Research worker started (durable jobs + NATS outbox)',flush=True)
    while True:
        try:
            busy=run_once()
            if not busy:time.sleep(2)
        except Exception as exc:
            print('Research worker error:',type(exc).__name__,str(exc)[:200],flush=True)
            time.sleep(4)
