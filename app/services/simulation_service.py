import os
import asyncio
from typing import Dict, Tuple, List
from uuid import UUID
from datetime import datetime
import numpy as np

from sqlmodel import Session
import dspy

from app.classes.simulation import Simulation, InternalAgentConfig
from app.models import Run, Intervention, ToolUsage, Embedding
from app.api.schemas import CreateSimRequest
from app.services.embedding_service import get_embedding_service


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

    def _extract_web_search_config(self, agent) -> Dict[str, any]:
        """Extract web search configuration from tool configuration"""
        if hasattr(agent, 'web_search_tools') and agent.web_search_tools:
            tools_config = agent.web_search_tools.dict()
            
            # Convert nested structure to flat config for tools.py
            config = {}
            for tool_name, tool_config in tools_config.items():
                if tool_config and tool_config.get('enabled', False):  # Only include enabled tools
                    config[tool_name] = tool_config
            
            print(f"   - Raw tools config: {tools_config}")
            print(f"   - Processed config: {config}")
            
            return config if config else None
        
        print(f"   - No web_search_tools found on agent")
        return None

    def _extract_recall_config(self, agent) -> Dict[str, any]:
        """Extract recall tools configuration from agent configuration"""
        if hasattr(agent, 'recall_tools') and agent.recall_tools:
            return agent.recall_tools
        
        print(f"   - No recall_tools found on agent")
        return None

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
            agent_configs = []
            for i, agent in enumerate(config.agents):
                # print(f"🔍 Agent {i} ({agent.name}) - Full object type: {type(agent)}")
                # print(f"🔍 Agent {i} - Available attributes: {[attr for attr in dir(agent) if not attr.startswith('_')]}")
                # print(f"🔍 Agent {i} - Raw agent object: {agent}")
                if hasattr(agent, 'web_search_tools'):
                    pass
                    # print(f"🔍 Agent {i} - web_search_tools type: {type(agent.web_search_tools)}")
                    # print(f"🔍 Agent {i} - web_search_tools value: {agent.web_search_tools}")
                web_search_config = self._extract_web_search_config(agent)
                recall_config = self._extract_recall_config(agent)
                
                agent_configs.append(InternalAgentConfig(
                    name=agent.name,
                    profile=agent.profile,
                    model_id=agent.model_id,
                    lm_config=agent.lm_config.dict() if agent.lm_config else None,
                    web_search_tools=web_search_config,
                    recall_tools=recall_config
                ))
            
            # Create simulation
            simulation = Simulation(
                topic=config.topic,
                agent_configs=agent_configs,
                lm=self._lm,
                api_base=self._api_base,
                api_key=self._api_key,
                run_id=run_id,
                db_engine=self._engine,
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
                
                # Extract tool usage from the current speaker
                tool_usage = None
                prediction_metadata = None
                try:
                    current_speaker = step_result["speaker"]
                    for agent in simulation._agents:
                        if agent.name == current_speaker:
                            tool_usage = getattr(agent, 'last_tool_usage', None)
                            base_metadata = getattr(agent, 'last_prediction_metadata', None) or {}
                            
                            # Add timeline to metadata if available
                            if tool_usage and tool_usage.get('timeline'):
                                base_metadata['timeline'] = tool_usage['timeline']
                            
                            prediction_metadata = base_metadata if base_metadata else None
                            break
                except Exception as e:
                    print(f"Warning: Could not extract tool usage for {step_result['speaker']}: {e}")

                print(f"Simulation {run_id} - Step {iteration_counter}: {step_result['speaker']}")

                # Store intervention and tool usage in database
                with Session(self._engine) as db:
                    # Create new Intervention with tool usage and reasoning data
                    intervention = Intervention(
                        run_id=run_id,
                        iteration=iteration_counter,
                        speaker=step_result["speaker"],
                        content=step_result["opinion"],  # "opinion" -> "content" 
                        engaged_agents=step_result["engaged"],
                        reasoning_steps=tool_usage.get("reasoning_steps", []) if tool_usage else None,
                        prediction_metadata=prediction_metadata,  # Store extra metadata as JSON
                        finished=step_result["finished"],
                        stopped_reason=step_result["stopped_reason"]
                    )
                    
                    try:
                        db.add(intervention)
                        db.flush()  # Get the intervention ID without committing
                        
                        # Store tool usage if present
                        tool_usage_records = []
                        if tool_usage and tool_usage.get("tools_used"):
                            for tool_data in tool_usage["tools_used"]:
                                tool_usage_record = ToolUsage(
                                    intervention_id=intervention.id,
                                    agent_name=step_result["speaker"],
                                    tool_name=tool_data.get("tool_name", "unknown"),
                                    query=tool_data.get("query", ""),
                                    output=str(tool_data.get("result", "")),
                                    raw_results=tool_data,  # Store full tool data for debugging
                                    execution_time=tool_data.get("execution_time")
                                )
                                db.add(tool_usage_record)
                                tool_usage_records.append(tool_usage_record)
                        
                        db.flush()  # Get tool usage IDs without committing
                        
                        # Generate and store embeddings
                        try:
                            embedding_service = get_embedding_service()
                            
                            # Collect all texts for batch embedding
                            texts_to_embed = []
                            embedding_metadata = []
                            
                            # 1. Add intervention text (PUBLIC)
                            texts_to_embed.append(intervention.content)
                            embedding_metadata.append({
                                'type': 'intervention',
                                'source_id': intervention.id,
                                'text_content': intervention.content,
                                'visibility': 'public',
                                'owner_agent': None,
                                'run_id': intervention.run_id
                            })
                            
                            # 2. Add tool usage texts (PRIVATE)
                            for tool_usage_record in tool_usage_records:
                                # Tool query
                                texts_to_embed.append(tool_usage_record.query)
                                embedding_metadata.append({
                                    'type': 'tool_query',
                                    'source_id': tool_usage_record.id,
                                    'text_content': tool_usage_record.query,
                                    'visibility': 'private',
                                    'owner_agent': tool_usage_record.agent_name,
                                    'run_id': intervention.run_id
                                })
                                
                                # Tool output
                                texts_to_embed.append(tool_usage_record.output)
                                embedding_metadata.append({
                                    'type': 'tool_output',
                                    'source_id': tool_usage_record.id,
                                    'text_content': tool_usage_record.output,
                                    'visibility': 'private',
                                    'owner_agent': tool_usage_record.agent_name,
                                    'run_id': intervention.run_id
                                })
                            
                            # Generate all embeddings in one batch
                            if texts_to_embed:
                                embeddings = embedding_service.encode(texts_to_embed)
                                
                                # Create embedding records with batch results
                                for i, metadata in enumerate(embedding_metadata):
                                    embedding_vector = embeddings[i].tolist() if embeddings.ndim > 1 else embeddings.tolist()
                                    
                                    db.add(Embedding(
                                        source_type=metadata['type'],
                                        source_id=metadata['source_id'],
                                        text_content=metadata['text_content'],
                                        visibility=metadata['visibility'],
                                        owner_agent=metadata['owner_agent'],
                                        run_id=metadata['run_id'],
                                        embedding=embedding_vector,
                                        embedding_model=embedding_service.model_name
                                    ))
                                
                        except Exception as embed_err:
                            print(f"Warning: Could not generate embeddings: {embed_err}")
                        
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
        """Trigger voting for a completed simulation using stored Interventions"""
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
        interventions_stmt = (
            select(Intervention)
            .where(Intervention.run_id == run_id)
            .order_by(Intervention.iteration)
        )
        interventions = db.exec(interventions_stmt).all()
        
        voting_agents = []
        for i, agent_data in enumerate(version_agents):
            # Create agent-specific model if needed
            agent_model = None
            if agent_data.get("model_id"):
                try:
                    lm_params = agent_data.get("lm_config", {}) or {}
                    agent_model = create_agent_lm(
                        model_id=agent_data["model_id"],
                        api_base=self._api_base,
                        api_key=self._api_key,
                        **lm_params
                    )
                except ValueError:
                    pass  # Use default LM
            
            agent = PoliAgent(
                agent_id=i,
                name=agent_data.get("name", f"Agent {i}"),
                background=agent_data.get("profile", ""),
                topic=topic,
                model=agent_model,
                memory_size=3,
                react_max_iters=6,
                refine_N=2,
                refine_threshold=0.05,
                max_interventions=max_interventions_per_agent
            )
            voting_agents.append(agent)
        
        # Reconstruct agent state from stored interventions
        agent_last_opinions = {}
        agent_memories = {agent.name: [] for agent in voting_agents}
        
        # Process interventions to build final state
        for intervention in interventions:
            # Track last opinion for each speaker
            agent_last_opinions[intervention.speaker] = intervention.content
            
            # Add opinions to memory of engaged agents
            for agent_name in intervention.engaged_agents:
                if agent_name in agent_memories:
                    agent_memories[agent_name].append(intervention.content)
        
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
