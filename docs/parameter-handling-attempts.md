# Parameter Handling Implementation Attempts

**Date**: October 11, 2025  
**Status**: REVERTED - All changes rolled back to original naive approach  
**Reason**: Multiple provider and thread safety issues, complexity outweighed benefits

## Overview

This document details all the attempts made to implement proper parameter handling for debate agents, including custom LM configuration, provider fixes, and thread safety improvements. All changes were ultimately reverted due to persistent LiteLLM provider errors and DSPy threading constraints.

---

## 1. Model Configuration Changes (`app/classes/model_config.py`)

### 1.1 Parameter Validation Function
**What was added:**
```python
def validate_lm_config_for_model(model_id: str, lm_config: Dict) -> Dict:
    """Validate and filter LM config parameters based on model capabilities"""
    provider = model_id.split("/")[0] if "/" in model_id else "unknown"
    model_name = model_id.lower()
    
    # Check for OpenAI reasoning models (o-series and gpt-5)
    is_reasoning_model = (
        provider == "openai" and (
            "gpt-5" in model_name or 
            model_name.startswith("openai/o1") or 
            model_name.startswith("openai/o3") or
            model_name.startswith("openai/o4")
        )
    )
    
    if is_reasoning_model:
        return {
            "temperature": 1.0,
            "max_tokens": max(16000, lm_config.get("max_tokens", 16000) if lm_config else 16000),
            "provider": "openrouter"
        }
    
    # Provider-specific parameter filtering
    if provider == "google":
        filtered_params = {}
        for k, v in lm_config.items():
            if k == "temperature":
                filtered_params[k] = v
            elif k == "max_tokens":
                filtered_params["max_output_tokens"] = v
                filtered_params["max_tokens"] = v  # Explicit override
            elif k == "top_p":
                filtered_params[k] = v
        filtered_params["provider"] = "openrouter"
        return filtered_params
    
    # Similar logic for anthropic, meta-llama providers...
```

**Purpose:** Filter and convert parameters based on model provider capabilities  
**Why it didn't work:** Even with correct parameter conversion, LiteLLM still couldn't route Google models through OpenRouter without explicit provider specification

### 1.2 Enhanced LM Creation Function
**What was changed:**
```python
def create_agent_lm(model_id: str, api_base: str, api_key: str, **lm_params) -> dspy.LM:
    # BEFORE (working but ignored parameters):
    return dspy.LM(model=model_id, api_base=api_base, api_key=api_key)
    
    # ATTEMPTED (complex parameter handling):
    safe_params = {k: v for k, v in lm_params.items() if v is not None}
    validated_params = validate_lm_config_for_model(model_id, safe_params)
    
    explicit_kwargs = {
        "model": model_id,
        "api_base": api_base,
        "api_key": api_key,
    }
    
    for key, value in validated_params.items():
        explicit_kwargs[key] = value
        
    if "openrouter.ai" in api_base:
        explicit_kwargs["provider"] = "openrouter"
        os.environ["LITELLM_PROVIDER"] = "openrouter"
    
    return dspy.LM(**explicit_kwargs)
```

**Purpose:** Ensure custom parameters are properly passed to DSPy LM instances  
**Why it didn't work:** DSPy internal modules still created new LM instances without provider information, causing LiteLLM routing failures

### 1.3 Global DSPy Monkey Patch
**What was added:**
```python
_original_LM_init = dspy.LM.__init__

def _patched_LM_init(self, *args, **kwargs):
    model = kwargs.get("model") or (args[0] if args else None)
    api_base = kwargs.get("api_base", "")
    
    if model and ("openrouter.ai" in api_base or "google/" in model or "gemini" in model):
        kwargs.setdefault("provider", "openrouter")
    
    os.environ.setdefault("LITELLM_PROVIDER", "openrouter")
    return _original_LM_init(self, *args, **kwargs)

dspy.LM.__init__ = _patched_LM_init
```

**Purpose:** Ensure ALL DSPy LM instances (including internal ones) get correct provider  
**Why it didn't work:** Still produced "LLM Provider NOT provided" errors, indicating the monkey patch wasn't catching all LM creation paths

---

## 2. Simulation Changes (`app/classes/simulation.py`)

### 2.1 Per-Agent Context Management
**What was changed:**
```python
# BEFORE (original approach):
a = PoliAgent(
    agent_id=idx,
    name=agent_config.name,
    background=agent_config.profile,
    topic=self.topic,
    embedder=self.embedder,
    model=agent_model,
    max_interventions=self.max_interventions_per_agent,
)

# ATTEMPTED (context-wrapped creation):
if agent_model:
    with dspy.context(lm=agent_model):
        a = PoliAgent(
            agent_id=idx,
            name=agent_config.name,
            background=agent_config.profile,
            topic=self.topic,
            embedder=self.embedder,
            model=agent_model,
            max_interventions=self.max_interventions_per_agent,
        )
```

**Purpose:** Ensure each agent is created with its own LM context to prevent DSPy global state conflicts  
**Why it didn't work:** DSPy thread safety constraints prevented context switching during parallel execution

---

## 3. Agent Changes (`app/classes/agents.py`)

### 3.1 Debug Monkey Patching
**What was added:**
```python
_original_lm_call = dspy.LM.__call__
_original_lm_forward = dspy.LM.forward

def debug_lm_call(self, *args, **kwargs):
    print(f"🔥 FINAL LM.__call__ to {getattr(self, 'model', 'UNKNOWN')} with kwargs:", kwargs)
    return _original_lm_call(self, *args, **kwargs)

def debug_lm_forward(self, *args, **kwargs):
    print(f"🔥 FINAL LM.forward to {getattr(self, 'model', 'UNKNOWN')} with kwargs:", kwargs)
    print(f"🔥 LM instance kwargs: {getattr(self, 'kwargs', {})}")
    return _original_lm_forward(self, *args, **kwargs)

dspy.LM.__call__ = debug_lm_call
dspy.LM.forward = debug_lm_forward
```

**Purpose:** Debug actual API calls to verify parameters were being passed correctly  
**Why it helped:** Revealed that parameters were correctly passed to LM creation but provider information was missing during actual API calls

### 3.2 Context-Based Module Creation
**What was changed:**
```python
# BEFORE (original approach):
if model:
    self.intent_module = dspy.Predict(AgentIntentSignature)
    self.respond_module = dspy.ReAct(signature=AgentRespondSignature, tools=[], max_iters=react_max_iters)
    self.vote_module = dspy.ChainOfThought(AgentVoteSignature)
    self.respond_module.lm = model

# ATTEMPTED (context-wrapped creation):
if model:
    with dspy.context(lm=model):
        self.intent_module = dspy.Predict(AgentIntentSignature)
        self.respond_module = dspy.ReAct(signature=AgentRespondSignature, tools=[], max_iters=react_max_iters)
        self.vote_module = dspy.ChainOfThought(AgentVoteSignature)
    self.respond_module.lm = model
```

**Purpose:** Ensure all DSPy modules are created with the correct LM context  
**Why it didn't work:** Modules still used global DSPy settings during actual inference calls

### 3.3 Thread-Safe Method Execution
**What was changed:**
```python
# BEFORE (original approach):
def propose(self, last_speaker: str, last_opinion: str) -> Dict[str, Any]:
    out = self.intent_module(
        topic=self.topic,
        context=short_context,
        persona_description=self.persona_description,
        last_speaker=last_speaker,
        last_opinion=last_opinion,
        interventions_remaining=self._get_intervention_context(),
    )

# ATTEMPTED (context-wrapped execution):
def propose(self, last_speaker: str, last_opinion: str) -> Dict[str, Any]:
    if self.model:
        with dspy.context(lm=self.model):
            out = self.intent_module(
                topic=self.topic,
                context=short_context,
                persona_description=self.persona_description,
                last_speaker=last_speaker,
                last_opinion=last_opinion,
                interventions_remaining=self._get_intervention_context(),
            )
    else:
        out = self.intent_module(...)
```

**Purpose:** Ensure each method call uses the agent's specific LM instead of global defaults  
**Why it didn't work:** DSPy's "settings can only be changed by the thread that initially configured it" error during parallel execution

### 3.4 Extensive Debug Logging
**What was added throughout methods:**
```python
print(f"DEBUG: Agent {self.name} checking intent to speak")
print(f"  - Agent model: {self.model}")
print(f"  - Model ID: {getattr(self.model, 'model', 'NOT_FOUND')}")
print(f"  - Max tokens: {getattr(self.model, 'max_tokens', 'NOT_FOUND')}")
print(f"  - Temperature: {getattr(self.model, 'temperature', 'NOT_FOUND')}")
print(f"  - Model kwargs: {getattr(self.model, 'kwargs', 'NOT_FOUND')}")
```

**Purpose:** Track LM instance state and parameter propagation throughout the execution pipeline  
**Result:** Confirmed that LM instances had correct parameters but LiteLLM still failed with provider errors

---

## 4. Main Application Changes (`app/main.py`)

### 4.1 Provider Addition to Global LM
**What was changed:**
```python
# BEFORE:
lm = dspy.LM(
    model="openai/gpt-4o-mini",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# ATTEMPTED:
lm = dspy.LM(
    model="openai/gpt-4o-mini",
    api_base="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    provider="openrouter"
)
```

**Purpose:** Ensure even the global default LM has correct provider information  
**Result:** Didn't solve the issue since individual agent LMs were still failing

---

## Summary of Root Causes

### 1. LiteLLM Provider Routing Issues
- **Problem**: LiteLLM couldn't route Google models through OpenRouter without explicit `provider="openrouter"`
- **Error**: `litellm.BadRequestError: LLM Provider NOT provided. You passed model=google/gemini-2.5-flash`
- **Attempted Solutions**: 
  - Adding provider to all LM creation calls
  - Setting `LITELLM_PROVIDER` environment variable
  - Global monkey patching of `dspy.LM.__init__`
- **Why they failed**: DSPy creates internal LM instances that bypassed our patches

### 2. DSPy Thread Safety Constraints
- **Problem**: DSPy's global settings cannot be changed from threads other than the main thread
- **Error**: `dspy.settings can only be changed by the thread that initially configured it`
- **Attempted Solutions**: 
  - Using `dspy.context()` instead of `dspy.configure()`
  - Per-agent context wrapping
  - Thread-local LM assignment
- **Why they failed**: Still triggered threading violations during parallel agent execution

### 3. DSPy Internal Module Behavior
- **Problem**: DSPy modules (ReAct, Predict, ChainOfThought) create their own LM instances internally
- **Observation**: Even when `self.respond_module.lm = model` was set, modules would revert to global defaults
- **Evidence**: Debug logs showed correct LM parameters during creation but default parameters during execution
- **Root Cause**: DSPy's internal architecture doesn't consistently respect manually assigned LMs

---

## Lessons Learned

1. **DSPy Parameter Handling**: DSPy has its own internal parameter management that's difficult to override reliably
2. **Provider Routing**: OpenRouter + Google models require explicit provider specification at every LM creation point
3. **Thread Safety**: DSPy is not designed for multi-threaded per-agent LM configuration
4. **Debugging Complexity**: The interaction between DSPy, LiteLLM, and OpenRouter creates multiple layers where parameters can be lost
5. **Simplicity vs Features**: The original naive approach (letting DSPy handle everything) was more stable than custom parameter management

---

## Current State

All changes have been reverted to the original naive approach:
- Simple `dspy.LM(model, api_base, api_key)` creation
- No custom parameter validation or provider specification
- No context managers or thread safety patterns
- No debug logging or monkey patching
- DSPy handles all LM configuration with its defaults

The frontend can still send model and parameter selections, but they are received and ignored, allowing DSPy to use its internal defaults. This provides a stable baseline for future parameter handling attempts with a different approach.

---

## Recommendations for Future Attempts

1. **Research DSPy 2.5+ versions** for improved parameter handling and thread safety
2. **Consider alternative frameworks** (LangChain, Guidance) for better multi-agent parameter control
3. **Implement parameter handling at the API layer** instead of the DSPy layer
4. **Use single-threaded execution** to avoid DSPy threading constraints
5. **Focus on OpenAI-compatible models** to avoid provider routing complexity