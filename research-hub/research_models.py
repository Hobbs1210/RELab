"""Shared research evidence and durable job model (SQLite for tests, PostgreSQL in Compose)."""
from __future__ import annotations
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Integer, DateTime, Float, Boolean, Text, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

class Base(DeclarativeBase): pass

def now():return datetime.now(timezone.utc)

def textcol():return mapped_column(Text,default='{}',nullable=False)

class Project(Base):
    __tablename__='projects'
    id:Mapped[str]=mapped_column(String(60),primary_key=True)
    name:Mapped[str]=mapped_column(String(120),nullable=False)
    description:Mapped[str]=mapped_column(Text,default='')
    created:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Device(Base):
    __tablename__='devices'
    id:Mapped[str]=mapped_column(String(60),primary_key=True)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    name:Mapped[str]=mapped_column(String(120))
    kind:Mapped[str]=mapped_column(String(60),default='unknown')
    identity:Mapped[str]=mapped_column(Text,default='{}')

class Artifact(Base):
    __tablename__='artifacts'
    id:Mapped[str]=mapped_column(String(64),primary_key=True) # sha256; dedupe
    size:Mapped[int]=mapped_column(Integer)
    type:Mapped[str]=mapped_column(String(32))
    original_name:Mapped[str]=mapped_column(String(255))
    source:Mapped[str]=mapped_column(String(30),default='upload')
    created:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class ProjectArtifact(Base):
    __tablename__='project_artifacts'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    artifact_id:Mapped[str]=mapped_column(ForeignKey('artifacts.id'))
    device_id:Mapped[str|None]=mapped_column(String(60),nullable=True)
    __table_args__=(UniqueConstraint('project_id','artifact_id','device_id'),)

class Evidence(Base):
    __tablename__='evidence'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    device_id:Mapped[str|None]=mapped_column(String(60),nullable=True)
    kind:Mapped[str]=mapped_column(String(60))
    external_ref:Mapped[str|None]=mapped_column(String(180),nullable=True)
    summary:Mapped[str]=mapped_column(Text)
    artifact_id:Mapped[str|None]=mapped_column(String(64),nullable=True)
    locator:Mapped[str]=mapped_column(Text,default='{}')
    fields:Mapped[str]=mapped_column(Text,default='{}')
    observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
    confidence:Mapped[float]=mapped_column(Float,default=1)
    clock_source:Mapped[str]=mapped_column(String(40),default='server')

    __table_args__=(UniqueConstraint('project_id','external_ref'),)

class Relationship(Base):
    __tablename__='relationships'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    from_type:Mapped[str]=mapped_column(String(40))
    from_id:Mapped[str]=mapped_column(String(120))
    relation:Mapped[str]=mapped_column(String(40))
    to_type:Mapped[str]=mapped_column(String(40))
    to_id:Mapped[str]=mapped_column(String(120))
    evidence_id:Mapped[int|None]=mapped_column(Integer,nullable=True)

class Event(Base):
    __tablename__='events'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    project_id:Mapped[str]=mapped_column(String(60),index=True)
    kind:Mapped[str]=mapped_column(String(80),index=True)
    body:Mapped[str]=mapped_column(Text)
    created:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    delivered:Mapped[bool]=mapped_column(Boolean,default=False)
    automation_done:Mapped[bool]=mapped_column(Boolean,default=False)

class Job(Base):
    __tablename__='jobs'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    kind:Mapped[str]=mapped_column(String(60))
    status:Mapped[str]=mapped_column(String(20),default='queued',index=True)
    params:Mapped[str]=mapped_column(Text,default='{}')
    result:Mapped[str]=mapped_column(Text,default='{}')
    error:Mapped[str]=mapped_column(Text,default='')
    attempts:Mapped[int]=mapped_column(Integer,default=0)
    max_attempts:Mapped[int]=mapped_column(Integer,default=2)
    created:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    updated:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Experiment(Base):
    __tablename__='experiments'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    project_id:Mapped[str]=mapped_column(ForeignKey('projects.id'),index=True)
    name:Mapped[str]=mapped_column(String(120))
    kind:Mapped[str]=mapped_column(String(60))
    params:Mapped[str]=mapped_column(Text,default='{}')
    created:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    last_job:Mapped[str|None]=mapped_column(String(36),nullable=True)

class Approval(Base):
    __tablename__='approvals'
    id:Mapped[str]=mapped_column(String(36),primary_key=True)
    project_id:Mapped[str]=mapped_column(String(60),index=True)
    action:Mapped[str]=mapped_column(String(60))
    params:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(20),default='pending')
    created:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    decision_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class ClockOffset(Base):
    __tablename__='clock_offsets'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    project_id:Mapped[str]=mapped_column(String(60))
    source:Mapped[str]=mapped_column(String(60))
    offset_ms:Mapped[float]=mapped_column(Float)
    uncertainty_ms:Mapped[float]=mapped_column(Float)
    observed_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class AgentMemory(Base):
    __tablename__='agent_memory'
    id:Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    project_id:Mapped[str]=mapped_column(String(60),index=True)
    text:Mapped[str]=mapped_column(Text)
    evidence_ids:Mapped[str]=mapped_column(Text,default='[]')
    status:Mapped[str]=mapped_column(String(20),default='hypothesis')
    created:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

_engine=None
Session=None

def configure(url=None):
    global _engine,Session
    url=url or os.getenv('RESEARCH_DATABASE_URL','sqlite:////tmp/device-research.db')
    kwargs={'connect_args':{'check_same_thread':False}} if url.startswith('sqlite') else {'pool_pre_ping':True}
    _engine=create_engine(url,**kwargs)
    Base.metadata.create_all(_engine)
    Session=sessionmaker(_engine,expire_on_commit=False)
    with Session.begin() as s:
        if not s.get(Project,'default'):
            s.add(Project(id='default',name='Default research project',description='Isolated starter workspace'))
    return Session
