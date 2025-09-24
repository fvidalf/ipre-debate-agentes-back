from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from sqlmodel import Session, select

from app.api.schemas import ConfigTemplatesListResponse, ConfigTemplateResponse, ConfigTemplateListItem, AgentSnapshotResponse
from app.models import ConfigTemplate, TemplateAgentSnapshot
from app.dependencies import get_db

router = APIRouter(prefix="/config-templates", tags=["config-templates"])



@router.get("", response_model=ConfigTemplatesListResponse)
async def get_config_templates(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100, description="Number of templates to return"),
    offset: int = Query(0, ge=0, description="Number of templates to skip")
):
    """
    Get public config templates that can be used for simulations.
    Since authentication is not implemented yet, only public templates are returned.
    """
    try:
        # Query for public config templates only (no owner_user_id and visibility = 'public')
        stmt = (
            select(ConfigTemplate)
            .where(ConfigTemplate.visibility == "public")
            .where(ConfigTemplate.owner_user_id.is_(None))
            .order_by(ConfigTemplate.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        templates = db.exec(stmt).all()
        
        # Count total public templates
        count_stmt = (
            select(ConfigTemplate)
            .where(ConfigTemplate.visibility == "public")
            .where(ConfigTemplate.owner_user_id.is_(None))
        )
        total_count = len(db.exec(count_stmt).all())
        
        # Convert to response format (no agents in list view)
        template_responses = [
            ConfigTemplateListItem(
                id=str(template.id),
                name=template.name,
                description=template.description,
                visibility=template.visibility,
                parameters=template.parameters,
                created_at=template.created_at
            )
            for template in templates
        ]
        
        return ConfigTemplatesListResponse(
            templates=template_responses,
            total=total_count
        )
        
    except Exception as e:
        raise HTTPException(500, f"Failed to fetch config templates: {str(e)}")

@router.get("/{template_id}", response_model=ConfigTemplateResponse)
async def get_config_template(
    template_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific public config template by ID.
    """
    try:
        template_uuid = UUID(template_id)
    except ValueError:
        raise HTTPException(400, "Invalid template ID format")
    
    # Get the template, but only if it's public and has no owner
    template = db.get(ConfigTemplate, template_uuid)
    if not template:
        raise HTTPException(404, "Config template not found")
    
    if template.visibility != "public" or template.owner_user_id is not None:
        raise HTTPException(404, "Config template not found")  # Don't reveal private templates exist
    
    # Get agents for this template
    agent_stmt = (
        select(TemplateAgentSnapshot)
        .where(TemplateAgentSnapshot.config_template_id == template_uuid)
        .order_by(TemplateAgentSnapshot.position)
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
    
    return ConfigTemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        visibility=template.visibility,
        parameters=template.parameters,
        agents=agents,
        created_at=template.created_at
    )
