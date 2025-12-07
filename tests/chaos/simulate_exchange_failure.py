"""Simulate exchange API failures for chaos testing."""

import logging
from typing import Optional, Dict, Any
from exchanges.base import ExchangeError

logger = logging.getLogger(__name__)


class ExchangeFailureSimulator:
    """Simulate exchange API failures."""
    
    def __init__(self):
        """Initialize exchange failure simulator."""
        self.fail_create_order = False
        self.fail_fetch_order = False
        self.fail_fetch_balance = False
        self.fail_fetch_positions = False
        self.fake_order_success = False  # Simulate order success but no execution
    
    def enable_create_order_failure(self):
        """Enable create order failure."""
        self.fail_create_order = True
        logger.warning("Exchange failure simulation: create_order will fail")
    
    def enable_fetch_order_failure(self):
        """Enable fetch order failure."""
        self.fail_fetch_order = True
        logger.warning("Exchange failure simulation: fetch_order will fail")
    
    def enable_fake_order_success(self):
        """Enable fake order success (order reports success but doesn't execute)."""
        self.fake_order_success = True
        logger.warning("Exchange failure simulation: orders will report success but not execute")
    
    def reset(self):
        """Reset all failure modes."""
        self.fail_create_order = False
        self.fail_fetch_order = False
        self.fail_fetch_balance = False
        self.fail_fetch_positions = False
        self.fake_order_success = False
        logger.info("Exchange failure simulation reset")


# Global failure simulator instance
_failure_simulator: Optional[ExchangeFailureSimulator] = None


def get_failure_simulator() -> ExchangeFailureSimulator:
    """Get global failure simulator instance.
    
    Returns:
        ExchangeFailureSimulator instance
    """
    global _failure_simulator
    if _failure_simulator is None:
        _failure_simulator = ExchangeFailureSimulator()
    return _failure_simulator

