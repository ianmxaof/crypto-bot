"""Monitor trading activity and risk metrics."""

import asyncio
import logging
from typing import Dict, Optional
from decimal import Decimal
from datetime import datetime, timezone

from risk.limits import RiskLimits
from risk.circuit_breaker import CircuitBreaker
from risk.position_reconciler import PositionReconciler
from exchanges.base import BaseExchange

logger = logging.getLogger(__name__)


class RiskMonitor:
    """Monitor trading activity and enforce risk controls."""
    
    def __init__(self, exchange: BaseExchange, risk_limits: RiskLimits,
                 circuit_breaker: CircuitBreaker,
                 reconciliation_interval: int = 300):
        """Initialize risk monitor.
        
        Args:
            exchange: Exchange to monitor
            risk_limits: Risk limits instance
            circuit_breaker: Circuit breaker instance
            reconciliation_interval: Position reconciliation interval in seconds
        """
        self.exchange = exchange
        self.risk_limits = risk_limits
        self.circuit_breaker = circuit_breaker
        self.reconciler = PositionReconciler()
        self.reconciliation_interval = reconciliation_interval
        self.running = False
        self._task: Optional[asyncio.Task] = None
        
    async def start(self, initial_capital: Decimal):
        """Start risk monitoring.
        
        Args:
            initial_capital: Initial capital for tracking
        """
        self.circuit_breaker.set_initial_capital(initial_capital)
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop(initial_capital))
        logger.info("Risk monitor started")
        
    async def stop(self):
        """Stop risk monitoring."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Risk monitor stopped")
        
    async def _monitor_loop(self, starting_capital: Decimal):
        """Main monitoring loop."""
        last_reconciliation = datetime.now(timezone.utc)
        
        while self.running:
            try:
                # Get current portfolio value
                balance = await self.exchange.fetch_balance("USDT")
                if "USDT" not in balance:
                    await asyncio.sleep(60)
                    continue
                    
                current_value = balance["USDT"].total
                positions = await self.exchange.fetch_positions()
                
                # Add position values
                for pos in positions:
                    # Estimate position value (simplified)
                    # In real implementation, would fetch current prices
                    current_value += pos.size * pos.entry_price  # Approximation
                    
                # Check circuit breaker
                allowed, error = self.circuit_breaker.check(current_value)
                if not allowed:
                    logger.critical(f"Circuit breaker: {error}")
                    # Could trigger alerts here
                    
                # Check daily loss limits
                allowed, error = self.risk_limits.check_daily_loss(starting_capital, current_value)
                if not allowed:
                    logger.warning(f"Daily loss limit: {error}")
                    # Could trigger alerts here
                    
                # Periodic position reconciliation
                now = datetime.now(timezone.utc)
                if (now - last_reconciliation).total_seconds() >= self.reconciliation_interval:
                    reconciliation_result = await self.reconciler.reconcile(
                        self.exchange,
                        positions
                    )
                    if not reconciliation_result["match"]:
                        logger.error(f"Position reconciliation failed: {reconciliation_result}")
                    last_reconciliation = now
                    
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in risk monitor loop: {e}", exc_info=True)
                await asyncio.sleep(60)
                
    def check_trade_allowed(self, position_size_usd: Decimal) -> tuple[bool, Optional[str]]:
        """Check if a trade is allowed.
        
        Args:
            position_size_usd: Position size in USD
            
        Returns:
            Tuple of (allowed, error_message)
        """
        # Check position size limit
        allowed, error = self.risk_limits.check_position_size(position_size_usd)
        if not allowed:
            return False, error
            
        return True, None

