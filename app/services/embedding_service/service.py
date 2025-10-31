"""
Main embedding service providing a unified interface for all embedding operations.

This is the primary interface that replaces the old SentenceEmbedder,
providing backward compatibility while enabling modern provider-based architecture.
"""

from typing import Optional, Union, List, Iterable
import numpy as np

from .base import EmbeddingProvider, TextInput


class EmbeddingService:
    """
    Unified embedding service with provider abstraction.
    
    This service acts as the main interface for embedding operations,
    delegating to specific providers while maintaining a consistent API
    that's compatible with the legacy SentenceEmbedder interface.
    
    Features:
    - Provider abstraction for different embedding backends
    - Backward compatibility with existing agent code
    - Consistent interface across all provider types
    - Support for both single and batch embedding operations
    """

    def __init__(self, provider: EmbeddingProvider):
        """
        Initialize embedding service with a specific provider.
        
        Args:
            provider: Embedding provider instance (HuggingFace, ONNX, OpenRouter, etc.)
        """
        self.provider = provider

    def encode(self, sentences: Union[str, List[str], Iterable[str]]) -> np.ndarray:
        """
        Encode sentences into embeddings.
        
        Maintains exact interface compatibility with the legacy SentenceEmbedder.encode().
        Always returns a 2D numpy array for consistency.
        
        Args:
            sentences: String, list of strings, or iterable of strings to encode
            
        Returns:
            2D numpy array of embeddings with shape (n_sentences, embedding_dim)
        """
        # Handle different input types
        if isinstance(sentences, str):
            # Single string: embed and wrap in 2D array
            result = self.provider.embed(sentences)
            return np.array([result])
        
        # List or iterable: convert to list and embed
        sentence_list = list(sentences) if not isinstance(sentences, list) else sentences
        if not sentence_list:
            # Empty input: return empty 2D array
            return np.array([]).reshape(0, -1)
        
        embeddings = self.provider.embed(sentence_list)
        return np.array(embeddings)

    def text_similarity_score(self, text1: str, text2: str) -> float:
        """
        Calculate similarity score between two texts.
        
        Maintains backward compatibility with legacy SentenceEmbedder interface.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between the two texts
        """
        emb1 = self.provider.embed(text1)
        emb2 = self.provider.embed(text2)
        return self.provider.cosine(emb1, emb2)

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate similarity between two embedding vectors.
        
        Maintains backward compatibility with legacy SentenceEmbedder interface.
        
        Args:
            a: First embedding vector
            b: Second embedding vector
            
        Returns:
            Cosine similarity score between the vectors
        """
        return self.provider.cosine(a, b)

    def similarity_many(self, query_vec: np.ndarray, doc_vecs: Iterable[np.ndarray]) -> np.ndarray:
        """
        Calculate similarities between a query vector and multiple document vectors.
        
        Args:
            query_vec: Single query embedding vector
            doc_vecs: Iterable of document embedding vectors
            
        Returns:
            Array of cosine similarity scores
        """
        return self.provider.cosine_many(query_vec, doc_vecs)

    def embed_batch(self, texts: List[str], batch_size: Optional[int] = None) -> List[np.ndarray]:
        """
        Embed a batch of texts with optional batch size control.
        
        Args:
            texts: List of texts to embed
            batch_size: Optional batch size override (only used by providers that support batching)
            
        Returns:
            List of embedding arrays
        """
        if hasattr(self.provider, 'embed_batch') and self.provider.supports_batching:
            return self.provider.embed_batch(texts, batch_size)
        else:
            # Fallback for providers without batching support
            return [self.provider.embed(text) for text in texts]

    # Provider information and capabilities
    @property
    def model_name(self) -> str:
        """Get the underlying model name/identifier."""
        return self.provider.model_name

    @property
    def supports_batching(self) -> bool:
        """Check if the provider supports efficient batching."""
        return self.provider.supports_batching

    @property
    def provider_type(self) -> str:
        """Get the provider type name."""
        return self.provider.__class__.__name__

    def cache_stats(self) -> Optional[dict]:
        """
        Get cache statistics if the provider supports caching.
        
        Returns:
            Cache statistics dict or None if caching is not enabled
        """
        cache = getattr(self.provider, 'cache', None)
        if cache and hasattr(cache, 'stats'):
            return cache.stats()
        return None

    def clear_cache(self) -> None:
        """Clear the provider's cache if it exists."""
        cache = getattr(self.provider, 'cache', None)
        if cache and hasattr(cache, 'clear'):
            cache.clear()

    def __repr__(self) -> str:
        """String representation of the service."""
        return f"EmbeddingService(provider={self.provider_type}, model={self.model_name})"