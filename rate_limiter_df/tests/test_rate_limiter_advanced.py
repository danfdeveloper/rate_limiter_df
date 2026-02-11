# test_rate_limiter_advanced.py

"""
Advanced tests for the rate limiter.
"""

import time
import threading
import pytest
from rate_limiter_df import RateLimiter, RateLimitExceeded


class TestSlidingWindowBehavior:
    """Verify the sliding window correctly tracks and expires calls."""

    def test_calls_allowed_after_oldest_expires(self):
        """After the oldest call slides out of the window, a new call should be allowed."""
        @RateLimiter(calls=2, period=0.5)
        def func():
            return True

        func()
        func()

        with pytest.raises(RateLimitExceeded):
            func()

        # Wait just long enough for the first call to expire
        time.sleep(0.55)
        assert func() is True

    def test_strict_count_within_window(self):
        """Calls spaced within the window must not exceed the limit."""
        @RateLimiter(calls=3, period=2.0)
        def func():
            return True

        # Space calls 0.3s apart — all within the 2s window
        for _ in range(3):
            func()
            time.sleep(0.3)

        # 4th call is still within the window; should be blocked
        with pytest.raises(RateLimitExceeded):
            func()

    def test_window_slides_incrementally(self):
        """As individual calls expire, slots open one at a time."""
        @RateLimiter(calls=3, period=0.5)
        def func():
            return True

        func()                  # t=0
        time.sleep(0.2)
        func()                  # t=0.2
        time.sleep(0.2)
        func()                  # t=0.4

        with pytest.raises(RateLimitExceeded):
            func()

        # Wait for first call to expire (t≈0.55), one slot opens
        time.sleep(0.15)
        func()

        # Still only one slot freed, so next should fail
        with pytest.raises(RateLimitExceeded):
            func()

    def test_full_reset_after_period(self):
        """After a full period of inactivity, all slots are available again."""
        @RateLimiter(calls=5, period=0.5)
        def func():
            return True

        for _ in range(5):
            func()

        time.sleep(0.6)

        # All 5 slots should be available again
        for _ in range(5):
            func()


class TestWaitTimeAccuracy:
    """Verify the reported wait time is useful and accurate."""

    def test_wait_time_is_positive(self):
        @RateLimiter(calls=1, period=1.0)
        def func():
            pass

        func()
        with pytest.raises(RateLimitExceeded, match=r"Try again in \d+\.\d+ seconds"):
            func()

    def test_waiting_the_reported_time_allows_retry(self):
        """Sleeping for the reported wait time should unblock the next call."""
        import re

        @RateLimiter(calls=1, period=0.5)
        def func():
            return True

        func()

        try:
            func()
        except RateLimitExceeded as e:
            match = re.search(r"(\d+\.\d+) seconds", str(e))
            wait = float(match.group(1))
            time.sleep(wait + 0.05)  # small buffer

        assert func() is True


class TestThreadSafety:
    """Verify correct behavior under concurrent access."""

    def test_concurrent_calls_respect_limit(self):
        """Multiple threads should not exceed the call limit."""
        limiter = RateLimiter(calls=5, period=2.0)
        successes = []
        failures = []
        lock = threading.Lock()

        @limiter
        def func():
            return True

        def worker():
            try:
                func()
                with lock:
                    successes.append(1)
            except RateLimitExceeded:
                with lock:
                    failures.append(1)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes) == 5
        assert len(failures) == 15

    def test_per_key_thread_isolation(self):
        """Per-key limits should be independent across threads using different keys."""
        successes = {"a": [], "b": []}
        lock = threading.Lock()

        @RateLimiter(calls=2, period=2.0, per_key=lambda key: key)
        def func(key):
            return key

        def worker(key):
            try:
                func(key)
                with lock:
                    successes[key].append(1)
            except RateLimitExceeded:
                pass

        threads = []
        for key in ("a", "b"):
            for _ in range(5):
                threads.append(threading.Thread(target=worker, args=(key,)))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes["a"]) == 2
        assert len(successes["b"]) == 2


class TestDecoratorBehavior:
    """Verify the decorator preserves function metadata and return values."""

    def test_preserves_function_name(self):
        @RateLimiter(calls=1, period=1.0)
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_preserves_docstring(self):
        @RateLimiter(calls=1, period=1.0)
        def my_function():
            """My docstring."""
            pass

        assert my_function.__doc__ == "My docstring."

    def test_passes_args_and_kwargs(self):
        @RateLimiter(calls=5, period=1.0)
        def add(a, b, extra=0):
            return a + b + extra

        assert add(1, 2) == 3
        assert add(1, 2, extra=10) == 13

    def test_propagates_exceptions(self):
        @RateLimiter(calls=5, period=1.0)
        def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError, match="boom"):
            fail()

    def test_failed_call_still_counts(self):
        """A call that raises should still consume a slot."""
        @RateLimiter(calls=2, period=1.0)
        def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            fail()
        with pytest.raises(ValueError):
            fail()
        with pytest.raises(RateLimitExceeded):
            fail()


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_single_call_limit(self):
        @RateLimiter(calls=1, period=0.5)
        def func():
            return True

        assert func() is True
        with pytest.raises(RateLimitExceeded):
            func()

    def test_large_call_limit(self):
        @RateLimiter(calls=100, period=1.0)
        def func():
            return True

        for _ in range(100):
            func()

        with pytest.raises(RateLimitExceeded):
            func()

    def test_per_key_with_none_key(self):
        """A per_key function that returns None should still work."""
        @RateLimiter(calls=1, period=1.0, per_key=lambda: None)
        def func():
            return True

        assert func() is True
        with pytest.raises(RateLimitExceeded):
            func()

    def test_per_key_with_varying_types(self):
        """Different key types should each get their own bucket."""
        @RateLimiter(calls=1, period=1.0, per_key=lambda k: k)
        def func(k):
            return k

        assert func(1) == 1
        assert func("a") == "a"
        assert func((1, 2)) == (1, 2)

        # Each key is now exhausted
        with pytest.raises(RateLimitExceeded):
            func(1)
        with pytest.raises(RateLimitExceeded):
            func("a")
        with pytest.raises(RateLimitExceeded):
            func((1, 2))


class TestAutoRetry:
    """Verify auto-retry behavior."""

    def test_auto_retry_succeeds_after_wait(self):
        """With auto_retry enabled, a rate-limited call should wait and succeed."""
        call_count = [0]

        @RateLimiter(calls=1, period=0.3, auto_retry=True, max_retries=3)
        def func():
            call_count[0] += 1
            return True

        assert func() is True
        # Second call should auto-retry after the window expires
        assert func() is True
        assert call_count[0] == 2

    def test_auto_retry_raises_with_zero_max_retries(self):
        """With max_retries=0, auto_retry should raise immediately."""
        @RateLimiter(calls=1, period=1.0, auto_retry=True, max_retries=0)
        def func():
            return True

        func()
        with pytest.raises(RateLimitExceeded):
            func()

    def test_auto_retry_disabled_by_default(self):
        """Without auto_retry, rate-limited calls should raise immediately."""
        @RateLimiter(calls=1, period=1.0)
        def func():
            return True

        func()
        start = time.time()
        with pytest.raises(RateLimitExceeded):
            func()
        elapsed = time.time() - start
        # Should raise almost immediately, not wait
        assert elapsed < 0.1

    def test_auto_retry_preserves_return_value(self):
        """Auto-retried calls should return the correct value."""
        @RateLimiter(calls=1, period=0.3, auto_retry=True, max_retries=3)
        def func():
            return "hello"

        assert func() == "hello"
        assert func() == "hello"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
