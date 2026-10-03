"""In-process token bucket (TRD TR-API-08: login 5/min per username).

The API is a single uvicorn worker (TR-ARC-03), so in-process state is consistent.
"""

import threading
import time
from collections.abc import Callable


class TokenBucket:
    def __init__(
        self, capacity: int, per_seconds: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self.capacity = capacity
        self.rate = capacity / per_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last refill)

    def allow(self, key: str) -> bool:
        """Take one token for `key`; False when the bucket is empty."""
        now = self._clock()
        with self._lock:
            tokens, last = self._buckets.get(key, (float(self.capacity), now))
            tokens = min(float(self.capacity), tokens + (now - last) * self.rate)
            if tokens < 1.0:
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1.0, now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


login_limiter = TokenBucket(capacity=5, per_seconds=60)
