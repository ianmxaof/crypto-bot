"""Inject network latency for chaos testing."""

import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)


class LatencyInjector:
    """Inject latency into async operations."""
    
    def __init__(self, latency_seconds: float = 5.0):
        """Initialize latency injector.
        
        Args:
            latency_seconds: Latency to inject in seconds
        """
        self.latency = latency_seconds
        self.enabled = False
    
    def enable(self):
        """Enable latency injection."""
        self.enabled = True
        logger.warning(f"Latency injection ENABLED: {self.latency}s")
    
    def disable(self):
        """Disable latency injection."""
        self.enabled = False
        logger.info("Latency injection disabled")
    
    async def inject(self, func: Callable, *args, **kwargs) -> Any:
        """Inject latency before calling function.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        """
        if self.enabled:
            logger.debug(f"Injecting {self.latency}s latency before {func.__name__}")
            await asyncio.sleep(self.latency)
        
        return await func(*args, **kwargs)


# Global latency injector instance
_latency_injector: LatencyInjector = None


def get_latency_injector(latency_seconds: float = 5.0) -> LatencyInjector:
    """Get global latency injector instance.
    
    Args:
        latency_seconds: Latency to inject
    
    Returns:
        LatencyInjector instance
    """
    global _latency_injector
    if _latency_injector is None:
        _latency_injector = LatencyInjector(latency_seconds)
    return _latency_injector

