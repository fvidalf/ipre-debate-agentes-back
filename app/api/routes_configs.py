from typing import List
from uuid import UUID
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlmodel import Session, select

from app.api.schemas import ConfigsListResponse, ConfigResponse, ConfigListItem, AgentSnapshotResponse, RunsListResponse, RunListItem, CreateConfigRequest, UpdateConfigRequest
from app.services.config_service import update_config_manual
from app.models import Config, ConfigAgentSnapshot, Run

router = APIRouter(prefix="/configs", tags=["configs"])
logger = logging.getLogger(__name__)

def get_db(request: Request):
    db_session_maker = getattr(request.app.state, "db_session", None)
    if db_session_maker is None:
        raise HTTPException(500, "Database not initialized")
    return db_session_maker()

@router.get("", response_model=ConfigsListResponse)
async def get_configs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100, description="Number of configs to return"),
    offset: int = Query(0, ge=0, description="Number of configs to skip")
):
    """
    Get all configs. Since authentication is not implemented yet, all configs are returned.
    Configs are always private/personal (unlike templates which can be public).
    """
    try:
        # Query for all configs (no visibility filtering - configs are always private)
        stmt = (
            select(Config)
            .order_by(Config.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        configs = db.exec(stmt).all()
        
        # Count total configs
        count_stmt = select(Config)
        total_count = len(db.exec(count_stmt).all())
        
        # Convert to response format (no agents in list view)
        config_responses = [
            ConfigListItem(
                id=str(config.id),
                name=config.name,
                description=config.description,
                parameters=config.parameters,
                version_number=config.version_number,
                source_template_id=str(config.source_template_id) if config.source_template_id else None,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in configs
        ]
        
        return ConfigsListResponse(
            configs=config_responses,
            total=total_count
        )
        
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch configs: {str(e)}")

@router.post("", response_model=ConfigResponse)
async def create_config(req: CreateConfigRequest, db: Session = Depends(get_db)):
    """
    Create a new blank/default config. Returns the config ID and default values.
    This is used by the frontend editor which requires a config ID to operate.
    """
    try:
        # Temporary user ID until auth is implemented
        temp_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # Create a default config with minimal parameters
        default_parameters = {
            "topic": "",
            "max_iters": 21,
            "bias": [],
            "stance": "",
            "embedding_model": "onnx_minilm",
            "embedding_config": {},
            "agents": []
        }
        
        config = Config(
            owner_user_id=temp_user_id,
            name="Untitled Config",
            description=None,
            parameters=default_parameters,
            version_number=1
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        
        # Return the config with empty agents list (no agent snapshots yet)
        return ConfigResponse(
            id=str(config.id),
            name=config.name,
            description=config.description,
            parameters=config.parameters,
            version_number=config.version_number,
            agents=[],  # Empty - will be populated when user adds agents
            source_template_id=None,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except Exception as e:
        raise HTTPException(500, f"Failed to create config: {str(e)}")

@router.patch("/{config_id}", response_model=ConfigResponse)
async def update_config(
    config_id: str,
    req: UpdateConfigRequest,
    db: Session = Depends(get_db)
):
    """
    Update a config with new values. Only provided fields are updated.
    Increments version number if parameters change.
    """
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(400, "Invalid config ID format")
    
    try:
        # Update config using the manual update function
        config = update_config_manual(
            db=db,
            config_id=config_uuid,
            name=req.name,
            description=req.description,
            topic=req.topic,
            agents=req.agents,
            max_iters=req.max_iters,
            bias=req.bias,
            stance=req.stance,
            embedding_model=req.embedding_model,
            embedding_config=req.embedding_config
        )
        
        db.commit()
        
        # Get updated agent snapshots
        agent_stmt = (
            select(ConfigAgentSnapshot)
            .where(ConfigAgentSnapshot.config_id == config_uuid)
            .order_by(ConfigAgentSnapshot.position)
        )
        agent_snapshots = db.exec(agent_stmt).all()
        
        agents = [
            AgentSnapshotResponse(
                position=snapshot.position,
                name=snapshot.name,
                background=snapshot.background,
                snapshot=snapshot.snapshot,
                created_at=snapshot.created_at
            )
            for snapshot in agent_snapshots
        ]
        
        return ConfigResponse(
            id=str(config.id),
            name=config.name,
            description=config.description,
            parameters=config.parameters,
            version_number=config.version_number,
            agents=agents,
            source_template_id=str(config.source_template_id) if config.source_template_id else None,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Failed to update config: {str(e)}")

@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config(
    config_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific config by ID. Since auth is not implemented, any config can be accessed.
    """
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(400, "Invalid config ID format")
    
    # Get the config (no visibility filtering needed for configs)
    config = db.get(Config, config_uuid)
    if not config:
        raise HTTPException(404, "Config not found")
    
    # Get agents for this config
    agent_stmt = (
        select(ConfigAgentSnapshot)
        .where(ConfigAgentSnapshot.config_id == config_uuid)
        .order_by(ConfigAgentSnapshot.position)
    )
    agent_snapshots = db.exec(agent_stmt).all()
    
    agents = [
        AgentSnapshotResponse(
            position=snapshot.position,
            name=snapshot.name,
            background=snapshot.background,
            snapshot=snapshot.snapshot,
            created_at=snapshot.created_at
        )
        for snapshot in agent_snapshots
    ]
    
    return ConfigResponse(
        id=str(config.id),
        name=config.name,
        description=config.description,
        parameters=config.parameters,
        version_number=config.version_number,
        agents=agents,
        source_template_id=str(config.source_template_id) if config.source_template_id else None,
        created_at=config.created_at,
        updated_at=config.updated_at
    )


@router.get("/{config_id}/runs", response_model=RunsListResponse)
async def get_config_runs(
    config_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100, description="Number of runs to return"),
    offset: int = Query(0, ge=0, description="Number of runs to skip")
):
    """
    Get all runs for a specific config, regardless of version.
    Shows which version each run used and whether it's on the latest version.
    """
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(400, "Invalid config ID format")
    
    # Verify config exists and is accessible (no filtering needed - all configs accessible without auth)
    config = db.get(Config, config_uuid)
    if not config:
        raise HTTPException(404, "Config not found")
    
    # Get runs for this config
    stmt = (
        select(Run)
        .where(Run.config_id == config_uuid)
        .order_by(Run.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    
    runs = db.exec(stmt).all()
    
    # Build response with version info
    run_items = [
        RunListItem(
            simulation_id=str(run.id),
            config_id=str(run.config_id) if run.config_id else None,
            config_name=config.name,
            config_version_when_run=run.config_version_when_run,
            is_latest_version=run.config_version_when_run == config.version_number if run.config_version_when_run else None,
            status=run.status,
            is_finished=run.finished,
            created_at=run.created_at,
            finished_at=run.finished_at
        )
        for run in runs
    ]
    
    # Count total runs for this config
    count_stmt = select(Run).where(Run.config_id == config_uuid)
    total = len(db.exec(count_stmt).all())
    
    return RunsListResponse(runs=run_items, total=total)
