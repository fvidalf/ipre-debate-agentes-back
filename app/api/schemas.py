from typing import List, Optional
from pydantic import BaseModel

class AgentConfig(BaseModel):
    name: str
    profile: str
    model_id: Optional[str] = None  # Model ID for this specific agent

class CreateSimRequest(BaseModel):
    topic: str
    agents: List[AgentConfig]  # Updated to use AgentConfig instead of separate lists
    max_iters: int = 21
    bias: Optional[List[float]] = None
    stance: str = ""
    embedding_model: str = "onnx_minilm"  # "openrouter" or "onnx_minilm"
    embedding_config: Optional[dict] = None  # Additional config for the embedding model

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
