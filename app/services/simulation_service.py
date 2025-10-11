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
                max_interventions_per_agent=config.max_interventions_per_agent,
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
                
                # Run the simulation step in a thread to avoid blocking the event loop
                loop = asyncio.get_event_loop()
                step_result = await loop.run_in_executor(None, simulation.step)
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
                
                # Yield control back to the event loop to handle other requests
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
        """Trigger voting for a completed simulation using stored RunEvents (efficient approach)"""
        from app.models import Summary, ConfigVersion
        from app.classes.agents import PoliAgent
        from app.classes.memory import FixedMemory
        from app.classes.model_config import create_agent_lm
        
        # Get run info
        run = db.get(Run, run_id)
        if not run:
            raise ValueError("Run not found")
        
        if not run.finished:
            raise ValueError("Run must be finished before voting")
        
        # Get config version 
        config_version = db.get(ConfigVersion, run.config_version_id)
        if not config_version:
            raise ValueError("Config version not found")
        
        version_agents = config_version.agents
        topic = config_version.parameters.get("topic", "")
        max_interventions_per_agent = config_version.parameters.get("max_interventions_per_agent")
        
        from sqlmodel import select
        events_stmt = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.iteration)
        )
        events = db.exec(events_stmt).all()
        
        embedder = create_sentence_embedder(
            model_type=config_version.parameters.get("embedding_model", "onnx_minilm")
        )
        
        voting_agents = []
        for i, agent_data in enumerate(version_agents):
            # Create agent-specific model if needed
            agent_model = None
            if agent_data.get("model_id"):
                try:
                    agent_model = create_agent_lm(
                        model_id=agent_data["model_id"],
                        api_base=self._api_base,
                        api_key=self._api_key
                    )
                except ValueError:
                    pass  # Use default LM
            
            agent = PoliAgent(
                agent_id=i,
                name=agent_data.get("name", f"Agent {i}"),
                background=agent_data.get("profile", ""),
                topic=topic,
                embedder=embedder,
                model=agent_model,
                memory_size=3,
                react_max_iters=6,
                refine_N=3,
                refine_threshold=0.05,
                max_interventions=max_interventions_per_agent
            )
            voting_agents.append(agent)
        
        # Reconstruct agent state from stored events (MUCH more efficient)
        agent_last_opinions = {}
        agent_memories = {agent.name: [] for agent in voting_agents}
        
        # Process events to build final state
        for event in events:
            # Track last opinion for each speaker
            agent_last_opinions[event.speaker] = event.opinion
            
            # Add opinions to memory of engaged agents
            for agent_name in event.engaged:
                if agent_name in agent_memories:
                    agent_memories[agent_name].append(event.opinion)
        
        # Apply reconstructed state to voting agents
        for agent in voting_agents:
            # Set last opinion (or keep generated initial opinion if they never spoke)
            if agent.name in agent_last_opinions:
                agent.last_opinion = agent_last_opinions[agent.name]
            
            # Rebuild memory from stored engagement history
            agent.memory = FixedMemory(3)  # Reset and rebuild
            for opinion in agent_memories[agent.name][-3:]:  # Only last 3 (memory limit)
                agent.memory.enqueue(opinion)
        
        # Now perform voting with reconstructed state
        yea = 0
        nay = 0
        reasons_list = []
        individual_votes = []
        
        for i, agent in enumerate(voting_agents):
            vote, reasoning, confidence = agent.vote()
            reasons_list.append(f"{agent.name}: {reasoning}")
            
            if vote:
                yea += 1
            else:
                nay += 1
                
            individual_votes.append({
                "agent_position": i,
                "agent_data": version_agents[i],
                "vote": vote,
                "reasoning": reasoning
            })
        
        # Store in Summary model
        summary = Summary(
            run_id=run_id,
            yea=yea,
            nay=nay,
            reasons=reasons_list,
            individual_votes=individual_votes
        )
        
        db.add(summary)
        db.commit()
        
        return yea, nay, reasons_list
