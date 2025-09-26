from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
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


@dataclass
class Simulation:
    # Inputs (same defaults/shape as notebook expectations)
    topic: str
    agent_configs: List[InternalAgentConfig]  # Updated to use internal agent configs
    embedder: Any                        # SentenceTransformer w/ PEFT, passed in
    lm: dspy.LM                       # dspy LM (configured outside, used as fallback)
    api_base: str                     # OpenRouter API base
    api_key: str                      # OpenRouter API key
    max_iters: int = 21
    # Moderator config per notebook
    bias: Optional[List[float]] = None  # defaults to [1,1,...]
    stance: str = ""

    # Runtime state (mirroring notebook variables)
    iters: int = 0
    intervenciones: List[str] = field(default_factory=list)  # speakers per iteration
    engagement_log: List[List[str]] = field(default_factory=list)  # engaged agent names per iter
    opiniones: List[str] = field(default_factory=list)  # all opinions in order

    # Internal handles (not in notebook but minimal to orchestrate)
    _agents: List[PoliAgent] = field(default_factory=list, init=False)
    _mod: Optional[Moderator] = field(default=None, init=False)
    _locutor: Optional[PoliAgent] = field(default=None, init=False)
    _started: bool = field(default=False, init=False)
    _finished: bool = field(default=False, init=False)

    def _build_agents(self) -> List[PoliAgent]:
        objs: List[PoliAgent] = []
        for idx, agent_config in enumerate(self.agent_configs):
            # Create agent-specific model if specified
            agent_model = None
            if agent_config.model_id:
                try:
                    agent_model = create_agent_lm(
                        model_id=agent_config.model_id,
                        api_base=self.api_base,
                        api_key=self.api_key
                    )
                except ValueError:
                    # If model is invalid, fall back to default
                    agent_model = create_agent_lm(
                        model_id=DEFAULT_MODEL,
                        api_base=self.api_base,
                        api_key=self.api_key
                    )
            
            # 0-based ids so Moderator indexing works: 0..N-1
            a = PoliAgent(
                agent_id=idx,
                name=agent_config.name,
                background=agent_config.profile,
                topic=self.topic,
                embedder=self.embedder,
                model=agent_model
            )
            objs.append(a)
        return objs

    def start(self) -> None:
        if self._started:
            return
        # Build agents and moderator exactly like the notebook
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
        )
        self._locutor = self._mod.opening_commenter()

        self._started = True
        self._finished = False
        self.iters = 0
        self.intervenciones.clear()
        self.engagement_log.clear()
        self.opiniones.clear()

    def step(self) -> Dict[str, Any]:
        """
        Advances one notebook iteration.
        Returns turn payload similar to what you'd print/log in the notebook.
        """
        if not self._started:
            self.start()
        if self._finished:
            return {"finished": True}

        self._mod.reset_requests()
        opinion = self._locutor.talk()

        # record like the notebook does
        self.opiniones.append(opinion)
        self.intervenciones.append(self._locutor.name)

        comprometidos: List[str] = []
        for agent in self._agents:
            if agent.name != self._locutor.name:
                reaction = agent.think(opinion)
                if reaction:
                    self._mod.add_request(agent)
                    comprometidos.append(agent.name)

        self.engagement_log.append(comprometidos)
        self._mod.update()
        next_locutor = self._mod.select_next_speaker()

        # stop conditions (same order/logic as notebook)
        stopped_reason: Optional[str] = None
        if next_locutor is None:
            stopped_reason = "no_one_wants_to_continue"
        elif self._mod.diversity_too_high(
            self._agents,
            min_iters=len(self._agents) - 1,
            current_iter=self.iters,
            threshold=0.6
        ):
            stopped_reason = "comments_too_similar"
        elif self.iters + 1 >= self.max_iters:
            stopped_reason = "max_iters_reached"

        if stopped_reason is not None:
            self._finished = True
        else:
            self._locutor = next_locutor
            self.iters += 1

        return {
            "iteration": self.iters,
            "speaker": self.intervenciones[-1],
            "opinion": opinion,
            "engaged": comprometidos,
            "finished": self._finished,
            "stopped_reason": stopped_reason,
        }

    def run(self) -> None:
        """
        Runs until the notebook's stop conditions trigger.
        """
        if not self._started:
            self.start()
        while not self._finished:
            _ = self.step()

    def vote(self) -> Tuple[int, int, List[str]]:
        """
        Executes the voting phase like the notebook.
        Returns (Yea, Nay, reasons[]).
        """
        Yea = 0
        Nay = 0
        razones: List[str] = []
        for agent in self._agents:
            voto, razon = agent.vote()
            razones.append(f"{agent.name}: {razon}")
            if voto:
                Yea += 1
            else:
                Nay += 1
        return Yea, Nay, razones

    # Minimal snapshot for API usage (no behavior change)
    def snapshot(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "max_iters": self.max_iters,
            "iters": self.iters,
            "finished": self._finished,
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "background": agent.background,
                    "last_opinion": agent.last_opinion,
                    "memory": agent.memory.to_list()
                }
                for agent in self._agents
            ],
            "intervenciones": self.intervenciones,
            "engagement_log": self.engagement_log,
            "opiniones": self.opiniones,
            "moderator": {
                "interventions": self._mod.interventions if self._mod else [],
                "hands_raised": self._mod.hands_raised if self._mod else [],
                "weight": getattr(self._mod, "weights", []),
                "bias": self.bias,
            },
        }