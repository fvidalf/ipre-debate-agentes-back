import os
import asyncio
from typing import Dict, Tuple, List
from uuid import UUID
from datetime import datetime

from sqlmodel import Session
import dspy

from app.classes.simulation import Simulation, InternalAgentConfig
from app.classes.nlp import create_sentence_embedder
from app.models import Run, RunEvent
from app.api.schemas import CreateSimRequest


class SimulationService:
    """
    Application service for managing simulation lifecycle.
    
    Responsibilities:
    - Orchestrate simulation execution in background
    - Handle database persistence of simulation events
    - Manage simulation status and error handling
    - Bridge between API layer and domain logic (Simulation class)
    """
    
    def __init__(self, lm, engine):
        self._lm = lm
        self._api_base = "https://openrouter.ai/api/v1"
        self._api_key = os.getenv("OPENROUTER_API_KEY")
        self._engine = engine

    async def run_simulation_background(self, run_id: UUID, config: CreateSimRequest):
        """Run simulation in background, storing events in database"""
        try:
            print(f"Starting simulation {run_id}")
            
            # Update status to running (use short-lived session)
            with Session(self._engine) as db:
                run = db.get(Run, run_id)
                run.status = "running"
                run.started_at = datetime.utcnow()
                db.add(run)
                db.commit()
            
            # Convert schema objects to internal AgentConfig objects
            agent_configs = [
                InternalAgentConfig(
                    name=agent.name,
                    profile=agent.profile,
                    model_id=agent.model_id
                )
                for agent in config.agents
            ]
            
            # Create embedder based on configuration
            embedder_config = config.embedding_config or {}
            sbert = create_sentence_embedder(
                model_type=config.embedding_model, 
                **embedder_config
            )
            
            # Create simulation
            simulation = Simulation(
                topic=config.topic,
                agent_configs=agent_configs,
                embedder=sbert,
                lm=self._lm,
                api_base=self._api_base,
                api_key=self._api_key,
                max_iters=config.max_iters,
                bias=config.bias,
                stance=config.stance,
            )
            
            # Start simulation
            simulation.start()
            print(f"Simulation {run_id} initialized with {len(agent_configs)} agents")
            
            # Run step by step, storing each event
            iteration_counter = 0
            while not simulation._finished:
                # Check if user requested stop (use short-lived session)
                with Session(self._engine) as db:
                    run = db.get(Run, run_id)
                    if run.status == "stopped":
                        simulation._finished = True
                        break
                    
                step_result = simulation.step()
                iteration_counter += 1  # Our own counter to ensure uniqueness
                
                print(f"Simulation {run_id} - Step {iteration_counter}: {step_result['speaker']}")
                
                # Store event in database (use short-lived session)
                with Session(self._engine) as db:
                    event = RunEvent(
                        run_id=run_id,
                        iteration=iteration_counter,
                        speaker=step_result["speaker"],
                        opinion=step_result["opinion"],
                        engaged=step_result["engaged"],
                        finished=step_result["finished"],
                        stopped_reason=step_result["stopped_reason"]
                    )
                    
                    try:
                        db.add(event)
                        
                        # Update run progress
                        run = db.get(Run, run_id)
                        run.iters = iteration_counter
                        run.finished = step_result["finished"]
                        run.stopped_reason = step_result["stopped_reason"]
                        db.add(run)
                        
                        db.commit()
                    except Exception as db_err:
                        print(f"Database error in simulation {run_id}: {db_err}")
                        db.rollback()
                        # Continue with the simulation even if one event fails
                
                if step_result["finished"]:
                    break
                
                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)
            
            # Mark as finished (use short-lived session)
            with Session(self._engine) as db:
                run = db.get(Run, run_id)
                run.status = "finished" if not run.stopped_reason else "stopped"
                run.finished_at = datetime.utcnow()
                db.add(run)
                db.commit()
            
            print(f"Simulation {run_id} completed")
            
            # Cleanup
            del simulation
            del sbert
            
        except Exception as e:
            print(f"Error in simulation {run_id}: {str(e)}")
            # Mark as failed with proper error handling (use short-lived session)
            try:
                with Session(self._engine) as db:
                    run = db.get(Run, run_id)
                    if run:
                        run.status = "failed"
                        run.stopped_reason = str(e)
                        run.finished_at = datetime.utcnow()
                        db.add(run)
                        db.commit()
            except Exception as db_error:
                print(f"Failed to update failed simulation status: {db_error}")

    async def trigger_voting(self, run_id: UUID, db: Session) -> Tuple[int, int, List[str]]:
        """Trigger voting for a completed simulation and store individual votes"""
        from app.models import Summary, ConfigVersion, ConfigAgent
        
        # Get run info
        run = db.get(Run, run_id)
        if not run:
            raise ValueError("Run not found")
        
        if not run.finished:
            raise ValueError("Run must be finished before voting")
        
        # Get config version to recreate simulation setup
        config_version = db.get(ConfigVersion, run.config_version_id)
        if not config_version:
            raise ValueError("Config version not found")
        
        version_agents = config_version.agents
        
        # Recreate simulation from stored events
        from sqlmodel import select
        events_stmt = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.iteration)
        )
        events = db.exec(events_stmt).all()
        
        # Create simulation instance
        embedder = create_sentence_embedder(
            model_type=config_version.parameters.get("embedding_model", "onnx_minilm")
        )
        
        # Convert version agents to internal configs
        agent_configs = [
            InternalAgentConfig(
                name=agent_data.get("name", f"Agent {i}"),
                profile=agent_data.get("profile", ""),
                model_id=agent_data.get("model_id")
            )
            for i, agent_data in enumerate(version_agents)
        ]
        
        simulation = Simulation(
            topic=config_version.parameters.get("topic", ""),
            agent_configs=agent_configs,
            embedder=embedder,
            lm=self._lm,
            api_base=self._api_base,
            api_key=self._api_key,
            max_iters=config_version.parameters.get("max_iters", 21),
            bias=config_version.parameters.get("bias", [1] * len(agent_configs)),
            stance=config_version.parameters.get("stance", "")
        )
        
        # Initialize simulation and replay events to restore state
        simulation.start()
        
        # Replay events to restore agent memory and state
        for event in events:
            # Find the agent that spoke
            speaking_agent = None
            for agent in simulation._agents:
                if agent.name == event.speaker:
                    speaking_agent = agent
                    break
            
            if speaking_agent:
                # Set the opinion (this would be the result of the forward() call)
                speaking_agent.last_opinion = event.opinion
                
                # Have other agents process this opinion (update their memory)
                for agent in simulation._agents:
                    if agent.name != event.speaker and agent.name in event.engaged:
                        agent.memory.enqueue(event.opinion)
        
        # Now trigger voting
        yea, nay, reasons_list = simulation.vote()
        
        # Create individual votes with agent position/index
        individual_votes = []
        for i, agent in enumerate(simulation._agents):
            vote, reasoning = agent.vote()
            individual_votes.append({
                "agent_position": i,
                "agent_data": version_agents[i],  # Store the full agent data from config version
                "vote": vote,
                "reasoning": reasoning
            })
        
        # Store in Summary model
        summary = Summary(
            run_id=run_id,
            yea=yea,
            nay=nay,
            reasons=reasons_list,  # Keep for backward compatibility
            individual_votes=individual_votes
        )
        
        db.add(summary)
        db.commit()
        
        return yea, nay, reasons_list
