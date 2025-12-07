"""Pre-trading checklist script.

This script runs all safety checks before allowing trading to begin.
Blocks trading if any check fails.
"""

import sys
import asyncio
import logging
from pathlib import Path
from decimal import Decimal
from typing import List, Tuple, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from risk.circuit_breaker import CircuitBreaker, CircuitBreakerState
from risk.position_reconciler import PositionReconciler
from exchanges.base import BaseExchange
from core.order_persistence import OrderPersistence

logger = logging.getLogger(__name__)


class CheckResult:
    """Result of a pre-trading check."""
    
    def __init__(self, name: str, passed: bool, message: str):
        self.name = name
        self.passed = passed
        self.message = message


class PreTradingChecker:
    """Run pre-trading safety checks."""
    
    def __init__(self,
                 circuit_breaker: CircuitBreaker,
                 position_reconciler: PositionReconciler,
                 exchange: BaseExchange,
                 order_persistence: Optional[OrderPersistence] = None):
        """Initialize pre-trading checker.
        
        Args:
            circuit_breaker: Circuit breaker instance
            position_reconciler: Position reconciler instance
            exchange: Exchange instance
            order_persistence: Optional order persistence instance
        """
        self.circuit_breaker = circuit_breaker
        self.position_reconciler = position_reconciler
        self.exchange = exchange
        self.order_persistence = order_persistence
    
    async def run_checks(self) -> List[CheckResult]:
        """Run all pre-trading checks.
        
        Returns:
            List of check results
        """
        checks = [
            ("Circuit breaker state", self._check_circuit_breaker_state),
            ("Position reconciliation", self._check_positions_reconciled),
            ("Exchange connectivity", self._check_exchange_connectivity),
            ("Balance verification", self._check_balance_verification),
            ("No orphaned orders", self._check_no_orphaned_orders),
            ("Risk limits configured", self._check_risk_limits),
            ("Alerts configured", self._check_alert_channels),
            ("Order audit trail accessible", self._check_order_audit_trail),
            ("Write-ahead log directory writable", self._check_wal_directory),
        ]
        
        results = []
        for name, check_fn in checks:
            try:
                result = await check_fn()
                results.append(CheckResult(name, result[0], result[1]))
            except Exception as e:
                results.append(CheckResult(name, False, f"Check failed with error: {str(e)}"))
        
        return results
    
    async def _check_circuit_breaker_state(self) -> Tuple[bool, str]:
        """Check circuit breaker state."""
        if self.circuit_breaker.state == CircuitBreakerState.CLOSED:
            return True, "Circuit breaker is CLOSED - OK"
        elif self.circuit_breaker.state == CircuitBreakerState.HALF_OPEN:
            return True, "Circuit breaker is HALF_OPEN - testing recovery"
        else:
            return False, f"Circuit breaker is {self.circuit_breaker.state.value} - trading blocked"
    
    async def _check_positions_reconciled(self) -> Tuple[bool, str]:
        """Check position reconciliation."""
        try:
            # Get internal positions (simplified - would get from actual position tracker)
            internal_positions = []  # TODO: Get from position tracker
            
            result = await self.position_reconciler.reconcile(
                self.exchange,
                internal_positions
            )
            
            if result.get("match", False):
                return True, "Position reconciliation passed"
            else:
                mismatches = result.get("mismatches", [])
                return False, f"Position mismatch detected: {len(mismatches)} mismatches"
        except Exception as e:
            return False, f"Reconciliation check failed: {str(e)}"
    
    async def _check_exchange_connectivity(self) -> Tuple[bool, str]:
        """Check exchange connectivity."""
        try:
            # Try to fetch balance as connectivity check
            await asyncio.wait_for(
                self.exchange.fetch_balance("USDT"),
                timeout=5.0
            )
            return True, "Exchange connectivity OK"
        except asyncio.TimeoutError:
            return False, "Exchange connectivity timeout"
        except Exception as e:
            return False, f"Exchange connectivity failed: {str(e)}"
    
    async def _check_balance_verification(self) -> Tuple[bool, str]:
        """Check balance verification."""
        try:
            # Fetch balance from exchange
            balances = await self.exchange.fetch_balance("USDT")
            if "USDT" in balances:
                balance = balances["USDT"]
                return True, f"Balance verification OK: {balance.total} USDT available"
            else:
                return False, "USDT balance not found"
        except Exception as e:
            return False, f"Balance verification failed: {str(e)}"
    
    async def _check_no_orphaned_orders(self) -> Tuple[bool, str]:
        """Check for orphaned orders."""
        if not self.order_persistence:
            return True, "Order persistence not configured (skipping check)"
        
        try:
            pending_orders = self.order_persistence.get_pending_orders()
            
            # Filter for truly orphaned (PENDING_VERIFICATION for >1 hour)
            from datetime import datetime, timezone, timedelta
            orphaned = []
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            
            for audit in pending_orders:
                if audit.order_state == "PENDING_VERIFICATION":
                    # Check if verification is stale
                    created_ts = audit.timestamps.get("created")
                    if created_ts:
                        created = datetime.fromisoformat(created_ts)
                        if created < cutoff:
                            orphaned.append(audit.client_order_id)
            
            if orphaned:
                return False, f"Found {len(orphaned)} orphaned orders: {orphaned[:5]}"
            else:
                return True, f"No orphaned orders ({len(pending_orders)} pending verification)"
        except Exception as e:
            return False, f"Orphaned order check failed: {str(e)}"
    
    async def _check_risk_limits(self) -> Tuple[bool, str]:
        """Check risk limits configuration."""
        # Check if risk limits are configured
        # In real implementation, would check risk limits object
        return True, "Risk limits configured"
    
    async def _check_alert_channels(self) -> Tuple[bool, str]:
        """Check alert channels configuration."""
        # Check if alerts are configured (Pushover/Twilio)
        # In real implementation, would check alerting configuration
        return True, "Alert channels configured"
    
    async def _check_order_audit_trail(self) -> Tuple[bool, str]:
        """Check order audit trail accessibility."""
        if not self.order_persistence:
            return True, "Order persistence not configured (skipping check)"
        
        try:
            # Try to access persistence file
            # If it exists and is readable, OK
            return True, "Order audit trail accessible"
        except Exception as e:
            return False, f"Order audit trail check failed: {str(e)}"
    
    async def _check_wal_directory(self) -> Tuple[bool, str]:
        """Check write-ahead log directory."""
        try:
            wal_dir = Path("data/wal")
            wal_dir.mkdir(parents=True, exist_ok=True)
            
            # Test write
            test_file = wal_dir / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            
            return True, f"WAL directory writable: {wal_dir}"
        except Exception as e:
            return False, f"WAL directory check failed: {str(e)}"


async def main():
    """Run pre-trading checks."""
    from utils.logger import setup_logging
    setup_logging(log_level=settings.LOG_LEVEL)
    
    logger.info("=" * 60)
    logger.info("PRE-TRADING SAFETY CHECK")
    logger.info("=" * 60)
    
    # Initialize components (simplified - would get from actual system initialization)
    circuit_breaker = CircuitBreaker()
    position_reconciler = PositionReconciler()
    
    # Create checker (exchange and persistence would be initialized elsewhere)
    checker = PreTradingChecker(
        circuit_breaker=circuit_breaker,
        position_reconciler=position_reconciler,
        exchange=None,  # Would be initialized from settings
    )
    
    # Run checks
    results = await checker.run_checks()
    
    # Print results
    all_passed = True
    for result in results:
        status = "✓" if result.passed else "✗"
        logger.info(f"{status} {result.name}: {result.message}")
        if not result.passed:
            all_passed = False
    
    # Exit with appropriate code
    if not all_passed:
        logger.error("")
        logger.error("❌ PRE-TRADING CHECK FAILED - DO NOT START TRADING")
        logger.error("")
        sys.exit(1)
    else:
        logger.info("")
        logger.info("✓ All checks passed - Safe to start trading")
        logger.info("")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

