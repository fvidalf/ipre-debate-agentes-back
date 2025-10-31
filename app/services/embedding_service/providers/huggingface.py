"""
HuggingFace Inference API embedding provider.

Provides high-performance embedding generation with intelligent batching,
caching, and normalization using the HuggingFace Inference API.
"""

import os
import threading
from typing import List, Optional, Iterable
import numpy as np
from huggingface_hub import InferenceClient

from ..base import BatchableProvider, TextInput, ArrayOrList, safe_cosine_similarity
from ..cache import EmbeddingCache, NoOpCache, create_cache_key


class HuggingFaceProvider(BatchableProvider):
    """
    HuggingFace Inference API implementation with advanced optimizations.
    
    Features:
    - Intelligent batching to reduce API calls
    - Thread-safe LRU caching with TTL support
    - L2 normalization for stable cosine similarity
    - Efficient vectorized operations for bulk similarity calculations
    - Configurable batch sizes and data types
    """

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: Optional[str] = None,
        *,
        normalize: bool = True,
        batch_size: int = 32,
        cache: Optional[EmbeddingCache] = None,
        dtype: np.dtype = np.float32,
        provider: str = "hf-inference",
    ):
        """
        Initialize HuggingFace embedding provider.
        
        Args:
            model: HuggingFace model identifier
            api_key: HuggingFace API token (defaults to HF_TOKEN env var)
            normalize: Whether to L2-normalize embeddings
            batch_size: Maximum batch size for API calls
            cache: Optional cache implementation
            dtype: NumPy data type for embeddings
            provider: Provider string for InferenceClient
        """
        self._model = model
        self.normalize = normalize
        self.batch_size = max(1, batch_size)
        self.cache = cache or NoOpCache()
        self.dtype = dtype

        self._client = InferenceClient(
            provider=provider,
            api_key=api_key or os.getenv("HF_TOKEN"),
        )
        self._lock = threading.RLock()

    @property
    def model_name(self) -> str:
        return self._model

    def embed(self, texts: TextInput) -> ArrayOrList:
        """
        Embed one or many texts with intelligent caching and batching.
        
        Args:
            texts: Single string or list of strings to embed
            
        Returns:
            Single numpy array for string input, list of arrays for list input
        """
        single = isinstance(texts, str)
        items = [texts] if single else list(texts)

        # Resolve from cache and identify missing items
        vectors = [None] * len(items)
        missing: List[tuple[int, str]] = []
        
        for i, text in enumerate(items):
            cached_vec = self._get_from_cache(text)
            if cached_vec is not None:
                vectors[i] = cached_vec
            else:
                missing.append((i, text))

        # Compute missing embeddings in batches
        for start in range(0, len(missing), self.batch_size):
            chunk = missing[start : start + self.batch_size]
            if not chunk:
                continue
            
            indices, texts_batch = zip(*chunk)
            embeddings = self._embed_batch(list(texts_batch))
            
            for idx, embedding in zip(indices, embeddings):
                vectors[idx] = embedding
                self._store_in_cache(items[idx], embedding)

        # All vectors should be filled at this point
        result: List[np.ndarray] = vectors  # type: ignore
        return result[0] if single else result

    def embed_batch(self, texts: List[str], batch_size: Optional[int] = None) -> List[np.ndarray]:
        """
        Embed a batch of texts with optional batch size override.
        
        Args:
            texts: List of texts to embed
            batch_size: Optional batch size override
            
        Returns:
            List of embedding arrays
        """
        if not texts:
            return []
        
        effective_batch_size = batch_size or self.batch_size
        result = []
        
        for start in range(0, len(texts), effective_batch_size):
            chunk = texts[start:start + effective_batch_size]
            chunk_embeddings = self._embed_batch(chunk)
            result.extend(chunk_embeddings)
        
        return result

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return safe_cosine_similarity(a, b)

    def cosine_many(self, query_vec: np.ndarray, doc_vecs: Iterable[np.ndarray]) -> np.ndarray:
        """
        Calculate cosine similarities between a query vector and multiple document vectors.
        
        Optimized vectorized implementation for bulk similarity calculations.
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
        cache_key = create_cache_key(self._model, text)
        return self.cache.get(cache_key)

    def _store_in_cache(self, text: str, vec: np.ndarray) -> None:
        """Store embedding in cache."""
        cache_key = create_cache_key(self._model, text)
        self.cache.set(cache_key, vec)

    def _embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Perform actual embedding computation via HuggingFace API.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding arrays
        """
        # Single API call for the whole batch
        with self._lock:
            api_output = self._client.feature_extraction(texts, model=self._model)

        # Normalize HuggingFace API output format
        if api_output is not None and len(api_output) > 0 and isinstance(api_output[0], (float, int)):
            # Single embedding returned as flat list
            api_output = [api_output]

        result = []
        for vec in api_output:
            arr = np.asarray(vec, dtype=self.dtype)
            if self.normalize:
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
            result.append(arr)
        
        return result