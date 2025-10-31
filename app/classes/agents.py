from typing import Optional, Tuple, Dict, Any
import dspy
import numpy as np
from .memory import FixedMemory

# ---------------------------------------------------------------------------
#  DEBUG: Commented out monkey patch for debugging
# ---------------------------------------------------------------------------

# COMMENTED OUT: Debug logging for API calls
# Store original methods
# _original_lm_call = dspy.LM.__call__
# _original_lm_forward = dspy.LM.forward

# def debug_lm_call(self, *args, **kwargs):
#     """Debug wrapper to see what parameters are actually sent to the API"""
#     print(f"🔥 FINAL LM.__call__ to {getattr(self, 'model', 'UNKNOWN')} with kwargs:", kwargs)
#     return _original_lm_call(self, *args, **kwargs)

# def debug_lm_forward(self, *args, **kwargs):
#     """Debug wrapper to see what parameters are actually sent to the API"""
#     print(f"🔥 FINAL LM.forward to {getattr(self, 'model', 'UNKNOWN')} with kwargs:", kwargs)
#     print(f"🔥 LM instance kwargs: {getattr(self, 'kwargs', {})}")
#     return _original_lm_forward(self, *args, **kwargs)

# # Apply monkey patches
# dspy.LM.__call__ = debug_lm_call
# dspy.LM.forward = debug_lm_forward


# ---------------------------------------------------------------------------
#  DSPy Signatures
# ---------------------------------------------------------------------------

class AgentIntentSignature(dspy.Signature):
    """Lightweight predictor: Based on the last opinion, should the agent respond at all?"""
    topic: str = dspy.InputField(desc="The debate topic or current question.")
    context: str = dspy.InputField(desc="Recent discussion context (short).")
    persona_description: str = dspy.InputField(desc="Agent's background and worldview.")
    last_speaker: str = dspy.InputField(desc="Name of the previous speaker.")
    last_opinion: str = dspy.InputField(desc="What the last speaker said.")
    interventions_remaining: str = dspy.InputField(desc="Number of interventions left ('unlimited' or a number like '3 remaining').")

    desire_to_speak: float = dspy.OutputField(desc="How strongly this agent wants to respond (0–1).")
    raise_hand: bool = dspy.OutputField(desc="Whether the agent raises their hand to speak.")


class AgentRespondSignature(dspy.Signature):
    """Generate and self-assess a debate response for a political or philosophical simulation."""

    # ---------- INPUTS ----------
    topic: str = dspy.InputField(
        desc="The current debate topic or question being discussed."
    )
    context: str = dspy.InputField(
        desc="Recent conversation history and relevant context."
    )
    persona_description: str = dspy.InputField(
        desc="Agent's personality, ideology, and worldview."
    )
    last_speaker: str = dspy.InputField(
        desc="Name of the last speaker who contributed to the discussion."
    )
    last_opinion: str = dspy.InputField(
        desc="What the last speaker said or argued."
    )
    interventions_remaining: str = dspy.InputField(
        desc="Number of interventions left ('unlimited', 'last intervention', or a number like '3 remaining')."
    )

    # ---------- OUTPUTS ----------
    # Targeted engagement fields
    counter_target: str = dspy.OutputField(
        desc="Quote or paraphrase the exact point addressed from last_opinion."
    )
    counter_type: str = dspy.OutputField(
        desc="Type of engagement: rebuttal | support | reframe | extend."
    )

    # Main text
    response: str = dspy.OutputField(
        desc="The agent's written, persona-consistent response for this turn that uses counter_target."
    )
    tone: str = dspy.OutputField(
        desc="Emotional tone or rhetorical style (analytical, passionate, confrontational, etc.)."
    )
    references_used: str = dspy.OutputField(
        desc="Sources and examples used in the response. Prefer to use tools to gather references."
    )
    stance_strength: str = dspy.OutputField(
        desc="Qualitative measure of how strongly the agent expresses their view."
    )

    # Self-assessment fields (for proposal phase)
    novelty_estimate: str = dspy.OutputField(
        desc="Model’s self-estimate (0-1) of how novel this response is versus the agent’s last message."
    )
    persona_fit_estimate: str = dspy.OutputField(
        desc="Model’s self-estimate (0-1) of how well this response fits the agent’s persona."
    )
    desire_to_speak: str = dspy.OutputField(
        desc="Model’s self-assessed desire (0-1) to speak this turn."
    )
    raise_hand: bool = dspy.OutputField(
        desc="True if the agent would raise their hand to speak this turn."
    )

class AgentVoteSignature(dspy.Signature):
    """Evaluate the debate and decide how to vote on the topic."""

    topic: str = dspy.InputField(desc="Debate topic under consideration.")
    context: str = dspy.InputField(desc="Summary of the discussion so far.")
    persona_description: str = dspy.InputField(desc="Agent's personality, values, and ideology.")
    opinion: str = dspy.InputField(desc="Agent's most recent expressed opinion.")

    vote: bool = dspy.OutputField(desc="True if the agent supports the motion, False if they oppose it.")
    reasoning: str = dspy.OutputField(desc="Detailed reasoning for the vote, aligned with the agent's personality and argument history.")
    confidence: str = dspy.OutputField(desc="Agent's confidence level in their decision (low/medium/high).")


class AgentSummarySignature(dspy.Signature):
    """Summarize recent discussion for memory compression and continuity."""
    recent_context: str = dspy.InputField(desc="The most recent lines of debate or discussion.")
    persona_description: str = dspy.InputField(desc="Agent's personality for consistent summarization style.")
    summary: str = dspy.OutputField(desc="A short summary of the discussion suitable for adding to memory.")


class AgentCritiqueSignature(dspy.Signature):
    """Critique and lightly improve a response for clarity, persona-fit, and tone consistency."""
    persona_description: str = dspy.InputField(desc="Agent's background and worldview.")
    response: str = dspy.InputField(desc="The drafted response to review.")
    corrected_response: str = dspy.OutputField(desc="Refined version preserving intent but improving fit and tone.")


# ---------------------------------------------------------------------------
#  PoliAgent Implementation
# ---------------------------------------------------------------------------

class PoliAgent(dspy.Module):
    """
    Debate agent with lightweight 'propose' stage and full ReAct 'talk' stage.
    """

    def __init__(
        self,
        agent_id: int,
        name: str,
        background: str,
        topic: str,
        model: Optional[dspy.LM] = None,
        memory_size: int = 3,
        react_max_iters: int = 6,
        refine_N: int = 2,
        refine_threshold: float = 0.05,
        max_interventions: Optional[int] = None,
        tools: Optional[list[callable]] = None,
    ):
        super().__init__()
        self.id = agent_id
        self.name = name
        self.topic = topic
        self.persona_description = background
        self.memory = FixedMemory(memory_size)
        self.model = model
        self.last_opinion: str = ""
        
        # Intervention tracking
        self.max_interventions = max_interventions
        self.interventions_used: int = 0

        # Tool setup
        self.last_tool_usage = None  # Initialize tool usage tracking
        self.tools = tools or []


        if model:
            self.intent_module = dspy.Predict(AgentIntentSignature)
            self.respond_module = dspy.ReAct(
                signature=AgentRespondSignature, 
                tools=self.tools, 
                max_iters=react_max_iters
            )
            self.vote_module = dspy.ChainOfThought(AgentVoteSignature)
            self.summarize = dspy.Predict(AgentSummarySignature)
            self.critique = dspy.Predict(AgentCritiqueSignature)
            
            # ORIGINAL: Try to set the LM on ReAct module (didn't work but that's the original approach)
            self.respond_module.lm = model
            
            # COMMENTED OUT: Debug logging for ReAct LM verification
            # print(f"DEBUG: Agent {self.name} ReAct LM: {self.respond_module.lm}")
            # print(f"DEBUG: Agent {self.name} ReAct LM kwargs: {getattr(self.respond_module.lm, 'kwargs', 'NOT_FOUND')}")
            
        else:
            # Fallback to default behavior when no model provided
            self.intent_module = dspy.Predict(AgentIntentSignature)
            self.respond_module = dspy.ReAct(
                signature=AgentRespondSignature, tools=tools, max_iters=6
            )
            self.vote_module = dspy.ChainOfThought(AgentVoteSignature)
            self.summarize = dspy.Predict(AgentSummarySignature)
            self.critique = dspy.Predict(AgentCritiqueSignature)
        
        # ---------------- Refiner ----------------
        def _reward_novelty_persona(inputs: Dict[str, Any], outputs: Dict[str, Any]) -> float:
            from app.services.embedding_service import get_embedding_service
            
            embedding_service = get_embedding_service()
            draft = getattr(outputs, "response", "") or ""
            prev = self.last_opinion or ""
            persona = inputs.get("persona_description", "") or ""
            novelty = 1.0 - float(embedding_service.text_similarity_score(draft, prev))
            persona_fit = float(embedding_service.text_similarity_score(draft, persona))
            return 0.6 * novelty + 0.4 * persona_fit

        self._use_refiner = refine_N and refine_N > 0
        if self._use_refiner:
            self.refine_response = dspy.Refine(
                self.respond_module,
                N=refine_N,
                reward_fn=_reward_novelty_persona,
                threshold=refine_threshold,
            )

    # -----------------------------------------------------------------------
    # Intervention Management
    # -----------------------------------------------------------------------
    
    def can_intervene(self) -> bool:
        """Check if agent can still intervene."""
        if self.max_interventions is None:
            return True
        return self.interventions_used < self.max_interventions
    
    def _get_intervention_context(self) -> str:
        """Get formatted string describing intervention status for the model."""
        if self.max_interventions is None:
            return "no limit"
        
        remaining = self.max_interventions - self.interventions_used
        if remaining == 1:
            return "last intervention"
        else:
            return f"{remaining} remaining"

    # -----------------------------------------------------------------------
    # Thinking Phase (cheap)
    # -----------------------------------------------------------------------

    def propose(self, last_speaker: str, last_opinion: str) -> Dict[str, Any]:
        """Quickly predict whether the agent wants to respond (low-cost stage)."""
        # Check if agent can even intervene
        if not self.can_intervene():
            return {
                "raise_hand": False,
                "desire_to_speak": 0.0,
                "draft": "",
                "meta": {"blocked_by_intervention_limit": True},
            }
        
        short_context = self.memory.to_text(limit=2)  # lightweight context

        # COMMENTED OUT: Debug logging for model information
        # print(f"DEBUG: Agent {self.name} checking intent to speak")
        # print(f"  - Agent model: {self.model}")
        # if self.model:
        #     print(f"  - Model ID: {getattr(self.model, 'model', 'NOT_FOUND')}")
        #     print(f"  - Max tokens: {getattr(self.model, 'max_tokens', 'NOT_FOUND')}")

        # REVERTED: Back to original simple approach, no context managers
        out = self.intent_module(
            topic=self.topic,
            context=short_context,
            persona_description=self.persona_description,
            last_speaker=last_speaker,
            last_opinion=last_opinion,
            interventions_remaining=self._get_intervention_context(),
        )

        return {
            "raise_hand": bool(out.raise_hand),
            "desire_to_speak": float(out.desire_to_speak),
            "draft": "",
            "meta": {},
        }

    # -----------------------------------------------------------------------
    # Tool Usage & Metadata Extraction
    # -----------------------------------------------------------------------

    def _extract_tool_usage_from_prediction(self, prediction) -> Dict[str, Any]:
        """Extract tool usage and reasoning from DSPy Prediction object, preserving order"""
        if not hasattr(prediction, 'trajectory') or not prediction.trajectory:
            return None
        
        trajectory = prediction.trajectory
        
        # Create unified timeline preserving the original sequence
        timeline = []
        tools_used = []
        reasoning_steps = []
        
        # Find max step number to iterate through all steps
        max_step = -1
        for key in trajectory.keys():
            if '_' in key:
                try:
                    step_num = int(key.split('_')[-1])
                    max_step = max(max_step, step_num)
                except ValueError:
                    continue
        
        # Build timeline in correct order
        for i in range(max_step + 1):
            # Add thought if exists
            thought_key = f'thought_{i}'
            if thought_key in trajectory:
                thought = trajectory[thought_key]
                timeline.append({
                    'type': 'thought',
                    'step': i,
                    'content': thought
                })
                reasoning_steps.append(thought)
            
            # Add tool usage if exists (skip 'finish' tool)
            tool_name_key = f'tool_name_{i}'
            if tool_name_key in trajectory:
                tool_name = trajectory[tool_name_key]
                if tool_name != 'finish':
                    tool_args = trajectory.get(f'tool_args_{i}', {})
                    observation = trajectory.get(f'observation_{i}', '')
                    
                    tool_usage = {
                        'tool_name': tool_name,
                        'query': tool_args.get('query', ''),
                        'result': observation,
                        'step': i
                    }
                    
                    timeline.append({
                        'type': 'tool_call',
                        'step': i,
                        'tool_name': tool_name,
                        'query': tool_args.get('query', ''),
                        'result': observation
                    })
                    
                    tools_used.append(tool_usage)
        
        # Count available tools
        tools_available = len(getattr(self.respond_module, 'tools', []))
        
        return {
            'timeline': timeline,
            'tools_used': tools_used,
            'reasoning_steps': reasoning_steps,
            'has_trajectory': True,
            'tools_available': tools_available
        }

    def _extract_prediction_metadata(self, prediction) -> Dict[str, Any]:
        """Extract additional metadata from DSPy Prediction object"""
        metadata = {}
        
        # Extract useful prediction fields
        for field in ['counter_target', 'counter_type', 'tone', 'stance_strength', 
                      'novelty_estimate', 'persona_fit_estimate', 'references_used']:
            if hasattr(prediction, field):
                metadata[field] = getattr(prediction, field)
        
        return metadata if metadata else None

    # -----------------------------------------------------------------------
    # Speaking Phase (expensive, full ReAct)
    # -----------------------------------------------------------------------

    def talk(self, last_speaker: str = "", last_opinion: str = "") -> str:
        """Produce full ReAct-based debate response, refined and critiqued."""
        
        full_context = self.memory.to_text()  # full, untruncated for ReAct

        inputs = dict(
            topic=self.topic,
            context=full_context,
            persona_description=self.persona_description,
            last_speaker=last_speaker or "",
            last_opinion=last_opinion or "",
            interventions_remaining=self._get_intervention_context(),
        )

        # Step 1: Generate or refine response
        print(f"{self.name} is generating response")
        if self._use_refiner:
            out = self.refine_response(**inputs)
        else:
            out = self.respond_module(**inputs)

        draft = out.response
        
        # Extract tool usage and metadata from prediction
        self.last_tool_usage = self._extract_tool_usage_from_prediction(out)
        self.last_prediction_metadata = self._extract_prediction_metadata(out)

        # Step 2: Critique / persona consistency pass
        crit = self.critique(
            persona_description=self.persona_description,
            response=draft
        )
        final_response = crit.corrected_response or draft

        # Step 3: Memory update and intervention tracking
        self.memory.enqueue(final_response)
        self.last_opinion = final_response
        self.interventions_used += 1  # Track that this agent has spoken
                
        return final_response

    # -----------------------------------------------------------------------
    # Voting
    # -----------------------------------------------------------------------

    def vote(self) -> Tuple[bool, str, str]:
        """Vote on the motion based on discussion history."""
        context = self.memory.to_text(limit=4)
        
        result = self.vote_module(
            topic=self.topic,
            context=context,
            persona_description=self.persona_description,
            opinion=self.last_opinion,
        )
        return result.vote, result.reasoning, result.confidence

    # -----------------------------------------------------------------------
    # Memory Summarization
    # -----------------------------------------------------------------------

    def summarize_memory(self):
        """Compress memory every few iterations."""
        recent = self.memory.to_text()
        if not recent.strip():
            return
        out = self.summarize(
            recent_context=recent,
            persona_description=self.persona_description,
        )
        self.memory.clear()
        self.memory.enqueue(out.summary)

    # -----------------------------------------------------------------------
    # Utilities
    # -----------------------------------------------------------------------

    def __repr__(self):
        return f"<PoliAgent {self.name}>"
