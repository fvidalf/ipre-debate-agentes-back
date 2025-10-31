from typing import List, Optional
import random
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .agents import PoliAgent


class Moderator:
    """
    Manages turn-taking using weighted sampling over agents who 'raised a hand'.
    Combines:
      - agent 'desire_to_speak' weights (short-term eagerness)
      - fairness weights (long-term intervention balance)
    """

    def __init__(
        self,
        agents: List[PoliAgent],
        stance: str = "",
        bias: Optional[List[float]] = None,
        max_interventions_per_agent: Optional[int] = None,
    ):
        self.agents = agents
        self._requests: List[PoliAgent] = []
        self.interventions = [0] * len(agents)
        self.hands_raised = [0] * len(agents)

        # Base weights (aligned 1:1 with agents)
        self.weights: List[float] = [1.0] * len(agents)
        self.bias = bias if bias is not None else [1.0] * len(agents)
        self.stance = stance
        self.max_interventions_per_agent = max_interventions_per_agent

        # Temporary desire weights during current round
        self._desire_weights: List[float] = []

    # -----------------------------------------------------------------------
    # Turn-taking management
    # -----------------------------------------------------------------------

    def opening_commenter(self) -> PoliAgent:
        """Select an opening commenter uniformly at random."""
        return random.choice(self.agents)

    def add_request(self, agent: PoliAgent, weight: float = 1.0) -> None:
        """
        Register that an agent wants to speak.
        The `weight` value (from agent.propose) represents how eager they are to join.
        """
        self._requests.append(agent)
        self._desire_weights.append(weight)

    def reset_requests(self) -> None:
        """Clear raised hands and temporary weights between iterations."""
        self._requests = []
        self._desire_weights = []

    # -----------------------------------------------------------------------
    # Fairness + weighting logic
    # -----------------------------------------------------------------------

    def update(self) -> None:
        """
        Compute final sampling weights for next-speaker selection.
        Combines short-term 'desire_to_speak' with long-term fairness.
        """
        if not self._requests:
            self.weights = []
            return

        requested_ids = [agent.id for agent in self._requests]

        # Track engagement stats
        for agent in self._requests:
            self.hands_raised[agent.id] += 1

        inter = np.array(self.interventions)[requested_ids]
        hands = np.array(self.hands_raised)[requested_ids]
        bias_array = np.array(self.bias, dtype=float)
        bias_array[bias_array == 0] = 1.0  # Prevent division by zero
        bias = (1 / bias_array)[requested_ids]

        # Base fairness score
        exponents = hands - bias * inter
        exponents = np.clip(exponents, -500, 500)
        fairness_weights = np.exp(exponents)

        # Combine fairness with short-term desire
        desire = np.array(self._desire_weights or [1.0] * len(requested_ids), dtype=float)
        desire = np.clip(desire, 0.01, 1.0)

        combined = fairness_weights * desire

        # Normalize safely
        if not np.any(np.isfinite(combined)) or combined.sum() <= 0:
            combined = np.ones_like(combined)

        combined = combined / combined.sum()
        self.weights = combined.tolist()

    # -----------------------------------------------------------------------
    # Speaker selection
    # -----------------------------------------------------------------------

    def select_next_speaker(self) -> Optional[PoliAgent]:
        """Choose next speaker using weighted sampling among requesters."""
        if not self._requests:
            return None

        if not self.weights or len(self.weights) != len(self._requests):
            chosen = random.choice(self._requests)
        else:
            weights_array = np.array(self.weights)
            if not np.all(np.isfinite(weights_array)) or np.sum(weights_array) <= 0:
                chosen = random.choice(self._requests)
            else:
                chosen = random.choices(self._requests, weights=self.weights, k=1)[0]

        # Track who spoke for fairness in next iterations
        self.interventions[chosen.id] += 1
        return chosen

    # -----------------------------------------------------------------------
    # Consensus/diversity tracking
    # -----------------------------------------------------------------------

    def diversity_too_high(
        self,
        agents: List[PoliAgent],
        min_iters: int,
        current_iter: int,
        threshold: float = 0.75,
    ) -> bool:
        """
        Detect when opinions are converging too much (to stop simulation).
        """
        from app.services.embedding_service import get_embedding_service
        
        last_opinions = [a.last_opinion for a in agents if a.last_opinion]
        if len(last_opinions) < 2:
            return False

        embedding_service = get_embedding_service()
        embeddings = embedding_service.encode(last_opinions)
        similarity_matrix = cosine_similarity(embeddings)
        n = len(last_opinions)
        total = similarity_matrix.sum() - np.trace(similarity_matrix)
        num_pairs = n * (n - 1)
        avg = float(total / (num_pairs + 1e-12))

        return avg > threshold and current_iter >= min_iters
