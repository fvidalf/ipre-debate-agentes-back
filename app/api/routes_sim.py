from typing import List
from uuid import UUID
import asyncio
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select

from app.api.schemas import CreateSimRequest, AvailableModelsResponse, AvailableModel, AvailableToolsResponse, AvailableTool, RunResponse
from app.services.config_service import create_or_update_config
from app.services.analytics_service import AnalyticsService
from app.models import Run, Intervention, ToolUsage, Config, User
from app.dependencies import get_db, get_current_user

router = APIRouter(prefix="/simulations", tags=["simulations"])

def get_service(request: Request):
    svc = getattr(request.app.state, "sim_service", None)
    if svc is None:
        raise HTTPException(500, "Simulation service not initialized")
    return svc

@router.get("/models", response_model=AvailableModelsResponse)
async def get_available_models_endpoint(current_user: User = Depends(get_current_user)):
    """Get the list of available models for agent configuration. Authentication required."""
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

@router.get("/tools", response_model=AvailableToolsResponse)
async def get_available_tools_endpoint():
    """Get available tools for the frontend."""
    web_search_tools = [
        AvailableTool(
            id="wikipedia_tool",
            name="Wikipedia",
            description="Search Wikipedia articles",
            icon="BookOpen",
            config_schema={
                "enabled": {"type": "boolean", "default": False, "description": "Enable Wikipedia search"},
                "canvas_position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate on canvas"},
                        "y": {"type": "number", "description": "Y coordinate on canvas"}
                    },
                    "description": "Position of tool node on visual canvas"
                }
            }
        ),
        AvailableTool(
            id="news_tool",
            name="News",
            description="Search news articles",
            icon="Newspaper",
            config_schema={
                "enabled": {"type": "boolean", "default": False, "description": "Enable news search"},
                "sources": {"type": "array", "items": {"type": "string"}, "default": [], "description": "News source domains to search"},
                "canvas_position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate on canvas"},
                        "y": {"type": "number", "description": "Y coordinate on canvas"}
                    },
                    "description": "Position of tool node on visual canvas"
                }
            }
        ),
        AvailableTool(
            id="pages_tool",
            name="Web Pages",
            description="Search general web pages",
            icon="Globe",
            config_schema={
                "enabled": {"type": "boolean", "default": False, "description": "Enable general web page search"},
                "sources": {"type": "array", "items": {"type": "string"}, "default": [], "description": "Web page domains to search"},
                "canvas_position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate on canvas"},
                        "y": {"type": "number", "description": "Y coordinate on canvas"}
                    },
                    "description": "Position of tool node on visual canvas"
                }
            }
        ),
        AvailableTool(
            id="google_ai_tool",
            name="Google AI",
            description="Enhanced search with AI summaries",
            icon="Sparkles",
            config_schema={
                "enabled": {"type": "boolean", "default": False, "description": "Enable Google AI enhanced search"},
                "canvas_position": {
                    "type": "object",
                    "properties": {
                        "x": {"type": "number", "description": "X coordinate on canvas"},
                        "y": {"type": "number", "description": "Y coordinate on canvas"}
                    },
                    "description": "Position of tool node on visual canvas"
                }
            }
        )
    ]
    
    return AvailableToolsResponse(tools={
        "web_search_tools": web_search_tools
    })

@router.post("")
async def create_and_run_simulation(
    req: CreateSimRequest, 
    svc=Depends(get_service), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create simulation and start running it immediately in the background"""
    if len(req.agents) == 0:
        raise HTTPException(400, "At least one agent must be provided")
    
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
                    "embedding_config": req.embedding_config,
                    "max_interventions_per_agent": req.max_interventions_per_agent
                },
                agents=req.agents,
                user_id=current_user.id
            )
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(500, f"Failed to update config: {str(e)}")
    
    # Create or get config version for the run
    from app.services.config_service import create_config_version, get_config_version
    
    config_version_record = None
    if config:
        # Use existing config version if available
        config_version_record = get_config_version(db, config.id, config.version_number)
        if not config_version_record:
            # Create version if it doesn't exist (shouldn't happen, but safety check)
            config_version_record = create_config_version(
                db=db,
                config_id=config.id,
                version_number=config.version_number,
                topic=req.topic,
                agents=req.agents,
                max_iters=req.max_iters,
                bias=req.bias,
                stance=req.stance,
                embedding_model=req.embedding_model,
                embedding_config=req.embedding_config
            )
    else:
        # Create a temporary version record for runs without saved configs
        # Use a dummy config_id and version 0 for standalone runs
        from uuid import uuid4
        temp_config_id = uuid4()
        config_version_record = create_config_version(
            db=db,
            config_id=temp_config_id,
            version_number=0,
            topic=req.topic,
            agents=req.agents,
            max_iters=req.max_iters,
            bias=req.bias,
            stance=req.stance,
            embedding_model=req.embedding_model,
            embedding_config=req.embedding_config,
            max_interventions_per_agent=req.max_interventions_per_agent
        )
    
    # Create Run record in database
    run = Run(
        user_id=current_user.id,
        config_id=config.id if config else None,
        config_version_when_run=config.version_number if config else None,
        config_version_id=config_version_record.id,
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
async def get_simulation_status(
    sim_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current simulation state and progress. Only the run owner can access."""
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    # Get run status and verify ownership
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")  # Don't reveal that it exists but is not accessible
    
    # Get config name and check if version is latest
    config_name = None
    is_latest_version = None
    if run.config_id:
        config = db.get(Config, run.config_id)
        if config:
            config_name = config.name
            is_latest_version = run.config_version_when_run == config.version_number
    
    # Get recent interventions with their tool usage (last 10 for better context)
    recent_interventions_stmt = (
        select(Intervention)
        .where(Intervention.run_id == run_uuid)
        .order_by(Intervention.iteration.desc())
    )
    recent_interventions = db.exec(recent_interventions_stmt).all()
    
    # Build enhanced latest_events with tool usage
    latest_events = []
    for intervention in reversed(recent_interventions):  # Chronological order
        # Get tool usage for this intervention
        tools_stmt = (
            select(ToolUsage)
            .where(ToolUsage.intervention_id == intervention.id)
            .order_by(ToolUsage.created_at)
        )
        tool_usages = db.exec(tools_stmt).all()
        
        event_data = {
            "iteration": intervention.iteration,
            "speaker": intervention.speaker,
            "opinion": intervention.content,  # Keep "opinion" for backward compatibility
            "engaged": intervention.engaged_agents,  # Keep "engaged" for backward compatibility
            "finished": intervention.finished,
            "timestamp": intervention.created_at.isoformat(),
            # Enhanced data
            "reasoning_steps": intervention.reasoning_steps or [],  # Backward compatibility
            "prediction_metadata": intervention.prediction_metadata or {},
            "tool_usages": [  # Backward compatibility
                {
                    "id": str(tool.id),
                    "tool_name": tool.tool_name,
                    "query": tool.query,
                    "output": tool.output,
                    "execution_time": tool.execution_time,
                    "created_at": tool.created_at.isoformat()
                }
                for tool in tool_usages
            ]
        }
        
        # NEW: Add unified timeline if metadata contains it
        if intervention.prediction_metadata and intervention.prediction_metadata.get('timeline'):
            event_data["reasoning_timeline"] = intervention.prediction_metadata['timeline']
        latest_events.append(event_data)
    
    # Get config version to calculate progress
    from app.models import ConfigVersion
    config_version = None
    if run.config_version_id:
        config_version = db.get(ConfigVersion, run.config_version_id)

    max_iters = 21  # default
    if config_version:
        max_iters = config_version.parameters.get("max_iters", 21)    
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
        latest_events=latest_events,
        is_finished=run.finished,
        stopped_reason=run.stopped_reason,
        started_at=run.started_at,
        finished_at=run.finished_at,
        created_at=run.created_at
    )

@router.post("/{sim_id}/stop")
async def stop_simulation(
    sim_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Stop a running simulation. Only the run owner can stop their simulations."""
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")  # Don't reveal that it exists but is not accessible
    
    if run.finished:
        raise HTTPException(400, "Simulation already finished")
    
    # Mark as stopped - background task will pick this up
    run.status = "stopped"
    run.stopped_reason = "Manually stopped by user"
    db.add(run)
    db.commit()
    
    return {
        "simulation_id": str(run.id),
        "status": "stopped",
        "message": "Stop request submitted"
    }

@router.post("/{sim_id}/vote")
async def vote_simulation(
    sim_id: str, 
    svc=Depends(get_service), 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Trigger voting phase for a completed simulation. Only the run owner can trigger voting."""
    from app.api.schemas import VotingResponse, IndividualVote
    from app.models import Summary, ConfigAgent
    from sqlmodel import select
    
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")  # Don't reveal that it exists but is not accessible
    
    if not run.finished:
        raise HTTPException(400, "Simulation must be finished before voting")
    
    # Check if voting already exists
    existing_summary_stmt = select(Summary).where(Summary.run_id == run_uuid)
    existing_summary = db.exec(existing_summary_stmt).first()
    
    if existing_summary and existing_summary.individual_votes:
        # Return existing voting results
        summary = existing_summary
    else:
        # Trigger new voting
        yea, nay, reasons = await svc.trigger_voting(run_uuid, db)
        
        # Get the newly created summary
        summary_stmt = select(Summary).where(Summary.run_id == run_uuid)
        summary = db.exec(summary_stmt).first()
        
        if not summary:
            raise HTTPException(500, "Failed to create voting summary")
    
    # Build simplified response with essential voting information
    individual_votes = []
    if summary.individual_votes:
        for vote_data in summary.individual_votes:
            # Get agent data from the stored vote (comes from ConfigVersion.agents)
            agent_data = vote_data["agent_data"]
            
            individual_votes.append(IndividualVote(
                agent_name=agent_data.get("name", f"Agent {vote_data['agent_position']}"),
                agent_background=agent_data.get("profile", ""),  # Their stance/profile for context
                vote=vote_data["vote"],
                reasoning=vote_data["reasoning"]
            ))
    
    return VotingResponse(
        simulation_id=str(run.id),
        yea=summary.yea or 0,
        nay=summary.nay or 0,
        individual_votes=individual_votes,
        created_at=summary.created_at
    )


@router.get("/{sim_id}/votes")
async def check_votes(
    sim_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if votes exist for a simulation without triggering voting. Only the run owner can access."""
    from app.api.schemas import VotingResponse, IndividualVote
    from app.models import Summary
    from sqlmodel import select
    
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")  # Don't reveal that it exists but is not accessible
    
    # Check if voting exists
    existing_summary_stmt = select(Summary).where(Summary.run_id == run_uuid)
    existing_summary = db.exec(existing_summary_stmt).first()
    
    if not existing_summary or not existing_summary.individual_votes:
        raise HTTPException(404, "No votes found for this simulation")
    
    # Build response with existing voting data
    individual_votes = []
    for vote_data in existing_summary.individual_votes:
        # Get agent data from the stored vote (comes from ConfigVersion.agents)
        agent_data = vote_data["agent_data"]
        
        individual_votes.append(IndividualVote(
            agent_name=agent_data.get("name", f"Agent {vote_data['agent_position']}"),
            agent_background=agent_data.get("profile", ""),  # Their stance/profile for context
            vote=vote_data["vote"],
            reasoning=vote_data["reasoning"]
        ))
    
    return VotingResponse(
        simulation_id=str(run.id),
        yea=existing_summary.yea or 0,
        nay=existing_summary.nay or 0,
        individual_votes=individual_votes,
        created_at=existing_summary.created_at
    )

@router.get("/{sim_id}/analytics")
async def check_analytics(
    sim_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if analytics exist for a simulation without triggering computation. Only the run owner can access."""
    from app.models import RunAnalytics
    
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")  # Don't reveal that it exists but is not accessible
    
    # Check if analytics already exist
    existing_analytics = db.query(RunAnalytics).filter(RunAnalytics.run_id == run_uuid).first()
    
    if not existing_analytics:
        raise HTTPException(404, "No analytics found for this simulation")
    
    # Return existing analytics
    from app.services.analytics_service import AnalyticsService
    analytics_service = AnalyticsService()
    return analytics_service._format_analytics_response(existing_analytics)


@router.post("/{sim_id}/analyze")
async def analyze_simulation(
    sim_id: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compute analytics for a completed simulation (engagement matrix, participation stats, opinion similarity).
    Only the run owner can analyze their simulations.
    """
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID format")
    
    # Get run to find config for embedding settings and verify ownership
    run = db.get(Run, run_uuid)
    if not run:
        raise HTTPException(404, "Simulation not found")
    
    if run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")  # Don't reveal that it exists but is not accessible
    
    # Create analytics service (uses shared embedding service internally)
    analytics_service = AnalyticsService()
    
    # Use short-lived session pattern
    analytics = analytics_service.get_or_compute_analytics(run_uuid, db)
    
    if analytics is None:
        raise HTTPException(404, "Simulation not found")
    
    if "error" in analytics:
        raise HTTPException(400, analytics["error"])
    
    return analytics


# -----------------------
# NEW: Enhanced Data Endpoints
# -----------------------

@router.get("/{sim_id}/interventions")
async def get_simulation_interventions(
    sim_id: str,
    include_reasoning: bool = False,
    include_tools: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get interventions (enhanced version of events) with optional reasoning and tool data.
    
    Query Parameters:
    - include_reasoning: Include internal reasoning steps in response
    - include_tools: Include tool usage data for each intervention
    """
    from app.models import Intervention, ToolUsage
    
    try:
        run_uuid = UUID(sim_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation ID")
    
    # Check if user owns this run
    run = db.get(Run, run_uuid)
    if not run or run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")
    
    # Get interventions
    interventions_stmt = (
        select(Intervention)
        .where(Intervention.run_id == run_uuid)
        .order_by(Intervention.iteration)
    )
    interventions = db.exec(interventions_stmt).all()
    
    # Build response
    result = []
    for intervention in interventions:
        intervention_data = {
            "id": str(intervention.id),
            "iteration": intervention.iteration,
            "speaker": intervention.speaker,
            "content": intervention.content,
            "engaged_agents": intervention.engaged_agents,
            "finished": intervention.finished,
            "stopped_reason": intervention.stopped_reason,
            "created_at": intervention.created_at.isoformat()
        }
        
        # Include reasoning if requested
        if include_reasoning and intervention.reasoning_steps:
            intervention_data["reasoning_steps"] = intervention.reasoning_steps
        
        # Include prediction metadata if available
        if intervention.prediction_metadata:
            intervention_data["prediction_metadata"] = intervention.prediction_metadata
        
        # Include tool usage if requested
        if include_tools:
            tools_stmt = (
                select(ToolUsage)
                .where(ToolUsage.intervention_id == intervention.id)
            )
            tools = db.exec(tools_stmt).all()
            
            intervention_data["tool_usages"] = [
                {
                    "id": str(tool.id),
                    "tool_name": tool.tool_name,
                    "query": tool.query,
                    "output": tool.output,
                    "execution_time": tool.execution_time,
                    "created_at": tool.created_at.isoformat()
                }
                for tool in tools
            ]
        
        result.append(intervention_data)
    
    return {
        "simulation_id": sim_id,
        "interventions": result,
        "total": len(result)
    }


@router.get("/{sim_id}/interventions/{intervention_id}/tools")
async def get_intervention_tools(
    sim_id: str,
    intervention_id: str,
    agent_name: str = None,  # Filter by specific agent
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get tool usage details for a specific intervention.
    
    Query Parameters:
    - agent_name: Filter tool usage by specific agent (optional)
    """
    from app.models import Intervention, ToolUsage
    
    try:
        run_uuid = UUID(sim_id)
        intervention_uuid = UUID(intervention_id)
    except ValueError:
        raise HTTPException(400, "Invalid simulation or intervention ID")
    
    # Check if user owns this run
    run = db.get(Run, run_uuid)
    if not run or run.user_id != current_user.id:
        raise HTTPException(404, "Simulation not found")
    
    # Check if intervention exists
    intervention = db.get(Intervention, intervention_uuid)
    if not intervention or intervention.run_id != run_uuid:
        raise HTTPException(404, "Intervention not found")
    
    # Get tool usages
    tools_stmt = select(ToolUsage).where(ToolUsage.intervention_id == intervention_uuid)
    
    if agent_name:
        tools_stmt = tools_stmt.where(ToolUsage.agent_name == agent_name)
    
    tools = db.exec(tools_stmt).all()
    
    return {
        "simulation_id": sim_id,
        "intervention_id": intervention_id,
        "tools": [
            {
                "id": str(tool.id),
                "agent_name": tool.agent_name,
                "tool_name": tool.tool_name,
                "query": tool.query,
                "output": tool.output,
                "execution_time": tool.execution_time,
                "raw_results": tool.raw_results,
                "created_at": tool.created_at.isoformat()
            }
            for tool in tools
        ],
        "total": len(tools)
    }
