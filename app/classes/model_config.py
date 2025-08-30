from typing import List, Dict, Optional
import dspy
import httpx
import asyncio
import os

# Cache for available models to avoid repeated API calls
_cached_models: Optional[Dict[str, Dict[str, str]]] = None

DEFAULT_MODEL = "openai/gpt-4o-mini"

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
                    
                    # Only include specific providers/models we want to support
                    if any(provider in model_id for provider in ["openai", "anthropic", "meta-llama", "google"]):
                        models[model_id] = {
                            "name": model.get("name", model_id),
                            "description": model.get("description", ""),
                            "provider": model_id.split("/")[0] if "/" in model_id else "unknown"
                        }
                
                _cached_models = models if models else FALLBACK_MODELS
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

def create_agent_lm(model_id: str, api_base: str, api_key: str) -> dspy.LM:
    """Create a dspy LM instance for a specific model"""
    if not is_valid_model(model_id):
        print(f"Warning: Model {model_id} not found in available models, using default")
        model_id = DEFAULT_MODEL
    
    return dspy.LM(
        model=model_id,
        api_base=api_base,
        api_key=api_key
    )
