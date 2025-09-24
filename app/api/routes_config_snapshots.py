from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session

from app.api.schemas import ConfigResponse, AgentSnapshotResponse, CanvasPosition
from app.services.config_service import get_config_snapshot
from app.models import Config
from app.dependencies import get_db

router = APIRouter(prefix="/config-snapshots", tags=["config-snapshots"])

@router.get("/{config_id}/versions/{version_number}", response_model=ConfigResponse)
async def get_config_snapshot_version(
    config_id: str,
    version_number: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific config snapshot by config ID and version number.
    This returns the complete config state as it existed at that version,
    including all agents and their configurations.
    """
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(400, "Invalid config ID format")
    
    # Get the config to check if it exists and get metadata
    config = db.get(Config, config_uuid)
    if not config:
        raise HTTPException(404, "Config not found")
    
    # Get the snapshot for the specific version
    snapshot = get_config_snapshot(db, config_uuid, version_number)
    if not snapshot:
        raise HTTPException(404, f"Snapshot not found for config {config_id} version {version_number}")
    
    # Convert agents from snapshot format to AgentSnapshotResponse format
    agents = []
    for i, agent_data in enumerate(snapshot.agents):
        canvas_position = None
        if agent_data.get("canvas_position"):
            canvas_position = CanvasPosition(
                x=agent_data["canvas_position"]["x"],
                y=agent_data["canvas_position"]["y"]
            )
        
        agents.append(AgentSnapshotResponse(
            position=i + 1,  # Position starts from 1
            name=agent_data.get("name"),
            background=None,  # Not stored in snapshot, could be added if needed
            canvas_position=canvas_position,
            snapshot={
                "profile": agent_data.get("profile", ""),
                "model_id": agent_data.get("model_id", "")
            },
            created_at=snapshot.created_at
        ))
    
    # Return in the same format as regular config endpoint
    return ConfigResponse(
        id=str(config.id),
        name=f"{config.name} (v{version_number})",  # Indicate it's a historical version
        description=config.description,
        parameters=snapshot.parameters,
        version_number=version_number,
        agents=agents,
        source_template_id=str(config.source_template_id) if config.source_template_id else None,
        created_at=snapshot.created_at,  # Use snapshot creation time
        updated_at=snapshot.created_at   # Snapshots are immutable
    )