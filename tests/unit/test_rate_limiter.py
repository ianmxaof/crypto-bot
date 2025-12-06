"""Unit tests for rate limiter."""

import pytest
import asyncio
from core.rate_limiter import RateLimiter, PerExchangeRateLimiter


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting."""
        limiter = RateLimiter(calls_per_second=2.0)
        
        start = asyncio.get_event_loop().time()
        for _ in range(3):
            await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        
        # Should take at least 1 second for 3 calls at 2/sec
        assert elapsed >= 0.9
        
    @pytest.mark.asyncio
    async def test_rate_limiter_context_manager(self):
        """Test rate limiter as context manager."""
        limiter = RateLimiter(calls_per_second=10.0)
        
        async with limiter:
            # Should acquire token
            pass
        
        # Should be able to acquire again quickly
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start
        assert elapsed < 0.1


class TestPerExchangeRateLimiter:
    """Test per-exchange rate limiter."""
    
    def test_get_limiter(self):
        """Test getting limiter for exchange."""
        manager = PerExchangeRateLimiter(default_calls_per_second=5.0)
        limiter = manager.get_limiter("bybit")
        
        assert limiter is not None
        assert limiter.calls_per_second == 5.0
        
    def test_custom_rate(self):
        """Test custom rate for exchange."""
        manager = PerExchangeRateLimiter(default_calls_per_second=5.0)
        limiter = manager.get_limiter("binance", calls_per_second=10.0)
        
        assert limiter.calls_per_second == 10.0

