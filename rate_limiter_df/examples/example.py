#!/usr/bin/env python3
"""
Example usage of the rate limiter.
"""

from rate_limiter_df import RateLimiter, RateLimitExceeded
import time


def main():
    print("Rate Limiter Examples")
    print("=" * 60)
    
    # Example 1: Basic rate limiting
    print("\n1. Basic Rate Limiting (3 calls per 2 seconds)")
    print("-" * 60)
    
    @RateLimiter(calls=3, period=2.0)
    def api_call():
        return "API call successful"
    
    for i in range(5):
        try:
            result = api_call()
            print(f"  Call {i+1}: {result}")
        except RateLimitExceeded as e:
            print(f"  Call {i+1}: {e}")
        time.sleep(0.3)
    
    # Example 2: Per-user rate limiting
    print("\n2. Per-User Rate Limiting (2 calls per user per 1 second)")
    print("-" * 60)
    
    def get_user_id(user_id, **kwargs):
        return user_id
    
    @RateLimiter(calls=2, period=1.0, per_key=get_user_id)
    def process_request(user_id, data):
        return f"Processed request for user {user_id}: {data}"
    
    # User 1 makes requests
    print("  User 1 requests:")
    for i in range(3):
        try:
            result = process_request(user_id=1, data=f"request_{i+1}")
            print(f"    {result}")
        except RateLimitExceeded as e:
            print(f"    User 1 rate limited: {e}")
        time.sleep(0.2)
    
    # User 2 makes requests (separate rate limit)
    print("\n  User 2 requests:")
    for i in range(3):
        try:
            result = process_request(user_id=2, data=f"request_{i+1}")
            print(f"    {result}")
        except RateLimitExceeded as e:
            print(f"    User 2 rate limited: {e}")
        time.sleep(0.2)
    
    print("\n" + "=" * 60)
    print("Examples completed!")


if __name__ == '__main__':
    main()

