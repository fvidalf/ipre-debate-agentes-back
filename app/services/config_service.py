"""
Helper functions for config management and versioning.
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select
from app.models import Config, ConfigAgentSnapshot
from app.api.schemas import AgentConfig


def build_config_snapshot(
    topic: str,
    agents: List[AgentConfig],
    max_iters: int = 21,
    bias: Optional[List[float]] = None,
    stance: str = "",
    embedding_model: str = "onnx_minilm",
    embedding_config: Optional[dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """Build a standardized config snapshot from request parameters."""
    return {
        "topic": topic,
        "agents": [
            {
                "name": agent.name,
                "profile": agent.profile,
                "model_id": agent.model_id
            }
            for agent in agents
        ],
        "max_iters": max_iters,
        "bias": bias,
        "stance": stance,
        "embedding_model": embedding_model,
        "embedding_config": embedding_config or {},
        **kwargs
    }


def create_or_update_config(
    db: Session,
    config_id: Optional[UUID],
    name: str,
    description: Optional[str],
    parameters: Dict[str, Any],
    agents: List[AgentConfig],
    user_id: UUID,
    source_template_id: Optional[UUID] = None
) -> Config:
    """
    Create a new config or update existing one with version increment.
    This handles the auto-save logic when a user runs a simulation.
    """
    if config_id:
        # Update existing config
        config = db.get(Config, config_id)
        if not config:
            raise ValueError(f"Config {config_id} not found")
        
        # Check if anything actually changed
        current_snapshot = build_config_snapshot(**parameters, agents=agents)
        if config.parameters != current_snapshot:
            # Config changed, increment version
            config.version_number += 1
            config.parameters = current_snapshot
            config.updated_at = datetime.utcnow()
            
            # Update agent snapshots
            _update_config_agents(db, config.id, agents)
        
        return config
    else:
        # Create new config
        config_snapshot = build_config_snapshot(**parameters, agents=agents)
        config = Config(
            owner_user_id=user_id,
            name=name,
            description=description,
            parameters=config_snapshot,
            version_number=1,
            source_template_id=source_template_id
        )
        db.add(config)
        db.flush()  # Get the ID
        
        # Create agent snapshots
        _create_config_agents(db, config.id, agents)
        
        return config


def update_config_manual(
    db: Session,
    config_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    topic: Optional[str] = None,
    agents: Optional[List[AgentConfig]] = None,
    max_iters: Optional[int] = None,
    bias: Optional[List[float]] = None,
    stance: Optional[str] = None,
    embedding_model: Optional[str] = None,
    embedding_config: Optional[dict] = None
) -> Config:
    """
    Manually update a config (for PATCH endpoint). 
    Only updates provided fields, increments version if parameters changed.
    """
    config = db.get(Config, config_id)
    if not config:
        raise ValueError(f"Config {config_id} not found")
    
    # Track if anything changed
    changed = False
    
    # Update metadata fields
    if name is not None and config.name != name:
        config.name = name
        changed = True
    
    if description is not None and config.description != description:
        config.description = description
        changed = True
    
    # Build new parameters from current + updates
    current_params = config.parameters.copy()
    
    if topic is not None:
        current_params["topic"] = topic
    if max_iters is not None:
        current_params["max_iters"] = max_iters
    if bias is not None:
        current_params["bias"] = bias
    if stance is not None:
        current_params["stance"] = stance
    if embedding_model is not None:
        current_params["embedding_model"] = embedding_model
    if embedding_config is not None:
        current_params["embedding_config"] = embedding_config
    
    # Handle agents update
    if agents is not None:
        current_params["agents"] = [
            {
                "name": agent.name,
                "profile": agent.profile,
                "model_id": agent.model_id
            }
            for agent in agents
        ]
    
    # Check if parameters changed
    if config.parameters != current_params:
        config.parameters = current_params
        config.version_number += 1
        changed = True
        
        # Update agent snapshots if agents were provided
        if agents is not None:
            _update_config_agents(db, config.id, agents)
    
    if changed:
        config.updated_at = datetime.utcnow()
    
    return config


def _create_config_agents(db: Session, config_id: UUID, agents: List[AgentConfig]):
    """Create agent snapshots for a config."""
    for position, agent in enumerate(agents, 1):
        agent_snapshot = ConfigAgentSnapshot(
            config_id=config_id,
            position=position,
            name=agent.name,
            background=None,  # Could be extracted from profile if needed
            snapshot={
                "profile": agent.profile,
                "model_id": agent.model_id
            }
        )
        db.add(agent_snapshot)


def _update_config_agents(db: Session, config_id: UUID, agents: List[AgentConfig]):
    """Update agent snapshots for a config."""
    # Delete existing agents
    existing_agents = db.exec(
        select(ConfigAgentSnapshot).where(ConfigAgentSnapshot.config_id == config_id)
    ).all()
    for agent in existing_agents:
        db.delete(agent)
    
    # Create new agents
    _create_config_agents(db, config_id, agents)


def config_needs_update(config: Config, new_parameters: Dict[str, Any]) -> bool:
    """Check if a config needs to be updated based on new parameters."""
    return config.parameters != new_parameters
