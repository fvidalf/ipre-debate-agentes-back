from collections import deque
from typing import Deque, List

class FixedMemory:
    def __init__(self, max_size: int = 3):
        self._queue: Deque[str] = deque(maxlen=max_size)

    def enqueue(self, item: str) -> None:
        self._queue.append(item)

    def to_list(self) -> List[str]:
        return list(self._queue)

    def __len__(self) -> int:
        return len(self._queue)

    def __repr__(self) -> str:
        return f"FixedMemory({list(self._queue)})"

    def to_text(self) -> str:
        return "\n".join(self._queue)
