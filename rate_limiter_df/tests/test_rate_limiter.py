# test_rate_limiter.py

"""
Tests for the rate limiter.
"""

import time
import pytest
from rate_limiter_df import RateLimiter, RateLimitExceeded


def test_basic_rate_limiting():
    """Test basic rate limiting functionality."""
    call_count = [0]
    
    @RateLimiter(calls=2, period=1.0)
    def test_func():
        call_count[0] += 1
        return call_count[0]
    
    # First two calls should succeed
    assert test_func() == 1
    assert test_func() == 2
    
    # Third call should fail
    with pytest.raises(RateLimitExceeded):
        test_func()
    
    # After waiting, should work again
    time.sleep(1.1)
    assert test_func() == 3


def test_per_key_rate_limiting():
    """Test rate limiting per key."""
    call_counts = {}
    
    def get_user_id(user_id, **kwargs):
        return user_id
    
    @RateLimiter(calls=2, period=1.0, per_key=get_user_id)
    def test_func(user_id):
        if user_id not in call_counts:
            call_counts[user_id] = 0
        call_counts[user_id] += 1
        return call_counts[user_id]
    
    # User 1 can make 2 calls
    assert test_func(user_id=1) == 1
    assert test_func(user_id=1) == 2
    
    # User 1 is rate limited
    with pytest.raises(RateLimitExceeded):
        test_func(user_id=1)
    
    # User 2 can still make calls (different key)
    assert test_func(user_id=2) == 1
    assert test_func(user_id=2) == 2
    
    # User 2 is rate limited
    with pytest.raises(RateLimitExceeded):
        test_func(user_id=2)


def test_token_refill():
    """Test that tokens refill over time."""
    call_count = [0]
    
    @RateLimiter(calls=2, period=0.5)
    def test_func():
        call_count[0] += 1
        return call_count[0]
    
    # Use up all tokens
    test_func()
    test_func()
    
    # Should be rate limited
    with pytest.raises(RateLimitExceeded):
        test_func()
    
    # Wait for tokens to refill
    time.sleep(0.6)
    
    # Should work again
    assert test_func() == 3


def test_multiple_functions():
    """Test that different functions have separate rate limits."""
    count1 = [0]
    count2 = [0]
    
    @RateLimiter(calls=1, period=1.0)
    def func1():
        count1[0] += 1
        return count1[0]
    
    @RateLimiter(calls=1, period=1.0)
    def func2():
        count2[0] += 1
        return count2[0]
    
    # Both should work independently
    assert func1() == 1
    assert func2() == 1
    
    # Both should be rate limited
    with pytest.raises(RateLimitExceeded):
        func1()
    with pytest.raises(RateLimitExceeded):
        func2()


def test_rate_limit_exception_message():
    """Test that RateLimitExceeded exception has a message."""
    @RateLimiter(calls=1, period=1.0)
    def test_func():
        pass
    
    test_func()
    
    with pytest.raises(RateLimitExceeded) as exc_info:
        test_func()
    
    assert "Rate limit exceeded" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

