"""
Shared embedding service for the entire application.

Provides a singleton pattern to ensure a single embedding service instance
is used across the entire server, reducing memory usage and improving
performance through shared caching.
"""

import threading
from typing import Optional
from .service import EmbeddingService
from .factory import EmbeddingProviderFactory
from .utils import get_embedding_config_from_env


class SharedEmbeddingService:
    """
    Singleton wrapper for the embedding service.
    
    Ensures only one embedding service instance exists across the entire
    application, with thread-safe initialization.
    """
    
    _instance: Optional[EmbeddingService] = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, provider_type: Optional[str] = None, **config_override) -> EmbeddingService:
        """
        Get the shared embedding service instance.
        
        Args:
            provider_type: Optional provider type override
            **config_override: Optional configuration overrides
            
        Returns:
            Shared EmbeddingService instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = cls._create_service(provider_type, **config_override)
        
        return cls._instance
    
    @classmethod
    def _create_service(cls, provider_type: Optional[str] = None, **config_override) -> EmbeddingService:
        """Create the embedding service using the factory."""
        env_provider_type, env_config = get_embedding_config_from_env()
        final_provider_type = provider_type or env_provider_type
        final_config = {**env_config, **config_override}
        
        print(f"🔧 Initializing shared embedding service: {final_provider_type}")
        
        # Use the factory to create provider
        provider = EmbeddingProviderFactory.create_provider(
            provider_type=final_provider_type,
            **final_config
        )
        
        return EmbeddingService(provider)
    
    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (useful for testing)."""
        with cls._lock:
            if cls._instance:
                cls._instance.clear_cache()
            cls._instance = None
    
    @classmethod
    def is_initialized(cls) -> bool:
        """Check if the service has been initialized."""
        return cls._instance is not None


# Global functions for easy access
def get_embedding_service(provider_type: Optional[str] = None, **config_override) -> EmbeddingService:
    """
    Get the shared embedding service instance.
    
    This is the main function that should be used throughout the application
    to access embeddings functionality.
    
    Args:
        provider_type: Optional provider type override
        **config_override: Optional configuration overrides
        
    Returns:
        Shared EmbeddingService instance
    """
    return SharedEmbeddingService.get_instance(provider_type, **config_override)


def reset_embedding_service() -> None:
    """Reset the shared embedding service (useful for testing)."""
    SharedEmbeddingService.reset()


def embedding_service_stats() -> Optional[dict]:
    """Get statistics from the shared embedding service."""
    if SharedEmbeddingService.is_initialized():
        return SharedEmbeddingService.get_instance().cache_stats()
    return None