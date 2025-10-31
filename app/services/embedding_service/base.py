"""
Base interfaces and protocols for the embedding service.

Provides the foundational abstractions that all embedding providers must implement.
"""

from __future__ import annotations
import numpy as np
from abc import ABC, abstractmethod
from typing import Union, List, Optional, Protocol, Iterable


# Type aliases for clarity
ArrayOrList = Union[np.ndarray, List[np.ndarray]]
TextInput = Union[str, List[str]]


class EmbeddingCache(Protocol):
    """Protocol for embedding cache implementations."""
    
    def get(self, key: str) -> Optional[np.ndarray]: 
        """Retrieve embedding from cache."""
        ...
    
    def set(self, key: str, value: np.ndarray) -> None: 
        """Store embedding in cache."""
        ...


class EmbeddingProvider(ABC):
    """
    Abstract base class for all embedding providers.
    
    Defines the contract that all embedding implementations must follow,
    ensuring consistent behavior across different backends (HuggingFace, ONNX, etc.).
    """
    
    @abstractmethod
    def embed(self, texts: TextInput) -> ArrayOrList:
        """
        Embed one or many texts into vector representations.
        
        Args:
            texts: Single string or list of strings to embed
            
        Returns:
            Single numpy array for string input, list of arrays for list input
        """
        pass
    
    @abstractmethod
    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embedding vectors.
        
        Args:
            a: First embedding vector
            b: Second embedding vector
            
        Returns:
            Cosine similarity score between -1 and 1
        """
        pass
    
    @abstractmethod
    def cosine_many(self, query_vec: np.ndarray, doc_vecs: Iterable[np.ndarray]) -> np.ndarray:
        """
        Calculate cosine similarities between a query vector and multiple document vectors.
        
        Args:
            query_vec: Single query embedding vector
            doc_vecs: Iterable of document embedding vectors
            
        Returns:
            Array of cosine similarity scores
        """
        pass
    
    @property
    @abstractmethod
    def supports_batching(self) -> bool:
        """Whether this provider supports efficient batch processing."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier for the underlying model."""
        pass


class BatchableProvider(EmbeddingProvider):
    """
    Extended interface for providers that support batching.
    
    Providers implementing this interface can handle batch operations
    more efficiently than processing items individually.
    """
    
    @property
    def supports_batching(self) -> bool:
        return True
    
    @abstractmethod
    def embed_batch(self, texts: List[str], batch_size: Optional[int] = None) -> List[np.ndarray]:
        """
        Embed a batch of texts with optional batch size control.
        
        Args:
            texts: List of texts to embed
            batch_size: Optional batch size override
            
        Returns:
            List of embedding arrays
        """
        pass


def normalize_vector(vec: np.ndarray) -> np.ndarray:
    """Utility function to L2-normalize a vector."""
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def safe_cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Safe cosine similarity calculation with normalization.
    
    Handles edge cases like zero vectors gracefully.
    """
    a_norm = normalize_vector(a)
    b_norm = normalize_vector(b)
    
    # Ensure inputs are 1D for dot product
    if a_norm.ndim > 1:
        a_norm = a_norm.flatten()
    if b_norm.ndim > 1:
        b_norm = b_norm.flatten()
    
    # Compute dot product and ensure it's a scalar
    dot_product = np.dot(a_norm, b_norm)
    
    # Handle case where dot product might be an array (shouldn't happen with 1D inputs, but safety first)
    if hasattr(dot_product, 'item'):
        return float(dot_product.item())
    else:
        return float(dot_product)