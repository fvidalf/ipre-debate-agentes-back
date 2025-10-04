from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session

from app.api.schemas import ConfigResponse, AgentSnapshotResponse, CanvasPosition
from app.services.config_service import get_config_version
from app.models import Config, User
from app.dependencies import get_db, get_current_user

router = APIRouter(prefix="/config-versions", tags=["config-versions"])

@router.get("/{config_id}/versions/{version_number}", response_model=ConfigResponse)
async def get_config_version_endpoint(
    config_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific config version by config ID and version number.
    This returns the complete config state as it existed at that version,
    including all agents and their configurations.
    Only the config owner can access their config versions.
    """
    try:
        config_uuid = UUID(config_id)
    except ValueError:
        raise HTTPException(400, "Invalid config ID format")
    
    # Get the config to check if it exists and verify ownership
    config = db.get(Config, config_uuid)
    if not config:
        raise HTTPException(404, "Config not found")
    
    if config.owner_user_id != current_user.id:
        raise HTTPException(404, "Config not found")  # Don't reveal that it exists but is not accessible
    
    # Get the version for the specific version number
    version = get_config_version(db, config_uuid, version_number)
    if not version:
        raise HTTPException(404, f"Version not found for config {config_id} version {version_number}")
    
    # Convert agents from version format to AgentSnapshotResponse format
    agents = []
    for i, agent_data in enumerate(version.agents):
        canvas_position = None
        if agent_data.get("canvas_position"):
            canvas_position = CanvasPosition(
                x=agent_data["canvas_position"]["x"],
                y=agent_data["canvas_position"]["y"]
            )
        
        agents.append(AgentSnapshotResponse(
            position=i + 1,  # Position starts from 1
            name=agent_data.get("name"),
            background=None,  # Not stored in version, could be added if needed
            canvas_position=canvas_position,
            snapshot={  # Note: This field name "snapshot" is correct - it contains the agent's configuration snapshot
                "profile": agent_data.get("profile", ""),
                "model_id": agent_data.get("model_id", "")
            },
            created_at=version.created_at
        ))
    
    # Return in the same format as regular config endpoint
    return ConfigResponse(
        id=str(config.id),
        name=f"{config.name} (v{version_number})",  # Indicate it's a historical version
        description=config.description,
        parameters=version.parameters,
        version_number=version_number,
        agents=agents,
        source_template_id=str(config.source_template_id) if config.source_template_id else None,
        created_at=version.created_at,  # Use version creation time
        updated_at=version.created_at   # Versions are immutable
    )