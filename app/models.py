from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Index, String
from sqlalchemy.dialects.postgresql import JSONB, ARRAY


# -----------------------
# Users & Auth
# -----------------------

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    email: str = Field(index=True, nullable=False)
    password_hash: Optional[str] = None          # for DIY auth; null if external
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None


class RefreshToken(SQLModel, table=True):
    __tablename__ = "refresh_tokens"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    token_hash: str = Field(nullable=False)      # store bcrypt hash of opaque token
    expires_at: datetime = Field(nullable=False)
    revoked_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# -----------------------
# Optional: reusable agent library
# -----------------------

class Agent(SQLModel, table=True):
    __tablename__ = "agents"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_user_id: Optional[UUID] = Field(foreign_key="users.id")
    name: str
    description: Optional[str] = None
    visibility: str = Field(default="private")   # 'private' | 'public'
    config: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# -----------------------
# Immutable Templates (blueprints)
# -----------------------

class ConfigTemplate(SQLModel, table=True):
    __tablename__ = "config_templates"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_user_id: Optional[UUID] = Field(foreign_key="users.id")
    name: str
    description: Optional[str] = None
    visibility: str = Field(default="private")
    parameters: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TemplateAgentSnapshot(SQLModel, table=True):
    __tablename__ = "template_agent_snapshots"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    config_template_id: UUID = Field(foreign_key="config_templates.id", nullable=False)
    position: int = Field(nullable=False)        # 1..N (aligns with bias[] order)
    name: Optional[str] = None
    background: Optional[str] = None
    snapshot: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("template_agent_snapshots_unique_pos", "config_template_id", "position", unique=True),
    )


# -----------------------
# Editable Configs (detached instances)
# -----------------------

class Config(SQLModel, table=True):
    __tablename__ = "configs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_user_id: Optional[UUID] = Field(foreign_key="users.id")
    name: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    version_number: int = Field(default=1)  # Auto-incremented on changes
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # lineage (optional)
    source_template_id: Optional[UUID] = Field(foreign_key="config_templates.id", default=None)


class ConfigVersion(SQLModel, table=True):
    __tablename__ = "config_versions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    config_id: UUID = Field(foreign_key="configs.id", nullable=False, index=True)
    version_number: int = Field(nullable=False)
    # Complete config state at this version (parameters + agents)
    parameters: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    agents: List[Dict[str, Any]] = Field(sa_column=Column(JSONB, nullable=False), default=[])
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("config_versions_unique_version", "config_id", "version_number", unique=True),
    )


class ConfigAgent(SQLModel, table=True):
    __tablename__ = "config_agents"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    config_id: UUID = Field(foreign_key="configs.id", nullable=False)
    position: int = Field(nullable=False)
    name: Optional[str] = None
    background: Optional[str] = None
    canvas_position: Optional[Dict[str, float]] = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    snapshot: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("config_agents_unique_pos", "config_id", "position", unique=True),
    )


# -----------------------
# Runs & Events
# -----------------------

class Run(SQLModel, table=True):
    __tablename__ = "runs"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    config_id: Optional[UUID] = Field(foreign_key="configs.id", default=None)
    config_version_when_run: Optional[int] = None  # Version number when this run was created
    # Reference to the frozen version (stored in separate table)
    config_version_id: Optional[UUID] = Field(foreign_key="config_versions.id", default=None)
    status: str = Field(default="created")       # created|queued|running|finished|failed|stopped
    iters: int = 0
    finished: bool = False
    stopped_reason: Optional[str] = None         # use enum in a future migration if you want
    meta: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False), default={})
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class RunEvent(SQLModel, table=True):
    __tablename__ = "run_events"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", nullable=False, index=True)
    iteration: int = Field(nullable=False)       # 1..N
    speaker: str = Field(nullable=False)
    opinion: str = Field(nullable=False)
    engaged: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), default=[])
    finished: bool = False
    stopped_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("run_events_unique_iter", "run_id", "iteration", unique=True),
    )


# -----------------------
# Voting Summary
# -----------------------

class Summary(SQLModel, table=True):
    __tablename__ = "summaries"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", nullable=False, index=True)
    yea: Optional[int] = None
    nay: Optional[int] = None
    reasons: Optional[List[str]] = Field(sa_column=Column(ARRAY(String)))  # from /vote (deprecated, use individual_votes)
    summary: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONB))     # structured verdict/metrics
    individual_votes: Optional[List[Dict[str, Any]]] = Field(sa_column=Column(JSONB), default=None)
    # Structure: [{"agent_position": int, "agent_data": {config_version_agent}, "vote": bool, "reasoning": "text"}]
    created_at: datetime = Field(default_factory=datetime.utcnow)


# -----------------------
# Analytics & Visualizations Cache
# -----------------------

class RunAnalytics(SQLModel, table=True):
    __tablename__ = "run_analytics"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", nullable=False, index=True, unique=True)
    
    # Engagement Matrix: [agent_index][turn] -> 0=inactive, 1=engaged, 2=speaking
    engagement_matrix: List[List[int]] = Field(sa_column=Column(JSONB, nullable=False))
    agent_names: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False))
    
    # Participation Statistics
    participation_stats: Dict[str, Any] = Field(sa_column=Column(JSONB, nullable=False))
    
    # Opinion Similarity Matrix (optional, computed if embedder available)
    opinion_similarity_matrix: Optional[List[List[float]]] = Field(sa_column=Column(JSONB), default=None)
    
    # Computed at first request
    computed_at: datetime = Field(default_factory=datetime.utcnow)
