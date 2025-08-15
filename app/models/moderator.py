# app/models/moderator.py
from typing import List, Optional
import random
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .nlp import StanceAwareSBERT
from .agents import PoliAgent


class Moderator:
    """
    Manages turn-taking using weighted sampling over agents who 'raised a hand'.
    Tracks fairness via 'interventions' and 'hands_raised' counts.
    """
    def __init__(self, agents: List[PoliAgent], sbert: StanceAwareSBERT, stance: str = "", bias: Optional[List[float]] = None,):
        self._sbert = sbert
        self.agents = agents
        self._requests: List[PoliAgent] = []
        self.interventions = [0] * len(agents)
        self.hands_raised = [0] * len(agents)
        self.weights: List[float] = []
        self.stance = stance
        self.bias = bias if bias is not None else [1.0] * len(agents)

    def opening_commenter(self) -> PoliAgent:
        return random.choice(self.agents)

    def add_request(self, agent: PoliAgent) -> None:
        self._requests.append(agent)

    def reset_requests(self) -> None:
        self._requests = []

    def update(self) -> None:
        for agent in self._requests:
            self.hands_raised[agent.id] += 1

        requested_ids = [agent.id for agent in self._requests]
        inter = np.array(self.interventions)[requested_ids]
        hands = np.array(self.hands_raised)[requested_ids]
        bias = (1 / np.array(self.bias))[requested_ids]
        w = np.exp(hands - bias * inter)
        self.weights = (w / (w.sum() + 1e-12)).tolist()

    def select_next_speaker(self) -> Optional[PoliAgent]:
        if not self._requests:
            return None
        chosen = random.choices(self._requests, weights=self.weights, k=1)[0]
        self.interventions[chosen.id] += 1
        return chosen

    # ---- Diversity (consensus) check ----
    def diversity_too_high(self, agents: List[PoliAgent], min_iters: int, current_iter: int, threshold: float = 0.6) -> bool:
        last_opinions = [agent.last_opinion for agent in agents if agent.last_opinion]
        if len(last_opinions) < 2:
            return False

        embeddings = self._sbert.encode(last_opinions)
        similarity_matrix = cosine_similarity(embeddings)
        n = len(last_opinions)
        total = similarity_matrix.sum() - np.trace(similarity_matrix)
        num_pairs = n * (n - 1)
        avg = float(total / (num_pairs + 1e-12))
        return avg > threshold and current_iter >= min_iters
