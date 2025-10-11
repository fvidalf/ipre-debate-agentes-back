from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class CanvasPosition(BaseModel):
    x: float
    y: float

class AgentConfig(BaseModel):
    name: str
    profile: str
    model_id: Optional[str] = None  # Model ID for this specific agent
    canvas_position: Optional[CanvasPosition] = None

class CreateSimRequest(BaseModel):
    config_id: Optional[str] = None  # Optional: reference to existing config for auto-save
    config_name: Optional[str] = "My debate"  # Name for the config if auto-saving
    config_description: Optional[str] = None  # Description for the config if auto-saving
    topic: str
    agents: List[AgentConfig]  # Updated to use AgentConfig instead of separate lists
    max_iters: int = 21
    bias: Optional[List[float]] = None
    stance: str = ""
    embedding_model: str = "onnx_minilm"  # "openrouter" or "onnx_minilm"
    embedding_config: Optional[dict] = None  # Additional config for the embedding model
    max_interventions_per_agent: Optional[int] = None  # Maximum number of times each agent can speak

class RunResponse(BaseModel):
    simulation_id: str
    config_id: Optional[str]
    config_name: Optional[str] = None
    config_version_when_run: Optional[int]
    is_latest_version: Optional[bool] = None  # True if run used latest config version
    status: str
    progress: Optional[dict] = None
    latest_events: List[dict] = []
    is_finished: bool
    stopped_reason: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

class RunListItem(BaseModel):
    simulation_id: str
    config_id: Optional[str]
    config_name: Optional[str] = None
    config_version_when_run: Optional[int]
    is_latest_version: Optional[bool] = None
    status: str
    is_finished: bool
    created_at: datetime
    finished_at: Optional[datetime]

class RunsListResponse(BaseModel):
    runs: List[RunListItem]
    total: int

class StepResponse(BaseModel):
    iteration: int
    speaker: str
    opinion: str
    engaged: List[str]
    finished: bool
    stopped_reason: Optional[str] = None

class AvailableModel(BaseModel):
    id: str
    name: str
    description: str
    provider: str

class AvailableModelsResponse(BaseModel):
    models: List[AvailableModel]
    default_model: str

# Agent Template Schemas
class AgentTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    visibility: str
    config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class AgentTemplatesListResponse(BaseModel):
    agents: List[AgentTemplateResponse]
    total: int

# Agent Snapshot Schema (for templates and configs)
class AgentSnapshotResponse(BaseModel):
    position: int
    name: Optional[str]
    background: Optional[str]
    canvas_position: Optional[CanvasPosition] = None
    snapshot: Dict[str, Any]
    created_at: datetime

# Config Template Schemas
class ConfigTemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    visibility: str
    parameters: Dict[str, Any]
    agents: List[AgentSnapshotResponse] = []  # Only included in single-item GET
    created_at: datetime

    class Config:
        from_attributes = True

class ConfigTemplateListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    visibility: str
    parameters: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True

class ConfigTemplatesListResponse(BaseModel):
    templates: List[ConfigTemplateListItem]
    total: int

# Config Schemas
class ConfigResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    parameters: Dict[str, Any]
    version_number: int
    agents: List[AgentSnapshotResponse] = []  # Only included in single-item GET
    source_template_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConfigListItem(BaseModel):
    id: str
    name: str
    description: Optional[str]
    parameters: Dict[str, Any]
    version_number: int
    source_template_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ConfigsListResponse(BaseModel):
    configs: List[ConfigListItem]
    total: int

class CreateConfigRequest(BaseModel):
    pass  # Empty - just a signal to create a blank config

class UpdateConfigRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    topic: Optional[str] = None
    agents: Optional[List[AgentConfig]] = None
    max_iters: Optional[int] = None
    bias: Optional[List[float]] = None
    stance: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_config: Optional[dict] = None
    max_interventions_per_agent: Optional[int] = None

# Voting Schemas
class IndividualVote(BaseModel):
    agent_name: str
    agent_background: str  # Their stance/profile for context
    vote: bool  # True=Yea, False=Nay  
    reasoning: str

class VotingResponse(BaseModel):
    simulation_id: str
    yea: int
    nay: int
    individual_votes: List[IndividualVote]
    created_at: datetime
