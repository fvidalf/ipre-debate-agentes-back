"""
Factory for creating embedding providers with consistent configuration.

Provides a centralized way to create and configure embedding providers
with support for caching, batching, and other optimizations.
"""

from typing import Optional, Dict, Any, Type
from .base import EmbeddingProvider
from .cache import InMemoryLRUCache, NoOpCache, EmbeddingCache
from .providers import HuggingFaceProvider, ONNXProvider, OpenRouterProvider


class EmbeddingProviderFactory:
    """
    Factory for creating embedding providers with consistent caching and configuration.
    
    Supports multiple provider types with automatic cache setup and parameter validation.
    """
    
    # Registry of available providers
    _PROVIDERS: Dict[str, Type[EmbeddingProvider]] = {
        "huggingface": HuggingFaceProvider,
        "hf": HuggingFaceProvider,  # Alias
        "onnx": ONNXProvider,
        "onnx_minilm": ONNXProvider,  # Backward compatibility alias
        "openrouter": OpenRouterProvider,
    }
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """Get list of available provider names."""
        return list(cls._PROVIDERS.keys())
    
    @classmethod
    def create_provider(
        cls,
        provider_type: str,
        cache_config: Optional[Dict[str, Any]] = None,
        **provider_kwargs
    ) -> EmbeddingProvider:
        """
        Create an embedding provider with optional caching.
        
        Args:
            provider_type: Type of provider to create ('huggingface', 'onnx', 'openrouter')
            cache_config: Optional cache configuration dict
            **provider_kwargs: Provider-specific configuration parameters
            
        Returns:
            Configured embedding provider instance
            
        Raises:
            ValueError: If provider_type is not supported
            
        Example:
            >>> factory = EmbeddingProviderFactory()
            >>> provider = factory.create_provider(
            ...     "huggingface",
            ...     cache_config={"capacity": 5000, "ttl_seconds": 3600},
            ...     model="sentence-transformers/all-MiniLM-L6-v2",
            ...     batch_size=16
            ... )
        """
        if provider_type not in cls._PROVIDERS:
            raise ValueError(
                f"Unknown provider type: {provider_type}. "
                f"Available providers: {list(cls._PROVIDERS.keys())}"
            )
        
        # Create cache if configuration is provided
        cache = cls._create_cache(cache_config)
        
        # Get provider class
        provider_class = cls._PROVIDERS[provider_type]
        
        # Create provider with cache
        return provider_class(cache=cache, **provider_kwargs)
    
    @classmethod
    def create_huggingface_provider(
        cls,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: Optional[str] = None,
        batch_size: int = 32,
        normalize: bool = True,
        cache_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> HuggingFaceProvider:
        """
        Convenience method to create a HuggingFace provider with common settings.
        
        Args:
            model: HuggingFace model identifier
            api_key: HuggingFace API token
            batch_size: Batch size for API calls
            normalize: Whether to normalize embeddings
            cache_config: Cache configuration
            **kwargs: Additional provider arguments
            
        Returns:
            Configured HuggingFace provider
        """
        cache = cls._create_cache(cache_config)
        return HuggingFaceProvider(
            model=model,
            api_key=api_key,
            batch_size=batch_size,
            normalize=normalize,
            cache=cache,
            **kwargs
        )
    
    @classmethod
    def create_onnx_provider(
        cls,
        model_dir: str = "./onnx-model",
        normalize: bool = True,
        cache_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> ONNXProvider:
        """
        Convenience method to create an ONNX provider with common settings.
        
        Args:
            model_dir: Directory containing ONNX model files
            normalize: Whether to normalize embeddings
            cache_config: Cache configuration
            **kwargs: Additional provider arguments
            
        Returns:
            Configured ONNX provider
        """
        cache = cls._create_cache(cache_config)
        return ONNXProvider(
            model_dir=model_dir,
            normalize=normalize,
            cache=cache,
            **kwargs
        )
    
    @classmethod
    def create_openrouter_provider(
        cls,
        model_name: str = "openai/text-embedding-3-small",
        api_key: Optional[str] = None,
        normalize: bool = True,
        cache_config: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> OpenRouterProvider:
        """
        Convenience method to create an OpenRouter provider with common settings.
        
        Args:
            model_name: OpenRouter model identifier
            api_key: OpenRouter API key
            normalize: Whether to normalize embeddings
            cache_config: Cache configuration
            **kwargs: Additional provider arguments
            
        Returns:
            Configured OpenRouter provider
        """
        cache = cls._create_cache(cache_config)
        return OpenRouterProvider(
            model_name=model_name,
            api_key=api_key,
            normalize=normalize,
            cache=cache,
            **kwargs
        )
    
    @classmethod
    def _create_cache(cls, cache_config: Optional[Dict[str, Any]]) -> EmbeddingCache:
        """
        Create cache instance from configuration.
        
        Args:
            cache_config: Cache configuration dict with keys:
                - type: Cache type ('lru' or 'none', defaults to 'lru')
                - capacity: Maximum cache size (default: 10000)
                - ttl_seconds: Time-to-live in seconds (optional)
                
        Returns:
            Cache instance
        """
        if not cache_config:
            return NoOpCache()
        
        cache_type = cache_config.get("type", "lru").lower()
        
        if cache_type == "none":
            return NoOpCache()
        elif cache_type == "lru":
            return InMemoryLRUCache(
                capacity=cache_config.get("capacity", 10000),
                ttl_seconds=cache_config.get("ttl_seconds")
            )
        else:
            raise ValueError(f"Unknown cache type: {cache_type}")


# Convenience instance for easy access
embedding_factory = EmbeddingProviderFactory()