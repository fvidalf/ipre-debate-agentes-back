from collections import deque
from typing import Deque, List, Optional

class FixedMemory:
    def __init__(self, max_size: int = 3):
        self._queue: Deque[str] = deque(maxlen=max_size)

    def enqueue(self, item: str) -> None:
        """Add a new entry to memory."""
        self._queue.append(item)

    def to_list(self) -> List[str]:
        """Return memory as a list (oldest to newest)."""
        return list(self._queue)

    def to_text(self, limit: Optional[int] = None) -> str:
        """
        Return memory contents joined as text.
        If `limit` is provided, only include the most recent N items.
        """
        if limit is not None:
            return "\n".join(list(self._queue)[-limit:])
        return "\n".join(self._queue)

    def clear(self) -> None:
        """Completely clear the memory contents."""
        self._queue.clear()

    def __len__(self) -> int:
        return len(self._queue)

    def __repr__(self) -> str:
        return f"FixedMemory({list(self._queue)})"
