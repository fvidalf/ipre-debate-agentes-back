from typing import List, Optional
from pydantic import BaseModel

class CreateSimRequest(BaseModel):
    topic: str
    profiles: List[str]
    agent_names: List[str]
    max_iters: int = 21
    bias: Optional[List[float]] = None
    stance: str = ""

class StepResponse(BaseModel):
    iteration: int
    speaker: str
    opinion: str
    engaged: List[str]
    finished: bool
    stopped_reason: Optional[str] = None
