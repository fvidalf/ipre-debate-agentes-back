"""
OpenRouter embedding provider using DSPy integration.

Wraps the existing DSPy OpenRouter implementation with the new provider interface
and adds caching support.
"""

import os
from typing import List, Optional, Iterable
import numpy as np
import dspy

from ..base import EmbeddingProvider, TextInput, ArrayOrList, safe_cosine_similarity
from ..cache import EmbeddingCache, NoOpCache, create_cache_key


class OpenRouterProvider(EmbeddingProvider):
    """
    OpenRouter embedding provider using DSPy's embedder abstraction.
    
    Features:
    - Integration with OpenRouter's API through DSPy
    - Intelligent caching to reduce API costs
    - Support for various OpenRouter embedding models
    - Thread-safe operations
    """

    def __init__(
        self,
        model_name: str = "openai/text-embedding-3-small",
        api_key: Optional[str] = None,
        cache: Optional[EmbeddingCache] = None,
        normalize: bool = True,
        dtype: np.dtype = np.float32
    ):
        """
        Initialize OpenRouter embedding provider.
        
        Args:
            model_name: OpenRouter model identifier
            api_key: OpenRouter API key (defaults to OPENROUTER_API_KEY env var)
            cache: Optional cache implementation
            normalize: Whether to L2-normalize embeddings
            dtype: NumPy data type for embeddings
        """
        self._model_name = model_name
        self.cache = cache or NoOpCache()
        self.normalize = normalize
        self.dtype = dtype
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
        
        # Initialize DSPy embedder for OpenRouter
        self.embedder = dspy.Embedder(
            model=self._model_name,
            api_base="https://openrouter.ai/api/v1",
            api_key=self.api_key
        )

    @property
    def supports_batching(self) -> bool:
        return False  # DSPy embedder doesn't expose batch interface

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, texts: TextInput) -> ArrayOrList:
        """
        Embed one or many texts using OpenRouter via DSPy.
        
        Args:
            texts: Single string or list of strings to embed
            
        Returns:
            Single numpy array for string input, list of arrays for list input
        """
        single = isinstance(texts, str)
        items = [texts] if single else list(texts)

        # Check cache for each item
        vectors = []
        missing_indices = []
        missing_texts = []
        
        for i, text in enumerate(items):
            cached_vec = self._get_from_cache(text)
            if cached_vec is not None:
                vectors.append(cached_vec)
            else:
                vectors.append(None)
                missing_indices.append(i)
                missing_texts.append(text)

        # Compute missing embeddings
        if missing_texts:
            computed_embeddings = self._embed_batch(missing_texts)
            for idx, embedding in zip(missing_indices, computed_embeddings):
                vectors[idx] = embedding
                self._store_in_cache(items[idx], embedding)

        # All vectors should be filled now
        result: List[np.ndarray] = vectors  # type: ignore
        return result[0] if single else result

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return safe_cosine_similarity(a, b)

    def cosine_many(self, query_vec: np.ndarray, doc_vecs: Iterable[np.ndarray]) -> np.ndarray:
        """
        Calculate cosine similarities between a query vector and multiple document vectors.
        """
        Q = query_vec
        if not np.isclose(np.linalg.norm(Q), 1.0, atol=1e-3):
            norm = np.linalg.norm(Q)
            Q = Q / norm if norm > 0 else Q

        # Stack and normalize document vectors if needed
        if isinstance(doc_vecs, np.ndarray) and doc_vecs.ndim == 2:
            D = doc_vecs
        else:
            D = np.vstack([d for d in doc_vecs])
        
        norms = np.linalg.norm(D, axis=1, keepdims=True)
        need_norm = np.any(np.abs(norms - 1.0) > 1e-3)
        if need_norm:
            nonzero_mask = norms.flatten() != 0
            D[nonzero_mask] = D[nonzero_mask] / norms[nonzero_mask]
        
        return (D @ Q).astype(self.dtype)

    def _get_from_cache(self, text: str) -> Optional[np.ndarray]:
        """Retrieve embedding from cache."""
        cache_key = create_cache_key(self.model_name, text)
        return self.cache.get(cache_key)

    def _store_in_cache(self, text: str, vec: np.ndarray) -> None:
        """Store embedding in cache."""
        cache_key = create_cache_key(self.model_name, text)
        self.cache.set(cache_key, vec)

    def _embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Embed a batch of texts using DSPy embedder.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding arrays
        """
        if not texts:
            return []

        # Use DSPy embedder - it expects a list and returns a list
        embeddings = self.embedder(texts)
        
        result = []
        for embedding in embeddings:
            arr = np.asarray(embedding, dtype=self.dtype)
            if self.normalize:
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
            result.append(arr)
        
        return result