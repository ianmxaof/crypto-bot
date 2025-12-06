"""Atomic balance manager for thread-safe balance operations."""

import asyncio
import logging
from typing import Dict, Optional
from decimal import Decimal
from contextlib import asynccontextmanager

from exchanges.base import Balance

logger = logging.getLogger(__name__)


class AtomicBalanceManager:
    """Thread-safe balance manager with reserve/release pattern.
    
    This prevents race conditions where balance is checked and then
    modified by another coroutine, which could lead to overspending.
    """
    
    def __init__(self, initial_balances: Dict[str, Balance]):
        """Initialize atomic balance manager.
        
        Args:
            initial_balances: Initial balance dictionary
        """
        self._balances: Dict[str, Balance] = {
            currency: Balance(
                currency=bal.currency,
                total=bal.total,
                free=bal.free,
                used=bal.used
            )
            for currency, bal in initial_balances.items()
        }
        self._lock = asyncio.Lock()
        self._reserved: Dict[str, Decimal] = {}  # currency -> reserved amount
        
    async def get_balance(self, currency: str = "USDT") -> Decimal:
        """Get available balance (free - reserved).
        
        Args:
            currency: Currency code
            
        Returns:
            Available balance
        """
        async with self._lock:
            if currency not in self._balances:
                return Decimal('0')
            
            reserved = self._reserved.get(currency, Decimal('0'))
            available = self._balances[currency].free - reserved
            return max(Decimal('0'), available)
    
    async def get_total_balance(self, currency: str = "USDT") -> Decimal:
        """Get total balance (including reserved).
        
        Args:
            currency: Currency code
            
        Returns:
            Total balance
        """
        async with self._lock:
            if currency not in self._balances:
                return Decimal('0')
            return self._balances[currency].total
    
    @asynccontextmanager
    async def reserve(self, currency: str, amount: Decimal):
        """Reserve balance for an operation.
        
        This is a context manager that ensures balance is reserved
        and then either released (if operation fails) or committed
        (if operation succeeds).
        
        Usage:
            async with balance_manager.reserve("USDT", Decimal("100")) as reserved:
                if reserved:
                    # Balance is reserved, proceed with operation
                    await do_operation()
                    # Balance will be committed automatically
                else:
                    # Insufficient balance
                    return
        
        Args:
            currency: Currency code
            amount: Amount to reserve
            
        Yields:
            True if reservation successful, False if insufficient balance
        """
        # Reserve the balance
        async with self._lock:
            if currency not in self._balances:
                if amount > Decimal('0'):
                    yield False
                    return
                self._balances[currency] = Balance(currency, Decimal('0'), Decimal('0'), Decimal('0'))
            
            available = self._balances[currency].free - self._reserved.get(currency, Decimal('0'))
            
            if available < amount:
                logger.warning(
                    f"Insufficient {currency} balance: available={available}, requested={amount}"
                )
                yield False
                return
            
            # Reserve the amount
            if currency not in self._reserved:
                self._reserved[currency] = Decimal('0')
            self._reserved[currency] += amount
            
            logger.debug(f"Reserved {amount} {currency} (available: {available - amount})")
        
        try:
            # Yield control - operation happens here
            yield True
        except Exception as e:
            # Operation failed - release reservation
            async with self._lock:
                if currency in self._reserved:
                    self._reserved[currency] -= amount
                    if self._reserved[currency] <= Decimal('0'):
                        del self._reserved[currency]
                logger.debug(f"Released reservation for {amount} {currency} due to error: {e}")
            raise
        else:
            # Operation succeeded - commit reservation (deduct from free balance)
            async with self._lock:
                if currency in self._reserved:
                    self._reserved[currency] -= amount
                    if self._reserved[currency] <= Decimal('0'):
                        del self._reserved[currency]
                
                # Deduct from free balance
                if self._balances[currency].free >= amount:
                    self._balances[currency].free -= amount
                    self._balances[currency].used += amount
                    self._balances[currency].total = self._balances[currency].free + self._balances[currency].used
                    logger.debug(f"Committed {amount} {currency} (free: {self._balances[currency].free})")
                else:
                    logger.error(
                        f"Balance inconsistency: free={self._balances[currency].free}, "
                        f"amount={amount}"
                    )
    
    async def add_balance(self, currency: str, amount: Decimal):
        """Add balance (e.g., from selling position).
        
        Args:
            currency: Currency code
            amount: Amount to add
        """
        async with self._lock:
            if currency not in self._balances:
                self._balances[currency] = Balance(currency, Decimal('0'), Decimal('0'), Decimal('0'))
            
            self._balances[currency].total += amount
            self._balances[currency].free += amount
            logger.debug(f"Added {amount} {currency} (total: {self._balances[currency].total})")
    
    async def get_all_balances(self) -> Dict[str, Balance]:
        """Get all balances (copy).
        
        Returns:
            Dictionary of currency -> Balance
        """
        async with self._lock:
            return {
                currency: Balance(
                    currency=bal.currency,
                    total=bal.total,
                    free=bal.free,
                    used=bal.used
                )
                for currency, bal in self._balances.items()
            }
    
    async def update_balance(self, currency: str, total: Decimal, free: Decimal, used: Decimal):
        """Update balance from external source (e.g., exchange reconciliation).
        
        Args:
            currency: Currency code
            total: Total balance
            free: Free balance
            used: Used balance
        """
        async with self._lock:
            self._balances[currency] = Balance(currency, total, free, used)
            # Clear reservations if they exceed available balance
            reserved = self._reserved.get(currency, Decimal('0'))
            if reserved > free:
                logger.warning(
                    f"Reserved amount {reserved} exceeds free balance {free} for {currency}, "
                    "clearing reservation"
                )
                self._reserved[currency] = Decimal('0')

