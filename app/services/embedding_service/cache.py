"""
Caching implementations for embedding storage.

Provides various caching strategies to avoid redundant embedding computations.
"""

import threading
import hashlib
from collections import OrderedDict
from typing import Optional, Tuple
import numpy as np

from .base import EmbeddingCache


class InMemoryLRUCache(EmbeddingCache):
    """
    Fast, thread-safe LRU cache with optional TTL (time-to-live).
    
    Features:
    - LRU eviction when capacity is exceeded
    - Optional TTL for cache entry expiration
    - Thread-safe operations with RLock
    - Stores numpy arrays efficiently
    - Monotonic logical clock for TTL (avoids time.time() overhead)
    """
    
    def __init__(self, capacity: int = 10000, ttl_seconds: Optional[int] = None):
        """
        Initialize LRU cache.
        
        Args:
            capacity: Maximum number of items to store
            ttl_seconds: Optional time-to-live for cache entries
        """
        self.capacity = capacity
        self.ttl = ttl_seconds
        self._lock = threading.RLock()
        self._store: OrderedDict[str, Tuple[np.ndarray, float]] = OrderedDict()

        # Use a monotonic counter for simple "age" tracking
        # This avoids importing time and is more predictable for testing
        self._tick = 0.0
        self._tick_step = 1.0

    def _now(self) -> float:
        """Get current logical timestamp."""
        self._tick += self._tick_step
        return self._tick

    def _expired(self, inserted_at: float) -> bool:
        """Check if a cache entry has expired."""
        if self.ttl is None:
            return False
        return (self._tick - inserted_at) > self.ttl

    def get(self, key: str) -> Optional[np.ndarray]:
        """
        Retrieve embedding from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached embedding array or None if not found/expired
        """
        with self._lock:
            if key not in self._store:
                return None
            
            arr, timestamp = self._store.pop(key)
            
            # Check expiration
            if self._expired(timestamp):
                return None
            
            # Move to end (mark as recently used)
            self._store[key] = (arr, timestamp)
            return arr

    def set(self, key: str, value: np.ndarray) -> None:
        """
        Store embedding in cache.
        
        Args:
            key: Cache key
            value: Embedding array to store
        """
        with self._lock:
            # Remove if already exists
            if key in self._store:
                self._store.pop(key)
            
            # Add new entry
            self._store[key] = (value, self._now())
            
            # Evict oldest entries if over capacity
            while len(self._store) > self.capacity:
                self._store.popitem(last=False)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()

    def size(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._store)

    def stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._store),
                "capacity": self.capacity,
                "ttl_seconds": self.ttl,
                "utilization": len(self._store) / self.capacity if self.capacity > 0 else 0
            }


class NoOpCache(EmbeddingCache):
    """Cache implementation that doesn't cache anything."""
    
    def get(self, key: str) -> Optional[np.ndarray]:
        return None
    
    def set(self, key: str, value: np.ndarray) -> None:
        pass


def create_cache_key(model_name: str, text: str) -> str:
    """
    Create a deterministic cache key for a model and text combination.
    
    Args:
        model_name: Name/identifier of the embedding model
        text: Input text
        
    Returns:
        Hex-encoded SHA-256 hash
    """
    hasher = hashlib.sha256()
    hasher.update(model_name.encode("utf-8"))
    hasher.update(b"\x00")  # Separator
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()