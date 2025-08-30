from typing import List, Tuple, Optional
import dspy
import numpy as np
from .memory import FixedMemory
from .nlp import StanceAwareSBERT


class PoliAgent(dspy.Module):
    """
    Debate agent with:
      - background persona
      - short-term memory
      - LM heads: respond (opinion generation) and voting (bool + hidden reasoning)
      - individual model for customized responses
    """
    def __init__(
        self,
        agent_id: int,
        name: str,
        background: str,
        topic: str,
        sbert: StanceAwareSBERT,
        model: Optional[dspy.LM] = None,
        memory_size: int = 3,
        respond_signature: str = "topic, context, your_background -> opinion",
        vote_signature: str = "topic, context, opinion -> vote:bool"
    ):
        super().__init__()
        self.id = agent_id
        self.name = name
        self.topic = topic
        self.background = background
        self.memory = FixedMemory(memory_size)
        self._sbert = sbert
        self.model = model  # Individual model for this agent
        
        # Create predictor modules with agent-specific model if provided
        if model:
            with dspy.context(lm=model):
                self.respond = dspy.Predict(respond_signature)
                self.voting = dspy.ChainOfThought(vote_signature)
        else:
            # Fallback to global configuration
            self.respond = dspy.Predict(respond_signature)
            self.voting = dspy.ChainOfThought(vote_signature)
            
        self.last_opinion: str = ""

    def talk(self) -> str:
        context = self.memory.to_text()
        
        # Use agent-specific model if available
        if self.model:
            with dspy.context(lm=self.model):
                out = self.respond(topic=self.topic, context=context, your_background=self.background)
        else:
            out = self.respond(topic=self.topic, context=context, your_background=self.background)
            
        # dspy returns a typed object with fields based on the signature
        self.last_opinion = out.opinion
        return self.last_opinion
    
    def evaluate(self, other_opinion: str, low: float = 0.3, high: float = 0.75) -> bool:
        similarity_score = self._sbert.text_similarity_score(self.last_opinion, other_opinion)
        if similarity_score < low or similarity_score > high:
            return True
        return False
    
    def think(self, other_opinion: str) -> bool:
        wanna_talk = self.evaluate(other_opinion)
        if wanna_talk:
            self.memory.enqueue(other_opinion)
        return wanna_talk

    def vote(self):
        context = self.memory.to_text()
        
        # Use agent-specific model if available
        if self.model:
            with dspy.context(lm=self.model):
                vote = self.voting(topic=self.topic, context=context, opinion=self.last_opinion)
        else:
            vote = self.voting(topic=self.topic, context=context, opinion=self.last_opinion)
            
        return vote.vote, vote.reasoning
