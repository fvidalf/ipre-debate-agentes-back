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
                sbert=sbert,
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

    async def trigger_voting(self, run_id: UUID) -> Tuple[int, int, List[str]]:
        """Trigger voting for a completed simulation"""
        # This would need to recreate the simulation from stored events
        # For now, return placeholder - we can implement this later
        return 0, 0, ["Voting not yet implemented in new system"]
