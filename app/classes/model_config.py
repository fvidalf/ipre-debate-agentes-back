from typing import List, Dict, Optional
import dspy
import httpx
import asyncio
import os

# Cache for available models to avoid repeated API calls
_cached_models: Optional[Dict[str, Dict[str, str]]] = None

DEFAULT_MODEL = "openai/gpt-4o-mini"

# Models to exclude from the available list (not suitable for debate agents)
EXCLUDED_MODELS = {
    # Image/Vision-focused models not suited for text debates
    "google/gemini-2.5-flash-image",
    "google/gemini-2.5-flash-image-preview",
    "openai/gpt-4o-audio-preview",  # Audio-focused
    
    # Specialized/niche models not suited for general debate
    "openai/gpt-5-codex",  # Coding-specific
    "openai/codex-mini",   # Coding-specific
    "openai/gpt-4o-mini-search-preview",  # Search-specific
    "openai/gpt-4o-search-preview",       # Search-specific
    
    # Content moderation models (not for conversation)
    "meta-llama/llama-guard-3-8b",
    "meta-llama/llama-guard-4-12b",
    "meta-llama/llama-guard-2-8b",
    
    # Obscure/experimental models with unclear reliability
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b:free",
    "openai/gpt-oss-20b",
    "google/gemma-3n-e2b-it:free",  # 2B model too small
    "google/gemma-3n-e2b-it",
    "google/gemma-3n-e4b-it:free",
    "google/gemma-3n-e4b-it",
    
    # Redundant older versions when newer ones are available
    "openai/gpt-4-0314",
    "openai/gpt-3.5-turbo-0613",
    "openai/gpt-4-1106-preview",
    "openai/gpt-4-turbo-preview",
    "anthropic/claude-3.5-sonnet-20240620",  # Newer version exists
    "openai/gpt-4o-2024-05-13",  # Older version
    "openai/gpt-4o-2024-08-06",  # Older version
    "openai/o1-mini-2024-09-12", # Older version
    "openai/gpt-4o-mini-2024-07-18",  # Older version
    "google/gemini-2.5-pro-preview-05-06",  # Preview versions
    "google/gemini-2.5-pro-preview-06-05",
    "google/gemini-2.5-flash-preview-09-2025",
    "google/gemini-2.5-flash-lite-preview-09-2025",
    "google/gemini-2.5-flash-lite-preview-06-17",
    
    # Models that are too small/limited for quality debates
    "meta-llama/llama-3.2-1b-instruct",  # 1B too small
    
    # Overly expensive flagship models that are overkill
    "openai/o3-pro",  # Requires BYOK, expensive
    "meta-llama/llama-3.1-405b-instruct",  # Massive model, expensive
    
    # Redundant variants when standard version exists
    "openai/o3-mini-high",  # Same as o3-mini with different settings
    "openai/o4-mini-high",  # Same as o4-mini with different settings
    "anthropic/claude-3.7-sonnet:thinking",  # Variant of standard model
    "openai/gpt-4o:extended",  # Extended context variant
    "openai/chatgpt-4o-latest",  # ChatGPT-specific variant
    "google/gemini-2.0-flash-exp:free",  # Experimental version
}

# Fallback models in case OpenRouter API is unavailable
FALLBACK_MODELS = {
    "openai/gpt-4o": {
        "name": "GPT-4o",
        "description": "Most capable OpenAI model, excellent for complex reasoning",
        "provider": "openai"
    },
    "openai/gpt-4o-mini": {
        "name": "GPT-4o Mini", 
        "description": "Faster and cheaper version of GPT-4o, good balance of capability and cost",
        "provider": "openai"
    },
    "anthropic/claude-3.5-sonnet": {
        "name": "Claude 3.5 Sonnet",
        "description": "Anthropic's most capable model, excellent for nuanced discussions",
        "provider": "anthropic"
    },
    "anthropic/claude-3-haiku": {
        "name": "Claude 3 Haiku",
        "description": "Fast and efficient Anthropic model, good for quick responses",
        "provider": "anthropic"
    },
    "meta-llama/llama-3.1-8b-instruct": {
        "name": "Llama 3.1 8B",
        "description": "Open source model, good for diverse perspectives",
        "provider": "meta"
    },
    "google/gemini-pro": {
        "name": "Gemini Pro",
        "description": "Google's advanced model, strong analytical capabilities",
        "provider": "google"
    }
}

async def fetch_openrouter_models() -> Dict[str, Dict[str, str]]:
    """Fetch available models from OpenRouter API"""
    global _cached_models
    
    if _cached_models is not None:
        return _cached_models
    
    try:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            print("Warning: No OPENROUTER_API_KEY found, using fallback models")
            _cached_models = FALLBACK_MODELS
            return _cached_models
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openrouter.ai/api/v1/models",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "https://localhost:8000",  # Required by OpenRouter
                    "X-Title": "Debate Agents Backend"
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                models = {}
                
                # Filter for models suitable for debate agents
                for model in data.get("data", []):
                    model_id = model.get("id", "")
                    
                    # Skip excluded models
                    if model_id in EXCLUDED_MODELS:
                        continue
                    
                    # Only include specific providers/models we want to support
                    if any(provider in model_id for provider in ["openai", "anthropic", "meta-llama", "google"]):
                        models[model_id] = {
                            "name": model.get("name", model_id),
                            "description": model.get("description", ""),
                            "provider": model_id.split("/")[0] if "/" in model_id else "unknown"
                        }
                
                # Sort models by provider first, then by model name
                sorted_models = dict(sorted(
                    models.items(),
                    key=lambda x: (x[1]["provider"], x[1]["name"])
                ))
                
                _cached_models = sorted_models if sorted_models else FALLBACK_MODELS
                return _cached_models
            else:
                print(f"Warning: OpenRouter API returned status {response.status_code}, using fallback models")
                _cached_models = FALLBACK_MODELS
                return _cached_models
                
    except Exception as e:
        print(f"Warning: Failed to fetch models from OpenRouter: {e}, using fallback models")
        _cached_models = FALLBACK_MODELS
        return _cached_models

def get_available_models() -> Dict[str, Dict[str, str]]:
    """Get the list of available models for agent configuration (sync wrapper)"""
    global _cached_models
    
    if _cached_models is not None:
        return _cached_models
    
    # Try to fetch from OpenRouter, fallback to hardcoded list
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(fetch_openrouter_models())
    except RuntimeError:
        # No event loop, create a new one
        return asyncio.run(fetch_openrouter_models())

def is_valid_model(model_id: str) -> bool:
    """Check if a model ID is in the available models"""
    available = get_available_models()
    return model_id in available

def validate_lm_config_for_model(model_id: str, lm_config: Dict) -> Dict:
    """Validate and filter LM config parameters based on model capabilities"""
    # COMMENTED OUT: Custom parameter handling - reverting to DSPy defaults
    # print(f"DEBUG: validate_lm_config_for_model called with model_id={model_id}, lm_config={lm_config}")
    
    # Simply return the config as-is, let DSPy handle everything
    return lm_config if lm_config else {}
    
    # provider = model_id.split("/")[0] if "/" in model_id else "unknown"
    # model_name = model_id.lower()
    
    # # Check for OpenAI reasoning models (o-series and gpt-5)
    # is_reasoning_model = (
    #     provider == "openai" and (
    #         "gpt-5" in model_name or 
    #         model_name.startswith("openai/o1") or 
    #         model_name.startswith("openai/o3") or
    #         model_name.startswith("openai/o4")
    #     )
    # )
    
    # if is_reasoning_model:
    #     # Reasoning models have strict requirements: temperature=1.0, max_tokens >= 16000
    #     # Apply these regardless of what user provided
    #     print(f"Info: {model_id} is a reasoning model, applying required parameters (temperature=1.0, max_tokens=16000)")
    #     return {
    #         "temperature": 1.0,
    #         "max_tokens": max(16000, lm_config.get("max_tokens", 16000) if lm_config else 16000),
    #         "provider": "openrouter"  # Add provider for reasoning models too
    #         # Only temperature and max_tokens are allowed, other params are ignored
    #     }
    
    # # For non-reasoning models, return provider even if no config provided
    # if not lm_config:
    #     return {"provider": "openrouter"}
    
    # if provider == "anthropic":
    #     # Claude models don't support frequency/presence penalties
    #     filtered_params = {k: v for k, v in lm_config.items() 
    #                       if k not in ["frequency_penalty", "presence_penalty"]}
    #     # Add provider for Anthropic models via OpenRouter
    #     filtered_params["provider"] = "openrouter"
    #     return filtered_params
    # elif provider == "google":
    #     # Gemini models have limited parameter support
    #     # CRITICAL: DSPy adds default max_tokens=4000 if not provided
    #     # We must explicitly set max_tokens to our value to prevent the default
    #     filtered_params = {}
    #     for k, v in lm_config.items():
    #         if k == "temperature":
    #             filtered_params[k] = v
    #         elif k == "max_tokens":
    #             # For Google models, set BOTH parameters to the same value
    #             # This prevents DSPy from adding its default max_tokens=4000
    #             filtered_params["max_output_tokens"] = v
    #             filtered_params["max_tokens"] = v  # Explicitly override DSPy default
    #         elif k == "top_p":
    #             filtered_params[k] = v
        
    #     # 🔧 CRITICAL: Add provider for Google models to prevent LiteLLM provider errors
    #     filtered_params["provider"] = "openrouter"
    #     print(f"DEBUG: Google model {model_id} filtered params with provider: {filtered_params}")
    #     return filtered_params
    # elif provider == "meta-llama":
    #     # Meta models support most OpenAI parameters
    #     filtered_params = {k: v for k, v in lm_config.items() 
    #                       if k not in ["frequency_penalty", "presence_penalty"]}
    #     # Add provider for Meta models via OpenRouter
    #     filtered_params["provider"] = "openrouter"
    #     return filtered_params
    # else:
    #     # OpenAI-compatible models, keep all params and add provider
    #     filtered_params = dict(lm_config)
    #     filtered_params["provider"] = "openrouter"
    #     return filtered_params

def create_agent_lm(model_id: str, api_base: str, api_key: str, **lm_params) -> dspy.LM:
    """Create a dspy LM instance for a specific model with customizable parameters"""
    if not is_valid_model(model_id):
        # print(f"Warning: Model {model_id} not found in available models, using default")
        model_id = DEFAULT_MODEL
    
    # COMMENTED OUT: Custom parameter handling - reverting to DSPy defaults
    # Filter out None values and validate parameter compatibility
    # safe_params = {k: v for k, v in lm_params.items() if v is not None}
    # validated_params = validate_lm_config_for_model(model_id, safe_params)
    
    try:
        # print(f"DEBUG: Creating dspy.LM with model={model_id}, validated_params={validated_params}")
        
        # SIMPLE APPROACH: Let DSPy handle everything with defaults
        return dspy.LM(model=model_id, api_base=api_base, api_key=api_key)
        
        # COMMENTED OUT: All custom parameter handling
        # # CRITICAL FIX: Pass parameters as explicit top-level kwargs to prevent DSPy adapters 
        # # from silently dropping them. This ensures Google models get max_output_tokens.
        # explicit_kwargs = {
        #     "model": model_id,
        #     "api_base": api_base,
        #     "api_key": api_key,
        # }
        
        # # Add validated parameters as explicit kwargs
        # for key, value in validated_params.items():
        #     explicit_kwargs[key] = value
        
        # # 🔧 PROVIDER FIX: Explicitly specify provider when using OpenRouter
        # # This prevents LiteLLM's "LLM Provider NOT provided" error for Google models
        # if "openrouter.ai" in api_base:
        #     explicit_kwargs["provider"] = "openrouter"
        #     # GLOBAL FIX: Set environment variable to ensure ALL LiteLLM calls use OpenRouter
        #     # This covers indirect DSPy LM creations in raise_hand, proposal modules, etc.
        #     import os
        #     os.environ["LITELLM_PROVIDER"] = "openrouter"
        #     print(f"DEBUG: Added provider=openrouter for OpenRouter API base + set global LITELLM_PROVIDER")
        
        # print(f"DEBUG: Final explicit kwargs for dspy.LM: {explicit_kwargs}")
        
        # lm_instance = dspy.LM(**explicit_kwargs)
        
        # # Log detailed LM instance information
        # print(f"DEBUG: Created LM instance:")
        # print(f"  - model: {getattr(lm_instance, 'model', 'NOT_FOUND')}")
        # print(f"  - max_tokens: {getattr(lm_instance, 'max_tokens', 'NOT_FOUND')}")
        # print(f"  - temperature: {getattr(lm_instance, 'temperature', 'NOT_FOUND')}")
        # print(f"  - top_p: {getattr(lm_instance, 'top_p', 'NOT_FOUND')}")
        # print(f"  - kwargs: {getattr(lm_instance, 'kwargs', 'NOT_FOUND')}")
        
        # # Try to access internal config if available
        # if hasattr(lm_instance, '__dict__'):
        #     print(f"  - LM instance attributes: {list(lm_instance.__dict__.keys())}")
        #     for key, value in lm_instance.__dict__.items():
        #         if 'token' in key.lower() or 'temp' in key.lower() or 'top_p' in key.lower():
        #             print(f"    {key}: {value}")
        
        # return lm_instance
    except Exception as e:
        # print(f"Failed to create LM for {model_id} with params {validated_params}: {e}")
        # Fallback to default model without custom params
        try:
            # print(f"Falling back to default model: {DEFAULT_MODEL}")
            return dspy.LM(model=DEFAULT_MODEL, api_base=api_base, api_key=api_key)
        except Exception as fallback_e:
            # print(f"Fallback to default model also failed: {fallback_e}")
            raise fallback_e

# --- COMMENTED OUT: Global DSPy Provider Patch ---
# REVERTED: All custom parameter and provider handling commented out
# Going back to DSPy defaults for stability

# _original_LM_init = dspy.LM.__init__

# def _patched_LM_init(self, *args, **kwargs):
#     # Automatically add provider=openrouter for any OpenRouter model
#     model = kwargs.get("model") or (args[0] if args else None)
#     api_base = kwargs.get("api_base", "")
    
#     if model and ("openrouter.ai" in api_base or "google/" in model or "gemini" in model):
#         kwargs.setdefault("provider", "openrouter")
#         print(f"🔧 GLOBAL PATCH: Added provider=openrouter for model={model}")
    
#     # Ensure all LiteLLM calls have a fallback provider environment variable
#     import os
#     os.environ.setdefault("LITELLM_PROVIDER", "openrouter")
    
#     return _original_LM_init(self, *args, **kwargs)

# dspy.LM.__init__ = _patched_LM_init
# print("✅ Patched DSPy.LM.__init__ to always include provider=openrouter for OpenRouter/Gemini models")
