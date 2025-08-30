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
from uuid import UUID
from datetime import datetime
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import dspy
from sqlmodel import Session, create_engine, SQLModel

from app.api.routes_sim import router as sim_router
from app.services import SimulationService
from app.models import User


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload available models from OpenRouter
    from app.classes.model_config import fetch_openrouter_models
    print("Loading available models from OpenRouter...")
    await fetch_openrouter_models()
    print("Models loaded successfully!")
    
    # Configure the LM to use OpenRouter
    lm = dspy.LM(
        model="openai/gpt-4o-mini",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY")
    )
    dspy.settings.configure(cache=False)
    dspy.configure(lm=lm)

    # Set up database connection
    database_url = os.getenv("DATABASE_URL", "postgresql://ipre_user:ipre_password@localhost:5432/ipre_db")
    engine = create_engine(database_url)
    
    # Create tables (if they don't exist)
    SQLModel.metadata.create_all(engine)
    
    # Create a mock user for testing
    from uuid import UUID
    with Session(engine) as session:
        mock_user_id = UUID("00000000-0000-0000-0000-000000000000")
        existing_user = session.get(User, mock_user_id)
        if not existing_user:
            mock_user = User(
                id=mock_user_id,
                email="test@example.com",
                is_active=True
            )
            session.add(mock_user)
            session.commit()
            print("Created mock user for testing")
        else:
            print("Mock user already exists")
    
    # Create a session maker
    def get_db_session():
        return Session(engine)

    # Expose services for routers to use
    app.state.sim_service = SimulationService(lm=lm, engine=engine)
    app.state.db_session = get_db_session
    
    yield
    
    # Cleanup on shutdown
    try:
        del lm
        app.state.sim_service = None
        app.state.db_session = None
        
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
