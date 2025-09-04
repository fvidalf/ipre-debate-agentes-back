from typing import List
from uuid import UUID
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select

from app.api.schemas import CreateSimRequest, AvailableModelsResponse, AvailableModel, RunResponse
from app.services.config_service import create_or_update_config, build_config_snapshot
from app.models import Run, RunEvent, Config

router = APIRouter(prefix="/simulations", tags=["simulations"])

def get_service(request: Request):
    svc = getattr(request.app.state, "sim_service", None)
    if svc is None:
        raise HTTPException(500, "Simulation service not initialized")
    return svc

def get_db(request: Request):
    db_session_maker = getattr(request.app.state, "db_session", None)
    if db_session_maker is None:
        raise HTTPException(500, "Database not initialized")
    return db_session_maker()

@router.get("/models", response_model=AvailableModelsResponse)
async def get_available_models_endpoint():
    """Get the list of available models for agent configuration"""
    from app.classes.model_config import fetch_openrouter_models, DEFAULT_MODEL
    
    try:
        models_dict = await fetch_openrouter_models()
        models = [
            AvailableModel(
                id=model_id,
                name=model_info["name"],
                description=model_info["description"],
                provider=model_info["provider"]
            )
            for model_id, model_info in models_dict.items()
        ]
        return AvailableModelsResponse(models=models, default_model=DEFAULT_MODEL)
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch available models: {str(e)}")

@router.post("")
async def create_and_run_simulation(req: CreateSimRequest, svc=Depends(get_service), db: Session = Depends(get_db)):
    """Create simulation and start running it immediately in the background"""
    if len(req.agents) == 0:
        raise HTTPException(400, "At least one agent must be provided")
    
    # Temporary user ID until auth is implemented
    temp_user_id = UUID("00000000-0000-0000-0000-000000000000")
    
    # Handle config auto-save if config_id is provided
    config = None
    if req.config_id:
        try:
            config_uuid = UUID(req.config_id)
            config = create_or_update_config(
                db=db,
                config_id=config_uuid,
                name=req.config_name,
                description=req.config_description,
                parameters={
                    "topic": req.topic,
                    "max_iters": req.max_iters,
                    "bias": req.bias,
                    "stance": req.stance,
                    "embedding_model": req.embedding_model,
                    "embedding_config": req.embedding_config
                },
                agents=req.agents,
                user_id=temp_user_id
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, f"Failed to update config: {str(e)}")
    
    # Build config snapshot for the run
    config_snapshot = build_config_snapshot(
        topic=req.topic,
        agents=req.agents,
        max_iters=req.max_iters,
        bias=req.bias,
        stance=req.stance,
        embedding_model=req.embedding_model,
        embedding_config=req.embedding_config
    )
    
    # Create Run record in database
    run = Run(
        user_id=temp_user_id,
        config_id=config.id if config else None,
        config_version_when_run=config.version_number if config else None,
        config_snapshot=config_snapshot,
        status="created"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    # Start background simulation (no db session passed)
    asyncio.create_task(svc.run_simulation_background(run.id, req))
    
    return {
        "simulation_id": str(run.id),
        "status": "created",
        "message": "Simulation started, use GET /simulations/{id} to check progress"
    }

@router.get("/{sim_id}", response_model=RunResponse)
async def get_simulation_status(sim_id: str, db: Session = Depends(get_db)):
    """Get current simulation state and progress"""
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    # Get run status
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    # Get config name and check if version is latest
    config_name = None
    is_latest_version = None
    if run.config_id:
        config = db.get(Config, run.config_id)
        if config:
            config_name = config.name
            is_latest_version = run.config_version_when_run == config.version_number
    
    # Get recent events (last 10 for better context)
    recent_events_stmt = (
        select(RunEvent)
        .where(RunEvent.run_id == run_uuid)
        .order_by(RunEvent.iteration.desc())
        .limit(10)
    )
    recent_events = db.exec(recent_events_stmt).all()
    
    # Calculate progress
    max_iters = run.config_snapshot.get("max_iters", 21)
    progress_percentage = (run.iters / max_iters) * 100 if max_iters > 0 else 0
    
    return RunResponse(
        simulation_id=str(run.id),
        config_id=str(run.config_id) if run.config_id else None,
        config_name=config_name,
        config_version_when_run=run.config_version_when_run,
        is_latest_version=is_latest_version,
        status=run.status,
        progress={
            "current_iteration": run.iters,
            "max_iterations": max_iters,
            "percentage": min(progress_percentage, 100)
        },
        latest_events=[
            {
                "iteration": event.iteration,
                "speaker": event.speaker,
                "opinion": event.opinion[:300] + "..." if len(event.opinion) > 300 else event.opinion,
                "engaged": event.engaged,
                "finished": event.finished,
                "timestamp": event.created_at.isoformat()
            }
            for event in reversed(recent_events)  # Chronological order
        ],
        is_finished=run.finished,
        stopped_reason=run.stopped_reason,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at
    )

@router.post("/{sim_id}/stop")
async def stop_simulation(sim_id: str, db: Session = Depends(get_db)):
    """Stop a running simulation"""
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if run.finished:
        raise HTTPException(400, "Simulation already finished")
    
    # Mark as stopped - background task will pick this up
    run.status = "stopped"
    run.stopped_reason = "user_requested"
    db.add(run)
    db.commit()
    
    return {
        "simulation_id": str(run.id),
        "status": "stopped",
        "message": "Stop request submitted"
    }

@router.post("/{sim_id}/vote")
async def vote_simulation(sim_id: str, svc=Depends(get_service), db: Session = Depends(get_db)):
    """Trigger voting phase for a completed simulation"""
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if not run.finished:
        raise HTTPException(400, "Simulation must be finished before voting")
    
    # This will need to be implemented in the service
    yea, nay, reasons = await svc.trigger_voting(run_uuid, db)
    
    return {
        "simulation_id": str(run.id),
        "yea": yea,
        "nay": nay,
        "reasons": reasons
    }
