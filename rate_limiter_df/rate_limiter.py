import time
import functools
from collections import deque
from typing import Callable, Optional, Dict, Any
from threading import Lock

class RateLimiter:
    """
    A rate limiter that uses a sliding window algorithm.

    Used via decorators to limit function call rates.

    Example:
        @RateLimiter(calls=1, period=60)  # 1 call per 60 seconds
        def my_function():
            pass
    """

    def __init__(self, calls: int = 1, period: float = 60.0, per_key: Optional[Callable[..., Any]] = None,
                 auto_retry: bool = False, max_retries: int = 3):
        """
        Initialize a rate limiter.

        Args:
            calls: Maximum number of calls allowed per period
            period: Length of time (in seconds)
            per_key: Optional function to extract a key from function arguments
                     for per-key rate limiting (e.g., per user ID)
            auto_retry: If True, automatically wait and retry when rate limited
            max_retries: Maximum number of retry attempts when auto_retry is enabled
        """
        self.calls = calls
        self.period = period
        self.per_key = per_key
        self.auto_retry = auto_retry
        self.max_retries = max_retries

        # Sliding window: {key: deque of call timestamps}
        self.windows: Dict[Any, deque[float]] = {}
        self.lock = Lock()

    def _get_key(self, *args: Any, **kwargs: Any) -> Any:
        """Extract rate limiting key from function arguments."""
        if self.per_key:
            return self.per_key(*args, **kwargs)
        return None  # Global rate limit

    def _try_acquire_or_wait_time(self, key: Any) -> float | None:
        """
        Try to acquire a call slot. Returns None on success, or the
        wait time in seconds if rate limited.
        """
        with self.lock:
            current_time = time.time()

            if key not in self.windows:
                self.windows[key] = deque()

            window = self.windows[key]

            # Remove timestamps outside the current window
            cutoff = current_time - self.period
            while window and window[0] <= cutoff:
                window.popleft()

            if len(window) < self.calls:
                window.append(current_time)
                return None

            # Rate limited: wait until the oldest call expires
            return window[0] + self.period - current_time

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator implementation.
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = self._get_key(*args, **kwargs)

            for attempt in range(self.max_retries + 1): # One initial try + retries
                wait_time = self._try_acquire_or_wait_time(key)

                if wait_time is None:
                    return func(*args, **kwargs)

                if not self.auto_retry or attempt == self.max_retries:
                    raise RateLimitExceeded(
                        f"Rate limit exceeded! Try again in {wait_time:.2f} seconds."
                    )

                time.sleep(wait_time)

        return wrapper

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass

rate_limiter = RateLimiter
