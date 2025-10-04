from typing import List
from uuid import UUID
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlmodel import Session, select

from app.api.schemas import AgentTemplatesListResponse, AgentTemplateResponse
from app.models import Agent, User
from app.dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agents", tags=["agents"])



@router.get("/templates", response_model=AgentTemplatesListResponse)
async def get_agent_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=100, description="Number of templates to return"),
    offset: int = Query(0, ge=0, description="Number of templates to skip")
):
    """
    Get agent templates: public templates plus user's private templates.
    Authentication required for platform access.
    """
    try:
        logger.info(f"Getting agent templates for user {current_user.email} with limit={limit}, offset={offset}")
        
        # Query for public agents AND user's private agents
        stmt = (
            select(Agent)
            .where(
                (Agent.visibility == "public") |
                (Agent.owner_user_id == current_user.id)
            )
            .order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        logger.debug(f"Executing query: {stmt}")
        agents = db.exec(stmt).all()
        logger.info(f"Found {len(agents)} agents")
        
        # Count total templates (public + user's private)
        count_stmt = (
            select(Agent)
            .where(
                (Agent.visibility == "public") |
                (Agent.owner_user_id == current_user.id)
            )
        )
        logger.debug(f"Executing count query: {count_stmt}")
        total_count = len(db.exec(count_stmt).all())
        logger.info(f"Total count: {total_count}")
        
        # Convert to response format
        agent_responses = [
            AgentTemplateResponse(
                id=str(agent.id),
                name=agent.name,
                description=agent.description,
                visibility=agent.visibility,
                config=agent.config,
                created_at=agent.created_at,
                updated_at=agent.updated_at
            )
            for agent in agents
        ]
        
        response = AgentTemplatesListResponse(
            agents=agent_responses,
            total=total_count
        )
        logger.info(f"Successfully returning {len(agent_responses)} agent templates")
        return response
        
    except Exception as e:
        logger.error(f"Error fetching agent templates: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to fetch agent templates: {str(e)}")

@router.get("/templates/{agent_id}", response_model=AgentTemplateResponse)
async def get_agent_template(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific agent template by ID. Shows public templates or user's private templates.
    Authentication required for platform access.
    """
    logger.info(f"Getting agent template with ID: {agent_id} for user {current_user.email}")
    try:
        agent_uuid = UUID(agent_id)
    except ValueError:
        logger.warning(f"Invalid agent ID format: {agent_id}")
        raise HTTPException(400, "Invalid agent ID format")
    
    try:
        # Get the agent
        agent = db.get(Agent, agent_uuid)
        if not agent:
            logger.warning(f"Agent template not found: {agent_uuid}")
            raise HTTPException(404, "Agent template not found")
        
        # Check access: public templates or user's own private templates
        if agent.visibility == "public" or agent.owner_user_id == current_user.id:
            # Accessible: public template or user's own private template
            pass
        else:
            # Private template belonging to someone else - not accessible
            logger.warning(f"Agent template access denied for user {current_user.email}: {agent_uuid}")
            raise HTTPException(404, "Agent template not found")  # Don't reveal private agents exist
        
        logger.info(f"Successfully retrieved agent template: {agent.name}")
        return AgentTemplateResponse(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            visibility=agent.visibility,
            config=agent.config,
            created_at=agent.created_at,
            updated_at=agent.updated_at
        )
    except HTTPException:
        raise  # Re-raise HTTP exceptions
    except Exception as e:
        logger.error(f"Error fetching agent template {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(500, f"Failed to fetch agent template: {str(e)}")
