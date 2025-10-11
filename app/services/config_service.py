"""
Helper functions for config management and versioning.
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime
from sqlmodel import Session, select
from app.models import Config, ConfigAgent, ConfigVersion
from app.api.schemas import AgentConfig


def create_config_version(
    db: Session,
    config_id: UUID,
    version_number: int,
    topic: str,
    agents: List[AgentConfig],
    max_iters: int = 21,
    bias: Optional[List[float]] = None,
    stance: str = "",
    embedding_model: str = "onnx_minilm",
    embedding_config: Optional[dict] = None,
    max_interventions_per_agent: Optional[int] = None,
    **kwargs
) -> ConfigVersion:
    """Create a ConfigVersion record with complete config state."""
    parameters = {
        "topic": topic,
        "max_iters": max_iters,
        "bias": bias,
        "stance": stance,
        "embedding_model": embedding_model,
        "embedding_config": embedding_config or {},
        "max_interventions_per_agent": max_interventions_per_agent,
        **kwargs
    }
    
    # Load existing canvas positions from ConfigAgent table
    existing_agents = db.exec(
        select(ConfigAgent)
        .where(ConfigAgent.config_id == config_id)
        .order_by(ConfigAgent.position)
    ).all()
    
    # Create a mapping of position -> canvas_position for existing agents
    canvas_positions = {agent.position: agent.canvas_position for agent in existing_agents}
    
    agents_data = []
    for i, agent in enumerate(agents):
        position = i + 1  # Positions start from 1
        
        # Use canvas position from request if provided, otherwise use saved position
        canvas_pos = None
        if agent.canvas_position:
            canvas_pos = agent.canvas_position.dict()
        elif position in canvas_positions and canvas_positions[position]:
            canvas_pos = canvas_positions[position]
        
        agents_data.append({
            "name": agent.name,
            "profile": agent.profile,
            "model_id": agent.model_id,
            "lm_config": agent.lm_config.dict() if agent.lm_config else None,
            "canvas_position": canvas_pos
        })
    
    # Check if version already exists (shouldn't happen, but just in case)
    existing_version = db.exec(
        select(ConfigVersion).where(
            ConfigVersion.config_id == config_id,
            ConfigVersion.version_number == version_number
        )
    ).first()
    
    if existing_version:
        # Update existing version
        existing_version.parameters = parameters
        existing_version.agents = agents_data
        db.add(existing_version)
        return existing_version
    else:
        # Create new version
        version = ConfigVersion(
            config_id=config_id,
            version_number=version_number,
            parameters=parameters,
            agents=agents_data
        )
        db.add(version)
        return version


def get_config_version(
    db: Session,
    config_id: UUID,
    version_number: int
) -> Optional[ConfigVersion]:
    """Get a specific config version by config_id and version_number."""
    return db.exec(
        select(ConfigVersion).where(
            ConfigVersion.config_id == config_id,
            ConfigVersion.version_number == version_number
        )
    ).first()


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
        if config.parameters != parameters:
            # Config changed, increment version
            config.version_number += 1
            config.parameters = parameters
            config.updated_at = datetime.utcnow()
            
            # Create version record for this new version
            create_config_version(
                db=db,
                config_id=config.id,
                version_number=config.version_number,
                agents=agents,
                **parameters
            )
            
            # Update agent snapshots in current config
            _update_config_agents(db, config.id, agents)
        
        return config
    else:
        # Create new config
        config = Config(
            owner_user_id=user_id,
            name=name,
            description=description,
            parameters=parameters,
            version_number=1,
            source_template_id=source_template_id
        )
        db.add(config)
        db.flush()  # Get the ID
        
        # Create version record for version 1
        create_config_version(
            db=db,
            config_id=config.id,
            version_number=1,
            agents=agents,
            **parameters
        )
        
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
    embedding_config: Optional[dict] = None,
    max_interventions_per_agent: Optional[int] = None
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
    if max_interventions_per_agent is not None:
        current_params["max_interventions_per_agent"] = max_interventions_per_agent
    
    # Handle agents update
    if agents is not None:
        # Agents are no longer stored in parameters - only in ConfigAgent table
        # Update agent snapshots if agents were provided
        _update_config_agents(db, config.id, agents)
        changed = True
    
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
        # Extract canvas position if provided
        canvas_position = None
        if agent.canvas_position:
            canvas_position = {
                "x": agent.canvas_position.x,
                "y": agent.canvas_position.y
            }
        
        agent_snapshot = ConfigAgent(
            config_id=config_id,
            position=position,
            name=agent.name,
            background=None,  # Could be extracted from profile if needed
            canvas_position=canvas_position,
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
        select(ConfigAgent).where(ConfigAgent.config_id == config_id)
    ).all()
    for agent in existing_agents:
        db.delete(agent)
    
    # Flush deletes to ensure they take effect before inserts
    db.flush()
    
    # Create new agents
    _create_config_agents(db, config_id, agents)


def config_needs_update(config: Config, new_parameters: Dict[str, Any]) -> bool:
    """Check if a config needs to be updated based on new parameters."""
    return config.parameters != new_parameters
