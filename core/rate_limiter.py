"""Rate limiter for exchange API protection."""

import asyncio
import time
import logging
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for API call throttling."""
    
    def __init__(self, calls_per_second: float = 10.0, burst_size: Optional[int] = None):
        """Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum calls per second
            burst_size: Maximum burst size (defaults to calls_per_second)
        """
        self.calls_per_second = calls_per_second
        self.burst_size = burst_size or int(calls_per_second)
        self._tokens = float(self.burst_size)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()
        
    async def acquire(self, tokens: float = 1.0):
        """Acquire tokens from the bucket, waiting if necessary.
        
        Args:
            tokens: Number of tokens to acquire (default 1)
        """
        async with self._lock:
            self._refill()
            
            while self._tokens < tokens:
                # Calculate wait time
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed / self.calls_per_second
                await asyncio.sleep(wait_time)
                self._refill()
                
            self._tokens -= tokens
            
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(
            self.burst_size,
            self._tokens + elapsed * self.calls_per_second
        )
        self._last_update = now
        
    async def __aenter__(self):
        """Context manager entry."""
        await self.acquire()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class PerExchangeRateLimiter:
    """Rate limiter that manages separate limits per exchange."""
    
    def __init__(self, default_calls_per_second: float = 10.0):
        """Initialize per-exchange rate limiter.
        
        Args:
            default_calls_per_second: Default rate limit for exchanges
        """
        self.default_rate = default_calls_per_second
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = asyncio.Lock()
        
    def get_limiter(self, exchange: str, calls_per_second: Optional[float] = None) -> RateLimiter:
        """Get or create a rate limiter for an exchange.
        
        Args:
            exchange: Exchange name
            calls_per_second: Custom rate limit (uses default if None)
            
        Returns:
            RateLimiter instance for the exchange
        """
        if exchange not in self._limiters:
            rate = calls_per_second or self.default_rate
            self._limiters[exchange] = RateLimiter(rate)
        return self._limiters[exchange]
        
    async def acquire(self, exchange: str, tokens: float = 1.0):
        """Acquire tokens for a specific exchange.
        
        Args:
            exchange: Exchange name
            tokens: Number of tokens to acquire
        """
        limiter = self.get_limiter(exchange)
        await limiter.acquire(tokens)

