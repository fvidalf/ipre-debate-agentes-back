import os
# Disable multiprocessing in transformers to prevent semaphore leaks
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "true"

import multiprocessing
multiprocessing.set_start_method('spawn', force=True)

from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

from contextlib import asynccontextmanager
from typing import Dict, Tuple, List
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import dspy

from app.api.routes_sim import router as sim_router
from app.models.simulation import Simulation
from app.models.nlp import load_stance_aware_sbert

# --- minimal service baked into main.py (can be moved later) ---
class SimulationService:
    def __init__(self, sbert, lm):
        self._sbert = sbert
        self._lm = lm
        self._sims: Dict[str, Simulation] = {}

    def create_sim(self, topic: str, profiles: List[str], agent_names: List[str],
                   max_iters: int, bias=None, stance: str = "") -> str:
        sim_id = str(uuid.uuid4())
        sim = Simulation(
            topic=topic,
            profiles=profiles,
            agent_names=agent_names,
            sbert=self._sbert,   # pass the wrapper/encoder you loaded
            lm=self._lm,
            max_iters=max_iters,
            bias=bias,
            stance=stance,
        )
        self._sims[sim_id] = sim
        return sim_id

    def start(self, sim_id: str) -> None:
        self._sims[sim_id].start()

    def step(self, sim_id: str):
        return self._sims[sim_id].step()

    def run(self, sim_id: str) -> None:
        self._sims[sim_id].run()

    def vote(self, sim_id: str) -> Tuple[int, int, List[str]]:
        return self._sims[sim_id].vote()

    def stop(self, sim_id: str) -> None:
        self._sims[sim_id]._finished = True  # preserve translation minimalism

    def snapshot(self, sim_id: str):
        return self._sims[sim_id].snapshot()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load stance-aware SBERT exactly via your nlp.py
    sbert = load_stance_aware_sbert()

    # Configure the LM to use OpenRouter
    lm = dspy.LM(
        model="openai/gpt-4o-mini",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
    dspy.settings.configure(cache=False)
    dspy.configure(lm=lm)

    # Expose a service for routers to use
    app.state.sim_service = SimulationService(sbert=sbert, lm=lm)
    
    yield
    
    # Cleanup on shutdown
    try:
        # Clean up SBERT model resources
        if hasattr(sbert, '_sbert') and sbert._sbert is not None:
            del sbert._sbert
        del sbert
        del lm
        app.state.sim_service = None
        
        # Force garbage collection
        import gc
        gc.collect()
    except Exception as e:
        print(f"Warning: Error during cleanup: {e}")

app = FastAPI(lifespan=lifespan)

# Configure CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

app.include_router(sim_router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
