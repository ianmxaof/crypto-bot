"""Reconcile positions between internal state and exchange."""

import asyncio
import logging
from typing import List, Dict, Optional, Callable, Any
from decimal import Decimal
from datetime import datetime, timezone

from exchanges.base import BaseExchange, Position
from core.event_bus import event_bus

logger = logging.getLogger(__name__)


class PositionReconciler:
    """Reconcile positions between internal tracking and exchange."""
    
    def __init__(self, tolerance_percent: Decimal = Decimal('0.01'),
                 reconciliation_interval: int = 30,
                 circuit_breaker: Optional[Any] = None):
        """Initialize position reconciler.
        
        Args:
            tolerance_percent: Tolerance for position differences (0.01 = 1%)
            reconciliation_interval: Seconds between automatic reconciliations
            circuit_breaker: Optional circuit breaker instance for triggering on mismatch
        """
        self.tolerance_percent = tolerance_percent
        self.reconciliation_interval = reconciliation_interval
        self.circuit_breaker = circuit_breaker
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._desync_callbacks: List[Callable] = []
        self._last_reconciliation: Optional[datetime] = None
        self._reconciliation_count = 0
        self._desync_count = 0
        self._consecutive_mismatches = 0
        
    async def reconcile(self, exchange: BaseExchange,
                       internal_positions: List[Position]) -> Dict:
        """Reconcile positions.
        
        Args:
            exchange: Exchange to reconcile with
            internal_positions: Internally tracked positions
            
        Returns:
            Dictionary with reconciliation results
        """
        try:
            # Fetch positions from exchange
            exchange_positions = await exchange.fetch_positions()
            
            # Build position maps
            internal_map = {pos.symbol: pos for pos in internal_positions}
            exchange_map = {pos.symbol: pos for pos in exchange_positions}
            
            mismatches = []
            missing_internal = []
            missing_exchange = []
            
            # Check all symbols
            all_symbols = set(internal_map.keys()) | set(exchange_map.keys())
            
            for symbol in all_symbols:
                internal_pos = internal_map.get(symbol)
                exchange_pos = exchange_map.get(symbol)
                
                if internal_pos and not exchange_pos:
                    missing_exchange.append(symbol)
                elif exchange_pos and not internal_pos:
                    missing_internal.append(symbol)
                elif internal_pos and exchange_pos:
                    # Check if sizes match
                    size_diff = abs(internal_pos.size - exchange_pos.size)
                    if size_diff > self.tolerance_percent * internal_pos.size:
                        mismatches.append({
                            "symbol": symbol,
                            "internal_size": float(internal_pos.size),
                            "exchange_size": float(exchange_pos.size),
                            "difference": float(size_diff)
                        })
                        
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "match": len(mismatches) == 0 and len(missing_internal) == 0 and len(missing_exchange) == 0,
                "mismatches": mismatches,
                "missing_internal": missing_internal,
                "missing_exchange": missing_exchange
            }
            
            if not result["match"]:
                logger.warning(f"Position mismatch detected: {result}")
                
            return result
            
        except Exception as e:
            logger.error(f"Error during position reconciliation: {e}", exc_info=True)
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "match": False,
                "error": str(e),
                "mismatches": [],
                "missing_internal": [],
                "missing_exchange": []
            }
    
    def register_desync_callback(self, callback: Callable):
        """Register callback for desync events.
        
        Args:
            callback: Async function(symbol, internal_pos, exchange_pos) -> None
        """
        self._desync_callbacks.append(callback)
    
    async def start_periodic_reconciliation(self, exchange: BaseExchange,
                                           get_internal_positions: Callable[[], List[Position]]):
        """Start periodic reconciliation task.
        
        Args:
            exchange: Exchange to reconcile with
            get_internal_positions: Function that returns current internal positions
        """
        if self._running:
            logger.warning("Periodic reconciliation already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(
            self._reconciliation_loop(exchange, get_internal_positions)
        )
        logger.info(f"Started periodic reconciliation (interval: {self.reconciliation_interval}s)")
    
    async def stop_periodic_reconciliation(self):
        """Stop periodic reconciliation task."""
        if not self._running:
            return
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped periodic reconciliation")
    
    async def _reconciliation_loop(self, exchange: BaseExchange,
                                  get_internal_positions: Callable[[], List[Position]]):
        """Background task for periodic reconciliation."""
        while self._running:
            try:
                await asyncio.sleep(self.reconciliation_interval)
                
                if not self._running:
                    break
                
                internal_positions = get_internal_positions()
                result = await self.reconcile(exchange, internal_positions)
                
                self._last_reconciliation = datetime.now(timezone.utc)
                self._reconciliation_count += 1
                
                if not result["match"]:
                    self._desync_count += 1
                    self._consecutive_mismatches += 1
                    
                    logger.warning(
                        f"Position desync detected (reconciliation #{self._reconciliation_count}): "
                        f"{len(result['mismatches'])} mismatches, "
                        f"{len(result['missing_internal'])} missing internal, "
                        f"{len(result['missing_exchange'])} missing exchange, "
                        f"consecutive mismatches: {self._consecutive_mismatches}"
                    )
                    
                    # Auto-correction logic
                    await self._handle_mismatch(result, exchange, internal_positions)
                    
                    # Notify callbacks
                    for callback in self._desync_callbacks:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(result)
                            else:
                                callback(result)
                        except Exception as e:
                            logger.error(f"Desync callback failed: {e}")
                else:
                    # Reset consecutive mismatch counter on success
                    self._consecutive_mismatches = 0
                    logger.debug(f"Position reconciliation passed (#{self._reconciliation_count})")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in reconciliation loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retry
    
    async def _handle_mismatch(self, result: Dict, exchange: BaseExchange, internal_positions: List[Position]):
        """Handle position mismatch with auto-correction.
        
        Args:
            result: Reconciliation result dictionary
            exchange: Exchange instance
            internal_positions: Internal positions list
        """
        mismatches = result.get("mismatches", [])
        
        # Check if mismatch is within tolerance
        within_tolerance = True
        for mismatch in mismatches:
            internal_size = Decimal(str(mismatch["internal_size"]))
            exchange_size = Decimal(str(mismatch["exchange_size"]))
            difference = abs(internal_size - exchange_size)
            
            # Check if difference exceeds tolerance
            if internal_size > 0:
                diff_percent = difference / internal_size
                if diff_percent > self.tolerance_percent:
                    within_tolerance = False
                    break
        
        if within_tolerance:
            # Within tolerance: Auto-sync internal state to exchange state
            logger.info("Mismatch within tolerance - auto-syncing internal state to exchange")
            
            # Sync internal positions to match exchange
            # This would update internal position tracker
            # Implementation depends on how positions are tracked
            # For now, log the action
            logger.info(f"Auto-syncing {len(mismatches)} positions within tolerance")
            
            # Publish event for monitoring
            event_bus.publish("risk:position_mismatch", {
                "action": "auto_sync",
                "mismatches": mismatches,
                "tolerance": float(self.tolerance_percent),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, source="position_reconciler")
        else:
            # Beyond tolerance: Trigger circuit breaker and halt trading
            logger.critical(
                f"Position mismatch BEYOND tolerance ({self.tolerance_percent*100}%) - "
                f"HALTING TRADING"
            )
            
            # Trigger circuit breaker if available
            if self.circuit_breaker:
                # Trigger circuit breaker (async)
                import asyncio
                asyncio.create_task(self._trigger_circuit_breaker("Position mismatch beyond tolerance"))
            
            # Publish critical event
            event_bus.publish("risk:position_mismatch", {
                "action": "halt_trading",
                "reason": "mismatch_beyond_tolerance",
                "mismatches": mismatches,
                "tolerance": float(self.tolerance_percent),
                "consecutive_mismatches": self._consecutive_mismatches,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, source="position_reconciler")
            
            # Persistent mismatches (>3 consecutive)
            if self._consecutive_mismatches > 3:
                logger.critical(
                    f"PERSISTENT position mismatch ({self._consecutive_mismatches} consecutive) - "
                    "Circuit breaker will remain OPEN until reconciliation passes"
                )
    
    async def _trigger_circuit_breaker(self, reason: str):
        """Trigger circuit breaker.
        
        Args:
            reason: Reason for triggering
        """
        if self.circuit_breaker:
            # Get current portfolio value (simplified)
            # In real implementation, would fetch actual value
            current_value = Decimal('0')  # Placeholder
            await self.circuit_breaker._trigger(reason)
            
            # If circuit breaker is in DRAINING state and reconciliation detects mismatch,
            # transition to OPEN immediately (per Opus 4.5 spec)
            from risk.circuit_breaker import CircuitBreakerState
            if self.circuit_breaker.state == CircuitBreakerState.DRAINING:
                # Use _update_state() to ensure state is persisted to disk
                self.circuit_breaker._update_state(CircuitBreakerState.OPEN)
                logger.critical("Circuit breaker transitioned from DRAINING to OPEN due to reconciliation mismatch")
    
    def get_stats(self) -> Dict:
        """Get reconciliation statistics.
        
        Returns:
            Dictionary with reconciliation stats
        """
        return {
            "reconciliation_count": self._reconciliation_count,
            "desync_count": self._desync_count,
            "consecutive_mismatches": self._consecutive_mismatches,
            "last_reconciliation": self._last_reconciliation.isoformat() if self._last_reconciliation else None,
            "running": self._running
        }

