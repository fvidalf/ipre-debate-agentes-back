from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import dspy

from .agents import PoliAgent
from .moderator import Moderator
from .model_config import create_agent_lm, DEFAULT_MODEL


agents: List[PoliAgent] = []  # will be set by Simulation at start


@dataclass
class InternalAgentConfig:
    """Configuration for a single agent (internal use)"""
    name: str
    profile: str
    model_id: Optional[str] = None
    lm_config: Optional[Dict[str, Any]] = None  # Language model parameters


@dataclass
class Simulation:
    topic: str
    agent_configs: List[InternalAgentConfig]
    embedder: Any
    lm: dspy.LM
    api_base: str
    api_key: str
    max_iters: int = 21
    bias: Optional[List[float]] = None
    stance: str = ""
    max_interventions_per_agent: Optional[int] = None

    iters: int = 0
    intervenciones: List[str] = field(default_factory=list)
    engagement_log: List[List[str]] = field(default_factory=list)
    opiniones: List[str] = field(default_factory=list)
    agent_intervention_counts: Dict[str, int] = field(default_factory=dict, init=False)

    _agents: List[PoliAgent] = field(default_factory=list, init=False)
    _mod: Optional[Moderator] = field(default=None, init=False)
    _locutor: Optional[PoliAgent] = field(default=None, init=False)
    _started: bool = field(default=False, init=False)
    _finished: bool = field(default=False, init=False)

    # -----------------------------------------------------------------------
    # Initialization
    # -----------------------------------------------------------------------

    def _build_agents(self) -> List[PoliAgent]:
        objs: List[PoliAgent] = []
        for idx, agent_config in enumerate(self.agent_configs):
            agent_model = None
            
            # Always create a model instance if we have parameters or a specific model
            if agent_config.model_id or agent_config.lm_config:
                model_id = agent_config.model_id or DEFAULT_MODEL
                lm_params = agent_config.lm_config or {}
                
                try:
                    agent_model = create_agent_lm(
                        model_id=model_id,
                        api_base=self.api_base,
                        api_key=self.api_key,
                        **lm_params
                    )
                except ValueError:
                    # Fallback to default model with parameters
                    agent_model = create_agent_lm(
                        model_id=DEFAULT_MODEL,
                        api_base=self.api_base,
                        api_key=self.api_key,
                        **lm_params
                    )

            # Create agent with its individual LM - BACK TO ORIGINAL APPROACH
            # No context manager, just pass the model directly like before
            a = PoliAgent(
                agent_id=idx,
                name=agent_config.name,
                background=agent_config.profile,
                topic=self.topic,
                embedder=self.embedder,
                model=agent_model,
                max_interventions=self.max_interventions_per_agent,
            )
            objs.append(a)
        return objs

    def start(self) -> None:
        if self._started:
            return
        self._agents = self._build_agents()
        global agents
        agents = self._agents

        if self.bias is None:
            self.bias = [1] * len(self._agents)

        self._mod = Moderator(
            self._agents,
            embedder=self.embedder,
            stance=self.stance,
            bias=self.bias,
            max_interventions_per_agent=self.max_interventions_per_agent,
        )
        self._locutor = self._mod.opening_commenter()

        self._started = True
        self._finished = False
        self.iters = 0
        self.intervenciones.clear()
        self.engagement_log.clear()
        self.opiniones.clear()
        # Agent intervention counts are now handled by individual agents

    # -----------------------------------------------------------------------
    # Debate Step
    # -----------------------------------------------------------------------

    def step(self) -> Dict[str, Any]:
        """Advance one iteration of the debate."""
        if not self._started:
            self.start()
        if self._finished:
            return {"finished": True}

        self._mod.reset_requests()
        
        # Get context from previous speaker and opinion for continuity
        last_speaker = self.intervenciones[-1] if self.intervenciones else ""
        last_opinion = self.opiniones[-1] if self.opiniones else ""
        
        opinion = self._locutor.talk(last_speaker=last_speaker, last_opinion=last_opinion)  # full ReAct phase

        self.opiniones.append(opinion)
        self.intervenciones.append(self._locutor.name)

        comprometidos: List[str] = []
        proposals: Dict[str, Any] = {}

        # --- Check intervention limits first ---
        # Get all agents except the current speaker who can still intervene
        eligible_agents = [
            agent for agent in self._agents 
            if agent.name != self._locutor.name and agent.can_intervene()
        ]
        
        # Check if we should stop due to intervention limits BEFORE asking for proposals
        stopped_reason = None
        if (self.max_interventions_per_agent is not None and 
            len(eligible_agents) == 0):
            stopped_reason = "All agents have reached their maximum intervention limit"
        
        # Only proceed with proposals if we have eligible agents
        if not stopped_reason and len(eligible_agents) > 0:
            # --- Parallelized proposal stage ---
            with ThreadPoolExecutor(max_workers=len(eligible_agents)) as ex:
                futures = {
                    ex.submit(agent.propose, self._locutor.name, opinion): agent
                    for agent in eligible_agents
                }
                for f in as_completed(futures):
                    agent = futures[f]
                    try:
                        proposal = f.result()
                        proposals[agent.name] = proposal
                        if proposal.get("raise_hand"):
                            comprometidos.append(agent.name)
                            self._mod.add_request(agent, weight=proposal.get("desire_to_speak", 0.0))
                    except Exception as e:
                        print(f"[Simulation] Agent {agent.name} proposal error: {e}")

            self.engagement_log.append(comprometidos)
            self._mod.update()
            next_locutor = self._mod.select_next_speaker()

            # --- Additional stopping conditions ---
            if next_locutor is None:
                stopped_reason = "No agents want to continue the debate"
        else:
            # No eligible agents, so no one can engage
            self.engagement_log.append([])
            next_locutor = None

        # --- Other stopping conditions ---
        if not stopped_reason:
            if self._mod.diversity_too_high(
                self._agents,
                min_iters=len(self._agents) - 1,
                current_iter=self.iters,
                threshold=0.75,
            ):
                stopped_reason = "Agent opinions have converged too much"
            elif self.iters + 1 >= self.max_iters:
                stopped_reason = "Maximum iterations limit reached"

        if stopped_reason:
            self._finished = True
        else:
            self._locutor = next_locutor
            self.iters += 1

        # --- Periodic memory summarization ---
        if self.iters % 3 == 0:
            for a in self._agents:
                a.summarize_memory()

        return {
            "iteration": self.iters,
            "speaker": self.intervenciones[-1],
            "opinion": opinion,
            "engaged": comprometidos,
            "finished": self._finished,
            "stopped_reason": stopped_reason,
        }

    # -----------------------------------------------------------------------
    # Run and Vote
    # -----------------------------------------------------------------------

    def run(self) -> None:
        """Run the debate to completion."""
        if not self._started:
            self.start()
        while not self._finished:
            _ = self.step()

    def vote(self) -> Tuple[int, int, List[str]]:
        """Run final voting round."""
        Yea, Nay = 0, 0
        reasons: List[str] = []
        for agent in self._agents:
            vote, reasoning, conf = agent.vote()
            reasons.append(f"{agent.name}: {reasoning} (confidence: {conf})")
            if vote:
                Yea += 1
            else:
                Nay += 1
        return Yea, Nay, reasons

    # -----------------------------------------------------------------------
    # Snapshot
    # -----------------------------------------------------------------------

    def snapshot(self) -> Dict[str, Any]:
        """Export minimal state snapshot."""
        return {
            "topic": self.topic,
            "max_iters": self.max_iters,
            "max_interventions_per_agent": self.max_interventions_per_agent,
            "iters": self.iters,
            "finished": self._finished,
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "background": agent.persona_description,
                    "last_opinion": agent.last_opinion,
                    "memory": agent.memory.to_list(),
                    "intervention_count": agent.interventions_used,
                    "max_interventions": agent.max_interventions,
                    "can_intervene": agent.can_intervene(),
                }
                for agent in self._agents
            ],
            "intervenciones": self.intervenciones,
            "engagement_log": self.engagement_log,
            "opiniones": self.opiniones,
            "agent_intervention_counts": {agent.name: agent.interventions_used for agent in self._agents},  # For backwards compatibility
            "moderator": {
                "interventions": self._mod.interventions if self._mod else [],
                "hands_raised": self._mod.hands_raised if self._mod else [],
                "weight": getattr(self._mod, "weights", []),
                "bias": self.bias,
            },
        }
