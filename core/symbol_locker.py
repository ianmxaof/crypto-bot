"""Symbol-level locking to prevent concurrent trades on the same symbol."""

import asyncio
import logging
from typing import Dict, Optional
from contextlib import asynccontextmanager
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SymbolLockError(Exception):
    """Raised when symbol lock cannot be acquired."""
    pass


class SymbolLocker:
    """Manages locks per trading symbol to prevent concurrent trades.
    
    This prevents race conditions where multiple agents try to trade
    the same symbol simultaneously, which could lead to:
    - Oversized positions
    - Conflicting orders
    - State desynchronization
    """
    
    def __init__(self, default_timeout: float = 30.0):
        """Initialize symbol locker.
        
        Args:
            default_timeout: Default timeout for acquiring locks (seconds)
        """
        self._locks: Dict[str, asyncio.Lock] = {}
        self._lock_owners: Dict[str, str] = {}  # symbol -> agent_id
        self._global_lock = asyncio.Lock()
        self._default_timeout = default_timeout
    
    @asynccontextmanager
    async def lock_symbol(self, symbol: str, agent_id: str, timeout: Optional[float] = None):
        """Acquire lock for a symbol.
        
        Usage:
            async with symbol_locker.lock_symbol("BTC/USDT", "agent_1"):
                # Only one agent can execute trades for BTC/USDT here
                await execute_trade(symbol)
        
        Args:
            symbol: Trading symbol to lock
            agent_id: ID of agent requesting lock
            timeout: Timeout in seconds (default: self._default_timeout)
            
        Yields:
            None (context manager)
            
        Raises:
            SymbolLockError: If lock cannot be acquired within timeout
        """
        timeout = timeout or self._default_timeout
        
        # Get or create lock for symbol
        async with self._global_lock:
            if symbol not in self._locks:
                self._locks[symbol] = asyncio.Lock()
        
        lock = self._locks[symbol]
        
        try:
            # Try to acquire lock with timeout
            acquired = await asyncio.wait_for(lock.acquire(), timeout=timeout)
            if not acquired:
                raise SymbolLockError(f"Failed to acquire lock for {symbol} within {timeout}s")
            
            # Record lock owner
            async with self._global_lock:
                self._lock_owners[symbol] = agent_id
            
            logger.debug(f"Lock acquired for {symbol} by {agent_id}")
            
            yield
            
        except asyncio.TimeoutError:
            current_owner = self._lock_owners.get(symbol, "unknown")
            raise SymbolLockError(
                f"Timeout acquiring lock for {symbol} (held by {current_owner})"
            )
        finally:
            # Release lock
            async with self._global_lock:
                self._lock_owners.pop(symbol, None)
            
            if lock.locked():
                lock.release()
                logger.debug(f"Lock released for {symbol}")
    
    def get_lock_owner(self, symbol: str) -> Optional[str]:
        """Check which agent (if any) holds the lock for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Agent ID holding the lock, or None if not locked
        """
        return self._lock_owners.get(symbol)
    
    def is_locked(self, symbol: str) -> bool:
        """Check if a symbol is currently locked.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            True if symbol is locked
        """
        if symbol not in self._locks:
            return False
        return self._locks[symbol].locked()
    
    def get_locked_symbols(self) -> Dict[str, str]:
        """Get all currently locked symbols and their owners.
        
        Returns:
            Dictionary mapping symbol -> agent_id
        """
        return self._lock_owners.copy()

