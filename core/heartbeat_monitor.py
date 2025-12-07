"""Heartbeat monitor for system health tracking."""

import asyncio
import logging
from typing import Optional
from datetime import datetime, timezone

from core.event_bus import event_bus
from risk.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    """Monitor system health with periodic heartbeats."""
    
    def __init__(self, 
                 interval_seconds: int = 60,
                 circuit_breaker: Optional[CircuitBreaker] = None,
                 order_gateway: Optional[Any] = None):
        """Initialize heartbeat monitor.
        
        Args:
            interval_seconds: Heartbeat interval in seconds
            circuit_breaker: Optional circuit breaker instance
            order_gateway: Optional order gateway instance
        """
        self.interval = interval_seconds
        self.circuit_breaker = circuit_breaker
        self.order_gateway = order_gateway
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_heartbeat: Optional[datetime] = None
    
    async def start(self):
        """Start heartbeat monitoring."""
        if self._running:
            logger.warning("Heartbeat monitor already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Heartbeat monitor started (interval: {self.interval}s)")
    
    async def stop(self):
        """Stop heartbeat monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Heartbeat monitor stopped")
    
    async def _heartbeat_loop(self):
        """Main heartbeat loop."""
        while self._running:
            try:
                await self._emit_heartbeat()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}", exc_info=True)
                await asyncio.sleep(self.interval)
    
    async def _emit_heartbeat(self):
        """Emit heartbeat event."""
        try:
            # Collect heartbeat data
            heartbeat_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "queue_size": event_bus.get_queue_size(),
                "dropped_events": event_bus.get_dropped_count(),
            }
            
            # Add circuit breaker state if available
            if self.circuit_breaker:
                heartbeat_data["circuit_breaker_state"] = self.circuit_breaker.state.value
                heartbeat_data["in_flight_orders"] = self.circuit_breaker.get_in_flight_count()
            
            # Add order gateway info if available
            if self.order_gateway:
                pending_verification = self.order_gateway.get_pending_verification_orders()
                heartbeat_data["pending_verification_orders"] = len(pending_verification)
            
            # Publish heartbeat
            event_bus.publish("system:heartbeat", heartbeat_data, source="heartbeat_monitor")
            
            self._last_heartbeat = datetime.now(timezone.utc)
            
            logger.debug(
                f"Heartbeat emitted: queue_size={heartbeat_data['queue_size']}, "
                f"circuit_breaker={heartbeat_data.get('circuit_breaker_state', 'N/A')}"
            )
        except Exception as e:
            logger.error(f"Error emitting heartbeat: {e}", exc_info=True)
    
    def get_last_heartbeat(self) -> Optional[datetime]:
        """Get last heartbeat timestamp.
        
        Returns:
            Last heartbeat timestamp or None
        """
        return self._last_heartbeat
    
    def is_alive(self, timeout_multiplier: float = 2.0) -> bool:
        """Check if system is alive (heartbeat within timeout).
        
        Args:
            timeout_multiplier: Multiplier for interval (default 2.0 = 2x interval)
        
        Returns:
            True if heartbeat received within timeout
        """
        if self._last_heartbeat is None:
            return False
        
        elapsed = (datetime.now(timezone.utc) - self._last_heartbeat).total_seconds()
        timeout = self.interval * timeout_multiplier
        return elapsed <= timeout

