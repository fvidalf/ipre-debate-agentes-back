from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Index, String
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from pgvector.sqlalchemy import Vector


# -----------------------
# Users & Auth
# -----------------------

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    email: str = Field(index=True, nullable=False)
    password_hash: str = Field(nullable=False)   # required for minimal auth
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


# -----------------------
# Interventions + thoughts and Tools
# -----------------------

class Intervention(SQLModel, table=True):
    """
    Stores actual debate interventions/messages.
    This is the main content that agents produce during debates.
    """
    __tablename__ = "interventions"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", nullable=False, index=True)
    iteration: int = Field(nullable=False)
    speaker: str = Field(nullable=False)
    content: str = Field(nullable=False)
    engaged_agents: List[str] = Field(sa_column=Column(ARRAY(String), nullable=False), default=[])
    
    # Internal reasoning (for frontend display, NOT for embedding)
    reasoning_steps: Optional[List[str]] = Field(sa_column=Column(JSONB), default=None)
    
    # Extra prediction metadata (counter_target, tone, stance_strength, etc.)
    prediction_metadata: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONB), default=None)
    
    # Debate flow metadata
    finished: bool = Field(default=False)
    stopped_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("interventions_unique_iter", "run_id", "iteration", unique=True),
    )


class ToolUsage(SQLModel, table=True):
    """
    Stores tool usage data per agent. Each tool usage is linked to the intervention it influenced.
    Private to each agent - other agents cannot see this data.
    """
    __tablename__ = "tool_usages"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    intervention_id: UUID = Field(foreign_key="interventions.id", nullable=False, index=True)
    agent_name: str = Field(nullable=False, index=True)  # Owner of this tool usage
    tool_name: str = Field(nullable=False)               # 'web_search', 'calculator', etc.
    
    # Embeddable content (what gets embedded for RAG)
    query: str = Field(nullable=False)                   # What agent searched/asked for
    output: str = Field(nullable=False)                  # Final summary/result from tool
    
    # Private metadata (not embedded, for debugging/analysis)
    raw_results: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONB), default=None)
    execution_time: Optional[float] = None               # Tool execution time in seconds
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("tool_usages_agent_run", "agent_name", "intervention_id"),
    )


class Embedding(SQLModel, table=True):
    """
    Stores vector embeddings for all embeddable content with privacy model.
    
    Privacy Rules:
    - Interventions: PUBLIC (all agents can access)
    - Tool queries/outputs: PRIVATE (only owning agent can access)  
    - Documents: PRIVATE (only owning agent can access)
    """
    __tablename__ = "embeddings"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # What content this embeds
    source_type: str = Field(nullable=False, index=True)  # 'intervention', 'tool_query', 'tool_output', 'document'
    source_id: UUID = Field(nullable=False, index=True)   # FK to source table
    text_content: str = Field(nullable=False)             # The actual text that was embedded
    
    # Privacy and access control
    visibility: str = Field(nullable=False, index=True)   # 'public' (interventions) or 'private' (tools/docs)
    owner_agent: Optional[str] = Field(default=None, index=True)  # For private embeddings
    run_id: Optional[UUID] = Field(foreign_key="runs.id", nullable=True, index=True)  # NULL for unassigned documents
    
    # Embedding data (384 dimensions for MiniLM)
    embedding: List[float] = Field(sa_column=Column(Vector(384), nullable=False))
    embedding_model: str = Field(nullable=False)          # 'sentence-transformers/all-MiniLM-L6-v2'
    
    # Chunking information (for large documents)
    chunk_index: Optional[int] = Field(default=None)      # NULL for non-chunked content, 0+ for chunks
    chunk_start: Optional[int] = Field(default=None)      # Character position in original document
    chunk_end: Optional[int] = Field(default=None)        # End character position
    
    # Optional metadata (renamed to avoid SQLAlchemy conflict)
    extra_metadata: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONB), default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("embeddings_source_lookup", "source_type", "source_id"),
        Index("embeddings_visibility_agent", "visibility", "owner_agent"),
        Index("embeddings_run_visibility", "run_id", "visibility"),
        Index("embeddings_chunk_lookup", "source_type", "source_id", "chunk_index"),
    )


# -----------------------
# Document Library
# -----------------------

class DocumentLibrary(SQLModel, table=True):
    """
    Global document library for pre-uploaded documents.
    These documents are owned by users but not yet assigned to agents.
    """
    __tablename__ = "document_library"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    owner_user_id: UUID = Field(foreign_key="users.id", nullable=False, index=True)
    
    # Document content
    title: str = Field(nullable=False)
    content: str = Field(nullable=False)
    document_type: str = Field(default="general")  # 'research_paper', 'briefing', 'data_sheet', 'general'
    
    # File metadata
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    content_hash: str = Field(nullable=False, index=True)  # SHA-256 for deduplication
    
    # Processing status
    processing_status: str = Field(default="pending")  # 'pending', 'processing', 'completed', 'failed'
    embedding_status: str = Field(default="pending")   # 'pending', 'processing', 'completed', 'failed'
    error_message: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(sa_column=Column(ARRAY(String)), default=[])
    description: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = Field(sa_column=Column(JSONB), default=None)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (
        Index("document_library_user_hash", "owner_user_id", "content_hash"),
        Index("document_library_status", "processing_status", "embedding_status"),
    )


class AgentDocumentAccess(SQLModel, table=True):
    """
    Tracks which agents have access to which documents during simulations.
    Used for analytics and cleanup.
    """
    __tablename__ = "agent_document_access"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    run_id: UUID = Field(foreign_key="runs.id", nullable=False, index=True)
    agent_name: str = Field(nullable=False, index=True)
    document_id: UUID = Field(foreign_key="document_library.id", nullable=False, index=True)
    
    # Access metadata
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(default=0)  # How many times agent accessed this document
    last_accessed_at: Optional[datetime] = None

    __table_args__ = (
        Index("agent_document_access_run_agent", "run_id", "agent_name"),
        Index("agent_document_access_unique", "run_id", "agent_name", "document_id", unique=True),
    )
