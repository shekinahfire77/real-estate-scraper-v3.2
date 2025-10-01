"""Test retry and circuit breaker functionality"""

import pytest
import time
from unittest.mock import Mock, patch

from src.scrapers.retry_handler import (
    CircuitBreaker,
    CircuitState,
    DomainCircuitBreaker,
    ExponentialBackoff,
    retry_with_backoff,
    AdaptiveRateLimiter
)


class TestCircuitBreaker:
    """Test CircuitBreaker class"""
    
    def test_circuit_breaker_opens(self):
        """Test circuit breaker opens after failures"""
        
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1
        )
        
        # Mock function that always fails
        def failing_func():
            raise Exception("Test failure")
        
        # Fail 3 times
        for _ in range(3):
            with pytest.raises(Exception):
                breaker.call(failing_func)
        
        # Circuit should be open
        assert breaker.state == CircuitState.OPEN
        
        # Next call should fail immediately
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            breaker.call(failing_func)
    
    def test_circuit_breaker_recovers(self):
        """Test circuit breaker recovery"""
        
        breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=0.1  # 100ms
        )
        
        def sometimes_failing_func(should_fail=True):
            if should_fail:
                raise Exception("Test failure")
            return "Success"
        
        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                breaker.call(sometimes_failing_func, should_fail=True)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for recovery timeout
        time.sleep(0.15)
        
        # Should enter half-open state and succeed
        result = breaker.call(sometimes_failing_func, should_fail=False)
        assert result == "Success"
        assert breaker.state == CircuitState.CLOSED


class TestExponentialBackoff:
    """Test ExponentialBackoff class"""
    
    def test_exponential_calculation(self):
        """Test exponential delay calculation"""
        
        backoff = ExponentialBackoff(
            base_delay=1.0,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False
        )
        
        assert backoff.get_delay(0) == 0
        assert backoff.get_delay(1) == 1.0  # 1 * 2^0
        assert backoff.get_delay(2) == 2.0  # 1 * 2^1
        assert backoff.get_delay(3) == 4.0  # 1 * 2^2
        assert backoff.get_delay(4) == 8.0  # 1 * 2^3
        assert backoff.get_delay(5) == 10.0  # Capped at max_delay
    
    def test_jitter(self):
        """Test jitter adds randomization"""
        
        backoff = ExponentialBackoff(
            base_delay=1.0,
            jitter=True
        )
        
        delays = [backoff.get_delay(2) for _ in range(10)]
        
        # With jitter, delays should vary
        assert len(set(delays)) > 1
        
        # All should be within expected range (50%-150% of 2.0)
        for delay in delays:
            assert 1.0 <= delay <= 3.0


class TestRetryDecorator:
    """Test retry_with_backoff decorator"""
    
    def test_retry_success_after_failures(self):
        """Test function succeeds after retries"""
        
        attempt_count = {'count': 0}
        
        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01  # Short delay for testing
        )
        def sometimes_failing():
            attempt_count['count'] += 1
            if attempt_count['count'] < 3:
                raise ValueError("Test failure")
            return "Success"
        
        result = sometimes_failing()
        
        assert result == "Success"
        assert attempt_count['count'] == 3
    
    def test_retry_max_attempts_exceeded(self):
        """Test function fails after max attempts"""
        
        @retry_with_backoff(
            max_attempts=2,
            base_delay=0.01
        )
        def always_failing():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError, match="Always fails"):
            always_failing()


class TestAdaptiveRateLimiter:
    """Test AdaptiveRateLimiter class"""
    
    def test_rate_limiting(self):
        """Test rate limiting enforces delays"""
        
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0  # 10 requests per second
        )
        
        start_time = time.time()
        
        # Make 3 requests
        for _ in range(3):
            limiter.wait_if_needed()
        
        elapsed = time.time() - start_time
        
        # Should take at least 0.2 seconds (3 requests at 10/sec)
        assert elapsed >= 0.19  # Allow small margin
    
    def test_rate_adjustment(self):
        """Test rate adjusts based on response"""
        
        limiter = AdaptiveRateLimiter(
            initial_rate=10.0,
            adjustment_factor=0.5  # 50% adjustment
        )
        
        initial_rate = limiter.get_current_rate()
        
        # Record slow response
        limiter.record_response(6.0, success=True)
        
        # Rate should decrease
        assert limiter.get_current_rate() < initial_rate
        
        # Record multiple fast responses
        for _ in range(10):
            limiter.record_response(0.5, success=True)
        
        # Rate should increase
        assert limiter.get_current_rate() > 5.0
