from typing import List
from uuid import UUID
import logging
import json
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlmodel import Session, select

from app.api.schemas import ConfigsListResponse, ConfigResponse, ConfigListItem, AgentSnapshotResponse, RunsListResponse, RunListItem, CreateConfigRequest, UpdateConfigRequest
from app.services.config_service import update_config_manual
from app.models import Config, ConfigAgent, Run
from app.dependencies import get_db

router = APIRouter(prefix="/configs", tags=["configs"])
logger = logging.getLogger(__name__)

def log_config_object(operation: str, config: Config, additional_info: str = "", db: Session = None):
    """Helper function to log config objects in a readable format"""
    try:
        config_dict = {
            "id": str(config.id),
            "name": config.name,
            "description": config.description,
            "parameters": config.parameters,
            "version_number": config.version_number,
            "source_template_id": str(config.source_template_id) if config.source_template_id else None,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
        
        # Also log the agent snapshots to see canvas positions
        if db:
            try:
                agent_stmt = (
                    select(ConfigAgent)
                    .where(ConfigAgent.config_id == config.id)
                    .order_by(ConfigAgent.position)
                )
                agent_snapshots = db.exec(agent_stmt).all()
                config_dict["agent_snapshots"] = [
                    {
                        "position": snapshot.position,
                        "name": snapshot.name,
                        "canvas_position": snapshot.canvas_position,
                        "snapshot": snapshot.snapshot
                    }
                    for snapshot in agent_snapshots
                ]
            except Exception as e:
                config_dict["agent_snapshots"] = f"Error loading snapshots: {e}"
        
        logger.info(f"CONFIG {operation.upper()}: {additional_info}")
        logger.info(f"Config object: {json.dumps(config_dict, indent=2)}")
    except Exception as e:
        logger.error(f"Failed to log config object: {e}")
        logger.info(f"CONFIG {operation.upper()}: {additional_info} (logging failed)")

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
        logger.info(f"RETRIEVE CONFIGS: Getting configs with limit={limit}, offset={offset}")
        
        # Query for all configs (no visibility filtering - configs are always private)
        stmt = (
            select(Config)
            .order_by(Config.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        configs = db.exec(stmt).all()
        
        logger.info(f"RETRIEVE CONFIGS: Found {len(configs)} configs")
        for i, config in enumerate(configs):
            log_config_object("RETRIEVE", config, f"Config {i+1}/{len(configs)} in list", db)
        
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
        logger.error(f"RETRIEVE CONFIGS ERROR: {e}")
        raise HTTPException(500, f"Failed to fetch configs: {str(e)}")

@router.post("", response_model=ConfigResponse)
async def create_config(req: CreateConfigRequest, db: Session = Depends(get_db)):
    """
    Create a new blank/default config. Returns the config ID and default values.
    This is used by the frontend editor which requires a config ID to operate.
    """
    try:
        logger.info(f"CREATE CONFIG: Starting creation of new config")
        logger.info(f"Create request: {req}")
        
        # Temporary user ID until auth is implemented
        temp_user_id = UUID("00000000-0000-0000-0000-000000000000")
        
        # Create a default config with minimal parameters
        default_parameters = {
            "topic": "Should artificial intelligence development be regulated by government?",
            "max_iters": 21,
            "bias": [],
            "stance": "",
            "embedding_model": "onnx_minilm",
            "embedding_config": {}
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
        
        log_config_object("CREATE", config, "Newly created config", db)
        
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
        logger.error(f"CREATE CONFIG ERROR: {e}")
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
        logger.error(f"UPDATE CONFIG ERROR: Invalid UUID format for config_id={config_id}")
        raise HTTPException(400, "Invalid config ID format")
    
    try:
        logger.info(f"UPDATE CONFIG: Starting update for config_id={config_id}")
        logger.info(f"Update request: {json.dumps(req.dict(exclude_unset=True), indent=2)}")
        
        # Log the config BEFORE update
        existing_config = db.get(Config, config_uuid)
        if existing_config:
            log_config_object("UPDATE_BEFORE", existing_config, f"Config before update (ID: {config_id})", db)
        else:
            logger.warning(f"UPDATE CONFIG: Config not found with ID={config_id}")
        
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
        
        # Log the config AFTER update
        log_config_object("UPDATE_AFTER", config, f"Config after update (ID: {config_id})", db)
        
        # Get updated agent snapshots
        agent_stmt = (
            select(ConfigAgent)
            .where(ConfigAgent.config_id == config_uuid)
            .order_by(ConfigAgent.position)
        )
        agent_snapshots = db.exec(agent_stmt).all()
        
        agents = [
            AgentSnapshotResponse(
                position=snapshot.position,
                name=snapshot.name,
                background=snapshot.background,
                canvas_position=snapshot.canvas_position,
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
        logger.error(f"UPDATE CONFIG ERROR: {e}")
        raise HTTPException(404, str(e))
    except Exception as e:
        logger.error(f"UPDATE CONFIG ERROR: {e}")
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
        logger.error(f"RETRIEVE SINGLE CONFIG ERROR: Invalid UUID format for config_id={config_id}")
        raise HTTPException(400, "Invalid config ID format")
    
    try:
        logger.info(f"RETRIEVE SINGLE CONFIG: Getting config with ID={config_id}")
        
        # Get the config (no visibility filtering needed for configs)
        config = db.get(Config, config_uuid)
        if not config:
            logger.warning(f"RETRIEVE SINGLE CONFIG: Config not found with ID={config_id}")
            raise HTTPException(404, "Config not found")
        
        log_config_object("RETRIEVE_SINGLE", config, f"Single config retrieval (ID: {config_id})", db)
        
        # Get agents for this config
        agent_stmt = (
            select(ConfigAgent)
            .where(ConfigAgent.config_id == config_uuid)
            .order_by(ConfigAgent.position)
        )
        agent_snapshots = db.exec(agent_stmt).all()
        
        agents = [
            AgentSnapshotResponse(
                position=snapshot.position,
                name=snapshot.name,
                background=snapshot.background,
                canvas_position=snapshot.canvas_position,
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"RETRIEVE SINGLE CONFIG ERROR: {e}")
        raise HTTPException(500, f"Failed to get config: {str(e)}")


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
