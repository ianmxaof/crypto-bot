"""Circuit breaker to halt trading on excessive losses."""

import json
import logging
import asyncio
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Trading halted
    HALF_OPEN = "half_open"  # Testing recovery
    DRAINING = "draining"  # Allowing in-flight orders to complete


class CircuitBreaker:
    """Circuit breaker to halt trading when losses exceed thresholds."""
    
    def __init__(self, loss_threshold_percent: Decimal = Decimal('0.10'),
                 loss_threshold_usd: Optional[Decimal] = None,
                 cooldown_seconds: int = 3600,
                 persistence_path: Optional[Path] = None):
        """Initialize circuit breaker.
        
        Args:
            loss_threshold_percent: Loss threshold as percentage (0.10 = 10%)
            loss_threshold_usd: Loss threshold in USD (if None, only uses percentage)
            cooldown_seconds: Seconds to wait before attempting recovery
            persistence_path: Optional path to persist circuit breaker state
        """
        self.loss_threshold_percent = loss_threshold_percent
        self.loss_threshold_usd = loss_threshold_usd
        self.cooldown_seconds = cooldown_seconds
        self.persistence_path = persistence_path
        self.state = CircuitBreakerState.CLOSED
        self.last_trigger_time: Optional[datetime] = None
        self.initial_capital: Optional[Decimal] = None
        self._in_flight_orders: Set[str] = set()  # Track in-flight order IDs
        self._lock = asyncio.Lock()
        
        # Load state from persistence if path provided
        if self.persistence_path:
            self._load_state()
        
    def set_initial_capital(self, capital: Decimal):
        """Set initial capital for percentage calculations.
        
        Args:
            capital: Initial capital
        """
        self.initial_capital = capital
        
    async def check(self, current_value: Decimal) -> tuple[bool, Optional[str]]:
        """Check if trading should be allowed.
        
        Args:
            current_value: Current portfolio value
            
        Returns:
            Tuple of (allowed, error_message)
        """
        async with self._lock:
            # Handle DRAINING state - allow in-flight orders to complete
            if self.state == CircuitBreakerState.DRAINING:
                # If no in-flight orders, transition to OPEN
                if len(self._in_flight_orders) == 0:
                    self._update_state(CircuitBreakerState.OPEN)
                    logger.info("Circuit breaker DRAINING complete - now OPEN")
                else:
                    # Still draining - allow existing orders but block new ones
                    return False, "Circuit breaker is DRAINING - waiting for in-flight orders"
            
            # Handle state transitions
            if self.state == CircuitBreakerState.OPEN:
                # Check if cooldown period has passed
                if self.last_trigger_time:
                    elapsed = (datetime.now(timezone.utc) - self.last_trigger_time).total_seconds()
                    if elapsed >= self.cooldown_seconds:
                        self._update_state(CircuitBreakerState.HALF_OPEN)
                        logger.warning("Circuit breaker entering HALF_OPEN state - testing recovery")
                    else:
                        return False, "Circuit breaker is OPEN - trading halted"
                        
            # Check if loss threshold exceeded
            if self.initial_capital and current_value < self.initial_capital:
                loss = self.initial_capital - current_value
                loss_percent = loss / self.initial_capital
                
                # Check percentage threshold
                if loss_percent >= self.loss_threshold_percent:
                    await self._trigger("Percentage loss threshold exceeded")
                    return False, f"Circuit breaker triggered: {loss_percent*100:.2f}% loss"
                    
                # Check absolute threshold
                if self.loss_threshold_usd and loss >= self.loss_threshold_usd:
                    await self._trigger("Absolute loss threshold exceeded")
                    return False, f"Circuit breaker triggered: ${loss:,.2f} loss"
                    
            # If half-open and check passes, close circuit breaker
            if self.state == CircuitBreakerState.HALF_OPEN:
                self._update_state(CircuitBreakerState.CLOSED)
                logger.info("Circuit breaker CLOSED - trading resumed")
                
            return True, None
    
    def check_sync(self, current_value: Decimal) -> tuple[bool, Optional[str]]:
        """Synchronous version of check (for backwards compatibility).
        
        Args:
            current_value: Current portfolio value
            
        Returns:
            Tuple of (allowed, error_message)
        """
        # For sync calls, if DRAINING, check if we can transition
        if self.state == CircuitBreakerState.DRAINING:
            if len(self._in_flight_orders) == 0:
                self.state = CircuitBreakerState.OPEN
                return False, "Circuit breaker is OPEN - trading halted"
            return False, "Circuit breaker is DRAINING - waiting for in-flight orders"
        
        if self.state == CircuitBreakerState.OPEN:
            if self.last_trigger_time:
                elapsed = (datetime.now(timezone.utc) - self.last_trigger_time).total_seconds()
                if elapsed >= self.cooldown_seconds:
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.warning("Circuit breaker entering HALF_OPEN state - testing recovery")
                else:
                    return False, "Circuit breaker is OPEN - trading halted"
        
        if self.initial_capital and current_value < self.initial_capital:
            loss = self.initial_capital - current_value
            loss_percent = loss / self.initial_capital
            
            if loss_percent >= self.loss_threshold_percent:
                # Note: This will trigger async, but we can't await here
                # The async _trigger will be called separately
                return False, f"Circuit breaker triggered: {loss_percent*100:.2f}% loss"
                
            if self.loss_threshold_usd and loss >= self.loss_threshold_usd:
                return False, f"Circuit breaker triggered: ${loss:,.2f} loss"
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.state = CircuitBreakerState.CLOSED
            logger.info("Circuit breaker CLOSED - trading resumed")
        
        return True, None
        
    async def _trigger(self, reason: str):
        """Trigger circuit breaker.
        
        Args:
            reason: Reason for triggering
        """
        async with self._lock:
            if self.state not in (CircuitBreakerState.OPEN, CircuitBreakerState.DRAINING):
                # If there are in-flight orders, enter DRAINING state first
                if len(self._in_flight_orders) > 0:
                    self._update_state(CircuitBreakerState.DRAINING)
                    logger.critical(
                        f"Circuit breaker TRIGGERED (DRAINING): {reason} - "
                        f"{len(self._in_flight_orders)} in-flight orders"
                    )
                else:
                    self._update_state(CircuitBreakerState.OPEN)
                    logger.critical(f"Circuit breaker TRIGGERED: {reason}")
                
                self.last_trigger_time = datetime.now(timezone.utc)
                self._save_state()
    
    def register_order(self, order_id: str):
        """Register an in-flight order.
        
        Args:
            order_id: Order ID to track
        """
        self._in_flight_orders.add(order_id)
        logger.debug(f"Registered in-flight order: {order_id} (total: {len(self._in_flight_orders)})")
    
    def complete_order(self, order_id: str):
        """Mark an order as complete.
        
        Args:
            order_id: Order ID that completed
        """
        self._in_flight_orders.discard(order_id)
        logger.debug(f"Completed order: {order_id} (remaining: {len(self._in_flight_orders)})")
        
        # If we're draining and no more orders, transition to OPEN
        if self.state == CircuitBreakerState.DRAINING and len(self._in_flight_orders) == 0:
            self._update_state(CircuitBreakerState.OPEN)
            logger.info("Circuit breaker DRAINING complete - now OPEN")
    
    async def wait_for_drain(self, timeout: float = 300.0) -> bool:
        """Wait for all in-flight orders to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all orders completed, False if timeout
        """
        import asyncio
        start_time = datetime.now(timezone.utc)
        
        while len(self._in_flight_orders) > 0:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            if elapsed >= timeout:
                logger.warning(
                    f"Timeout waiting for drain: {len(self._in_flight_orders)} orders still in-flight"
                )
                return False
            
            await asyncio.sleep(1.0)
        
        logger.info("All in-flight orders completed")
        return True
            
    def reset(self):
        """Manually reset circuit breaker."""
        self._update_state(CircuitBreakerState.CLOSED)
        self.last_trigger_time = None
        self._in_flight_orders.clear()
        # Save state after clearing in-flight orders
        self._save_state()
        logger.info("Circuit breaker manually reset")
    
    def get_in_flight_count(self) -> int:
        """Get number of in-flight orders.
        
        Returns:
            Number of in-flight orders
        """
        return len(self._in_flight_orders)
    
    def _save_state(self):
        """Save circuit breaker state to disk."""
        if not self.persistence_path:
            return
        
        try:
            state_data = {
                "state": self.state.value,
                "last_trigger_time": self.last_trigger_time.isoformat() if self.last_trigger_time else None,
                "initial_capital": str(self.initial_capital) if self.initial_capital else None,
                "in_flight_orders": list(self._in_flight_orders)
            }
            
            self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persistence_path, 'w') as f:
                json.dump(state_data, f, indent=2)
            
            logger.debug(f"Circuit breaker state saved: {self.state.value}")
        except Exception as e:
            logger.error(f"Error saving circuit breaker state: {e}")
    
    def _load_state(self):
        """Load circuit breaker state from disk.
        
        If state is OPEN, stay OPEN (do not auto-recover).
        """
        if not self.persistence_path or not self.persistence_path.exists():
            return
        
        try:
            with open(self.persistence_path, 'r') as f:
                state_data = json.load(f)
            
            # Load state
            state_str = state_data.get("state", "CLOSED")
            try:
                self.state = CircuitBreakerState(state_str)
            except ValueError:
                logger.warning(f"Invalid circuit breaker state: {state_str}, using CLOSED")
                self.state = CircuitBreakerState.CLOSED
            
            # Load last trigger time
            if state_data.get("last_trigger_time"):
                self.last_trigger_time = datetime.fromisoformat(state_data["last_trigger_time"])
            
            # Load initial capital
            if state_data.get("initial_capital"):
                self.initial_capital = Decimal(str(state_data["initial_capital"]))
            
            # Load in-flight orders
            self._in_flight_orders = set(state_data.get("in_flight_orders", []))
            
            logger.info(f"Circuit breaker state loaded: {self.state.value}")
            
            # Critical: If OPEN, stay OPEN (do not auto-recover)
            if self.state == CircuitBreakerState.OPEN:
                logger.critical(
                    "Circuit breaker state is OPEN - trading will remain halted. "
                    "Manual reset required."
                )
        except Exception as e:
            logger.error(f"Error loading circuit breaker state: {e}")
            # Default to CLOSED on error (safe default)
            self.state = CircuitBreakerState.CLOSED
    
    def _update_state(self, new_state: CircuitBreakerState):
        """Update state and persist.
        
        Args:
            new_state: New circuit breaker state
        """
        self.state = new_state
        self._save_state()

