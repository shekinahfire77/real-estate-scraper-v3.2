"""Advanced retry and circuit breaker implementation"""

import time
import logging
import random
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta
from functools import wraps
from collections import defaultdict, deque
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures exceeded threshold, blocking calls
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: type = Exception):
        """
        Initialize circuit breaker
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type to catch
        """
        
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker is OPEN for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try again"""
        
        return (self.last_failure_time and 
                time.time() - self.last_failure_time >= self.recovery_timeout)
    
    def _on_success(self):
        """Handle successful call"""
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def reset(self):
        """Manually reset the circuit breaker"""
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED


class DomainCircuitBreaker:
    """Circuit breaker per domain"""
    
    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60):
        """
        Initialize domain-specific circuit breakers
        
        Args:
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before retry
        """
        
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.breakers = defaultdict(
            lambda: CircuitBreaker(failure_threshold, recovery_timeout)
        )
    
    def get_breaker(self, domain: str) -> CircuitBreaker:
        """Get circuit breaker for domain"""
        return self.breakers[domain]
    
    def is_open(self, domain: str) -> bool:
        """Check if circuit is open for domain"""
        return self.breakers[domain].state == CircuitState.OPEN
    
    def reset_domain(self, domain: str):
        """Reset circuit breaker for domain"""
        if domain in self.breakers:
            self.breakers[domain].reset()
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all domains"""
        
        stats = {}
        for domain, breaker in self.breakers.items():
            stats[domain] = {
                'state': breaker.state.value,
                'failure_count': breaker.failure_count,
                'last_failure': breaker.last_failure_time
            }
        return stats


class ExponentialBackoff:
    """Exponential backoff with jitter"""
    
    def __init__(self,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        """
        Initialize exponential backoff
        
        Args:
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential calculation
            jitter: Add randomization to prevent thundering herd
        """
        
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        
        if attempt <= 0:
            return 0
        
        # Calculate exponential delay
        delay = min(
            self.base_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        
        # Add jitter
        if self.jitter:
            delay = delay * (0.5 + random.random())  # 50% to 150% of calculated
        
        return delay


def retry_with_backoff(max_attempts: int = 3,
                      base_delay: float = 1.0,
                      max_delay: float = 60.0,
                      exceptions: tuple = (Exception,)):
    """Decorator for retry with exponential backoff"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            backoff = ExponentialBackoff(
                base_delay=base_delay,
                max_delay=max_delay
            )
            
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    delay = backoff.get_delay(attempt)
                    logger.warning(
                        f"{func.__name__} attempt {attempt} failed, "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class AdaptiveRateLimiter:
    """Adaptive rate limiting based on response times"""
    
    def __init__(self,
                 initial_rate: float = 10.0,
                 min_rate: float = 1.0,
                 max_rate: float = 100.0,
                 adjustment_factor: float = 0.1):
        """
        Initialize adaptive rate limiter
        
        Args:
            initial_rate: Starting requests per second
            min_rate: Minimum requests per second
            max_rate: Maximum requests per second
            adjustment_factor: How much to adjust rate (0.1 = 10%)
        """
        
        self.current_rate = initial_rate
        self.min_rate = min_rate
        self.max_rate = max_rate
        self.adjustment_factor = adjustment_factor
        
        self.last_request_time = 0
        self.response_times = deque(maxlen=10)
    
    def wait_if_needed(self):
        """Wait if necessary to maintain rate limit"""
        
        now = time.time()
        min_interval = 1.0 / self.current_rate
        
        time_since_last = now - self.last_request_time
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def record_response(self, response_time: float, success: bool):
        """Record response and adjust rate"""
        
        self.response_times.append(response_time)
        
        if not success:
            # Decrease rate on failure
            self.decrease_rate()
        elif response_time > 5.0:  # Slow response
            self.decrease_rate()
        elif response_time < 1.0 and len(self.response_times) == 10:
            # All recent responses were fast
            if all(rt < 1.0 for rt in self.response_times):
                self.increase_rate()
    
    def increase_rate(self):
        """Increase request rate"""
        
        new_rate = self.current_rate * (1 + self.adjustment_factor)
        self.current_rate = min(new_rate, self.max_rate)
        
        logger.debug(f"Rate increased to {self.current_rate:.2f} req/s")
    
    def decrease_rate(self):
        """Decrease request rate"""
        
        new_rate = self.current_rate * (1 - self.adjustment_factor)
        self.current_rate = max(new_rate, self.min_rate)
        
        logger.debug(f"Rate decreased to {self.current_rate:.2f} req/s")
    
    def get_current_rate(self) -> float:
        """Get current request rate"""
        return self.current_rate
