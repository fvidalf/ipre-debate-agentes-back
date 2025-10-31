"""
ONNX-based embedding provider for local inference.

Wraps the existing ONNX implementation with the new provider interface
and adds caching support for improved performance.
"""

import os
from typing import List, Optional, Iterable
import numpy as np

from ..base import EmbeddingProvider, TextInput, ArrayOrList, safe_cosine_similarity
from ..cache import EmbeddingCache, NoOpCache, create_cache_key


class ONNXProvider(EmbeddingProvider):
    """
    ONNX-optimized sentence encoder for lightweight local inference.
    
    Features:
    - Local inference with no external API dependencies
    - Intelligent caching to avoid redundant computations
    - Efficient mean pooling for sentence embeddings
    - Thread-safe operations
    """

    def __init__(
        self,
        model_dir: str = "./onnx-model",
        cache: Optional[EmbeddingCache] = None,
        normalize: bool = True,
        dtype: np.dtype = np.float32
    ):
        """
        Initialize ONNX embedding provider.
        
        Args:
            model_dir: Directory containing ONNX model files
            cache: Optional cache implementation
            normalize: Whether to L2-normalize embeddings
            dtype: NumPy data type for embeddings
        """
        try:
            import onnxruntime as ort
            from transformers import AutoTokenizer
        except ImportError:
            raise ImportError(
                "ONNX provider requires onnxruntime and transformers. "
                "Install with: pip install onnxruntime transformers"
            )
        
        self.model_dir = model_dir
        self.cache = cache or NoOpCache()
        self.normalize = normalize
        self.dtype = dtype
        
        # Initialize tokenizer and ONNX session
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.session = ort.InferenceSession(
            os.path.join(model_dir, "model.onnx"),
            providers=["CPUExecutionProvider"]
        )

    @property
    def supports_batching(self) -> bool:
        return False  # ONNX provider doesn't implement special batching logic

    @property 
    def model_name(self) -> str:
        return f"onnx:{self.model_dir}"

    def embed(self, texts: TextInput) -> ArrayOrList:
        """
        Embed one or many texts using local ONNX inference.
        
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
        Perform ONNX inference on a batch of texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding arrays
        """
        if not texts:
            return []

        # Tokenize all texts
        encoded = self.tokenizer(
            texts, 
            return_tensors="np", 
            padding=True, 
            truncation=True, 
            max_length=256
        )
        
        # Prepare inputs for ONNX model
        input_feed = {}
        for input_node in self.session.get_inputs():
            input_name = input_node.name
            if input_name in encoded:
                input_feed[input_name] = encoded[input_name]
        
        # Run ONNX inference
        outputs = self.session.run(None, input_feed)[0]
        
        # Apply mean pooling using attention mask
        attention_mask = encoded["attention_mask"]
        
        # Mean pooling: sum embeddings and divide by attention mask sum
        masked_embeddings = outputs * np.expand_dims(attention_mask, axis=-1)
        summed = np.sum(masked_embeddings, axis=1)
        counts = np.sum(attention_mask, axis=1, keepdims=True)
        counts = np.maximum(counts, 1)  # Avoid division by zero
        
        mean_pooled = summed / counts
        
        result = []
        for embedding in mean_pooled:
            arr = embedding.astype(self.dtype)
            if self.normalize:
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
            result.append(arr)
        
        return result