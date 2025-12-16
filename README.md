# Rate Limiter

A Python decorator-based rate limiter using the token bucket algorithm.

Made by Dan Foster

## Features

- Simple decorator-based API rate limiting
- Token bucket algorithm for smooth rate limiting (both short bursts and constant usage are supported)
- Per-key rate limiting support (e.g., per user ID)
- Thread-safe implementation
- Zero external dependencies (Python standard library only)

## Installation

pip install -e .

### Basic Rate Limiting

```python
from rate_limiter_df import RateLimiter, RateLimitExceeded

@RateLimiter(calls=10, period=60)  # 10 calls per 60 seconds
def my_api_call():
    # Your function code goes here
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

### Advanced Example

```python
from rate_limiter_df import RateLimiter, RateLimitExceeded
import time

@RateLimiter(calls=3, period=5.0)
def expensive_operation():
    print("Performing expensive operation...")
    return "Done"

# Make multiple calls
for i in range(5):
    try:
        result = expensive_operation()
        print(f"Call {i+1}: {result}")
    except RateLimitExceeded as e:
        print(f"Call {i+1}: {e}")
        time.sleep(1)  # Wait before retrying
```

## How It Works

The rate limiter uses the **token bucket algorithm**:

- Each function (or key) has a bucket that holds tokens
- Tokens are consumed when the function is called
- Tokens refill over time at a constant rate
- If no tokens are available, a `RateLimitExceeded` exception is raised

## API Reference

### `RateLimiter(calls, period, per_key=None)`

Creates a rate limiter decorator.

**Parameters:**
- `calls` (int): Maximum number of calls allowed
- `period` (float): Time period in seconds
- `per_key` (callable, optional): Function to extract a key from function arguments for per-key rate limiting

**Returns:**
- A decorator that can be applied to functions

### `RateLimitExceeded`

Exception raised when the rate limit is exceeded. The exception message includes information about when to retry.

## License

MIT License - see LICENSE.txt for details.
