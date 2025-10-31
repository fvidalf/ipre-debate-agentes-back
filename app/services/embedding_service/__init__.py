"""
Modern, modular embedding service with provider abstraction.

This package provides a unified interface for various embedding providers
with features like intelligent caching, batching, and normalization.
"""

from .service import EmbeddingService
from .factory import EmbeddingProviderFactory
from .base import EmbeddingProvider, EmbeddingCache
from .cache import InMemoryLRUCache, NoOpCache
from .shared import get_embedding_service, reset_embedding_service, embedding_service_stats
from .utils import setup_onnx_model

__all__ = [
    "EmbeddingService",
    "EmbeddingProviderFactory", 
    "EmbeddingProvider",
    "EmbeddingCache",
    "InMemoryLRUCache",
    "NoOpCache",
    "get_embedding_service",
    "reset_embedding_service", 
    "embedding_service_stats",
    "setup_onnx_model"
]