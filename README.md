# Rate Limiter

A Python decorator-based rate limiter using the sliding window algorithm.

Made by Dan Foster

## Features

- Simple decorator-based API rate limiting
- Sliding window algorithm for strict rate limiting (exactly N calls allowed per time period)
- Per-key rate limiting support (e.g., per user ID)
- Auto-retry with configurable max retries
- Thread-safe implementation
- Zero external dependencies (Python standard library only)

## Installation

```bash
pip install rate-limiter-df
```

For development:

```bash
pip install -e ".[dev]"
```

## Usage

### Basic Rate Limiting

```python
from rate_limiter_df import RateLimiter, RateLimitExceeded

@RateLimiter(calls=10, period=60)  # 10 calls per 60 seconds
def my_api_call():
    return "Success"

try:
    result = my_api_call()
except RateLimitExceeded as e:
    print(f"Rate limit exceeded: {e}")
```

### Per-Key Rate Limiting

Rate limit different keys (e.g., user IDs) independently:

```python
def get_user_id(user_id, **kwargs):
    return user_id

@RateLimiter(calls=5, period=60, per_key=get_user_id)
def process_user_request(user_id, data):
    # Each user gets their own rate limit
    return f"Processed request for user {user_id}"

# User 1 can make 5 calls
process_user_request(user_id=1, data="...")
process_user_request(user_id=1, data="...")

# User 2 has their own separate rate limit
process_user_request(user_id=2, data="...")
```

### Auto-Retry

Automatically wait and retry when rate limited:

```python
@RateLimiter(calls=2, period=1.0, auto_retry=True, max_retries=3)
def resilient_call():
    return "Success"

# If rate limited, the decorator will sleep and retry up to 3 times
# before raising RateLimitExceeded
result = resilient_call()
```

## How It Works

The rate limiter uses the **sliding window algorithm**:

- Each function (or key) tracks timestamps of recent calls
- When a call is made, timestamps older than the window period are discarded
- If the number of calls within the window is under the limit, the call proceeds
- If the limit has been reached, a `RateLimitExceeded` exception is raised with a retry time
- With `auto_retry` enabled, the decorator sleeps for the wait time and retries automatically

## API Reference

### `RateLimiter(calls, period, per_key=None, auto_retry=False, max_retries=3)`

Creates a rate limiter decorator.

**Parameters:**
- `calls` (int): Maximum number of calls allowed per period. Default: `1`
- `period` (float): Time period in seconds. Default: `60.0`
- `per_key` (callable, optional): Function to extract a key from function arguments for per-key rate limiting
- `auto_retry` (bool): If `True`, automatically wait and retry when rate limited. Default: `False`
- `max_retries` (int): Maximum number of retry attempts when `auto_retry` is enabled. Default: `3`

**Returns:**
- A decorator that can be applied to functions

### `RateLimitExceeded`

Exception raised when the rate limit is exceeded. The exception message includes the wait time before a retry will succeed.

## License

MIT License - see LICENSE.txt for details.
