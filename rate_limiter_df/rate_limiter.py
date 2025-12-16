import time
import functools
from typing import Callable, Optional, Dict, Any
from threading import Lock

class RateLimiter:
    """
    A rate limiter that uses the token bucket algorithm.
    
    Used via decorators to limit function call rates.
    
    Example:
        @RateLimiter(calls=10, period=60)  # 10 calls per 60 seconds
        def my_function():
            pass
    """
    
    def __init__(self, calls: int = 10, period: float = 60.0, per_key: Optional[Callable[..., Any]] = None):
        """
        Initialize a rate limiter.
        
        Args:
            calls: Maximum number of calls allowed per period
            period: Length of time (in seconds)
            per_key: Optional function to extract a key from function arguments
                     for per-key rate limiting (e.g., per user ID)
        """
        self.calls = calls
        self.period = period
        self.per_key = per_key
        
        # Token bucket: {key: (tokens, last_refill_time)}
        self.buckets: Dict[Any, tuple[float, float]] = {}
        self.lock = Lock()
    
    def _get_key(self, *args: Any, **kwargs: Any) -> Any:
        """Extract rate limiting key from function arguments."""
        if self.per_key:
            return self.per_key(*args, **kwargs)
        return None  # Global rate limit
    
    def _refill_tokens(self, key: Any, current_time: float) -> float:
        """
        Refill tokens based on elapsed time.
        Returns the number of available tokens.
        """
        if key not in self.buckets:
            # Initialize bucket with full tokens
            self.buckets[key] = (self.calls, current_time)
            return self.calls
        
        tokens, last_refill = self.buckets[key]
        elapsed = current_time - last_refill
        
        # Calculate tokens to add based on elapsed time
        tokens_to_add = (elapsed / self.period) * self.calls
        new_tokens = min(self.calls, tokens + tokens_to_add)
        
        # Update bucket
        self.buckets[key] = (new_tokens, current_time)
        return new_tokens
    
    def _acquire_token(self, key: Any) -> bool:
        """
        Try to acquire a token from the bucket.
        Returns True if token was acquired, False otherwise.
        """
        with self.lock:
            current_time = time.time()
            tokens = self._refill_tokens(key, current_time)
            
            if tokens >= 1.0:
                # Consume one token
                tokens -= 1.0
                self.buckets[key] = (tokens, current_time)
                return True
            else:
                return False
    
    def _get_wait_time(self, key: Any) -> float:
        """Calculate how long until next token is available."""
        with self.lock:
            current_time = time.time()
            tokens = self._refill_tokens(key, current_time)
            
            if tokens >= 1.0:
                return 0.0
            
            # Calculate time until next token
            tokens_needed = 1.0 - tokens
            time_needed = (tokens_needed / self.calls) * self.period
            return time_needed
    
    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """
        Decorator implementation.
        """
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = self._get_key(*args, **kwargs)
            
            if not self._acquire_token(key):
                wait_time = self._get_wait_time(key)
                raise RateLimitExceeded(
                    f"Rate limit exceeded! Try again in {wait_time:.2f} seconds."
                )
            
            return func(*args, **kwargs)
        
        return wrapper

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    pass

# Alias for backward compatibility
rate_limiter = RateLimiter
