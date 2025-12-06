"""Base exchange interface for unified API access."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime
from enum import Enum


class ExchangeError(Exception):
    """Base exception for exchange operations."""
    pass


class InsufficientBalance(ExchangeError):
    """Raised when insufficient balance for operation."""
    pass


class OrderNotFound(ExchangeError):
    """Raised when order is not found."""
    pass


class OrderRejectionReason(Enum):
    """Reasons for order rejection."""
    CIRCUIT_BREAKER_ACTIVE = "circuit_breaker_active"
    POSITION_LIMIT_EXCEEDED = "position_limit_exceeded"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    INVALID_QUANTITY = "invalid_quantity"
    INVALID_PRICE = "invalid_price"
    RISK_CHECK_FAILED = "risk_check_failed"
    SYMBOL_LOCKED = "symbol_locked"
    UNKNOWN = "unknown"


class OrderValidationResult:
    """Result of order validation."""
    def __init__(self, allowed: bool, reason: Optional[OrderRejectionReason] = None,
                 message: Optional[str] = None):
        self.allowed = allowed
        self.reason = reason
        self.message = message
    
    @classmethod
    def success(cls) -> "OrderValidationResult":
        """Create a successful validation result."""
        return cls(allowed=True)
    
    @classmethod
    def rejected(cls, reason: OrderRejectionReason, message: str) -> "OrderValidationResult":
        """Create a rejected validation result."""
        return cls(allowed=False, reason=reason, message=message)


class Position:
    """Represents an open position."""
    def __init__(self, symbol: str, size: Decimal, entry_price: Decimal, side: str, 
                 unrealized_pnl: Decimal = Decimal('0'), leverage: Decimal = Decimal('1')):
        self.symbol = symbol
        self.size = size
        self.entry_price = entry_price
        self.side = side  # 'long' or 'short'
        self.unrealized_pnl = unrealized_pnl
        self.leverage = leverage


class Balance:
    """Represents account balance."""
    def __init__(self, currency: str, total: Decimal, free: Decimal, used: Decimal):
        self.currency = currency
        self.total = total
        self.free = free
        self.used = used


class Order:
    """Represents an order."""
    def __init__(self, id: str, symbol: str, side: str, type: str, amount: Decimal,
                 price: Optional[Decimal], status: str, filled: Decimal = Decimal('0'),
                 remaining: Decimal = Decimal('0'), timestamp: Optional[datetime] = None,
                 client_order_id: Optional[str] = None):
        self.id = id
        self.symbol = symbol
        self.side = side  # 'buy' or 'sell'
        self.type = type  # 'market', 'limit', etc.
        self.amount = amount
        self.price = price
        self.status = status  # 'open', 'closed', 'canceled', 'filled', 'partial'
        self.filled = filled
        self.remaining = remaining
        self.timestamp = timestamp or datetime.utcnow()
        self.client_order_id = client_order_id  # For idempotent order submission


class FundingRate:
    """Represents funding rate information."""
    def __init__(self, symbol: str, rate: Decimal, timestamp: datetime, next_funding_time: Optional[datetime] = None):
        self.symbol = symbol
        self.rate = rate
        self.timestamp = timestamp
        self.next_funding_time = next_funding_time


class BaseExchange(ABC):
    """Base class for all exchange implementations."""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """Initialize exchange client.
        
        Args:
            api_key: API key
            api_secret: API secret
            testnet: Use testnet/sandbox environment
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.name = self.__class__.__name__.replace("Exchange", "").lower()
        self._is_simulation = False
        
    def is_simulation(self) -> bool:
        """Check if this exchange is running in simulation mode.
        
        Returns:
            True if in simulation/paper trading mode
        """
        return self._is_simulation
        
    def set_simulation(self, is_simulation: bool):
        """Set simulation mode.
        
        Args:
            is_simulation: Whether to enable simulation mode
        """
        self._is_simulation = is_simulation
        
    @abstractmethod
    async def fetch_balance(self, currency: Optional[str] = None) -> Dict[str, Balance]:
        """Fetch account balance.
        
        Args:
            currency: Specific currency to fetch (None for all)
            
        Returns:
            Dictionary mapping currency to Balance
        """
        pass
        
    @abstractmethod
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Fetch open positions.
        
        Args:
            symbol: Specific symbol to fetch (None for all)
            
        Returns:
            List of open positions
        """
        pass
        
    @abstractmethod
    async def create_market_order(self, symbol: str, side: str, amount: Decimal, 
                                   params: Optional[Dict] = None,
                                   client_order_id: Optional[str] = None) -> Order:
        """Create a market order.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            params: Additional parameters
            
        Returns:
            Created order
        """
        pass
        
    @abstractmethod
    async def create_limit_order(self, symbol: str, side: str, amount: Decimal, price: Decimal,
                                  params: Optional[Dict] = None,
                                  client_order_id: Optional[str] = None) -> Order:
        """Create a limit order.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            price: Limit price
            params: Additional parameters
            
        Returns:
            Created order
        """
        pass
        
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        """Fetch order by ID.
        
        Args:
            order_id: Order ID
            symbol: Trading pair symbol
            
        Returns:
            Order object
        """
        pass
        
    @abstractmethod
    async def fetch_funding_rates(self, symbols: Optional[List[str]] = None) -> Dict[str, FundingRate]:
        """Fetch funding rates for perpetuals.
        
        Args:
            symbols: List of symbols to fetch (None for all)
            
        Returns:
            Dictionary mapping symbol to FundingRate
        """
        pass
        
    @abstractmethod
    async def set_leverage(self, leverage: int, symbol: str) -> bool:
        """Set leverage for a symbol.
        
        Args:
            leverage: Leverage amount (1-125 typically)
            symbol: Trading pair symbol
            
        Returns:
            True if successful
        """
        pass
        
    @abstractmethod
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker/price data for a symbol.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker data dictionary
        """
        pass
        
    @abstractmethod
    async def close_position(self, symbol: str, side: Optional[str] = None) -> bool:
        """Close an open position.
        
        Args:
            symbol: Trading pair symbol
            side: Position side to close ('long' or 'short'), None closes both
            
        Returns:
            True if successful
        """
        pass
    
    async def validate_order(self, symbol: str, side: str, amount: Decimal,
                            price: Optional[Decimal] = None,
                            order_type: str = "market") -> OrderValidationResult:
        """Validate an order before submission.
        
        This method should be called BEFORE create_market_order or create_limit_order
        to ensure all risk checks pass. Subclasses can override to add exchange-specific
        validation.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            price: Order price (for limit orders)
            order_type: 'market' or 'limit'
            
        Returns:
            OrderValidationResult indicating if order is allowed
        """
        # Basic validation
        if amount <= Decimal('0'):
            return OrderValidationResult.rejected(
                OrderRejectionReason.INVALID_QUANTITY,
                f"Order amount must be positive, got {amount}"
            )
        
        if price is not None and price <= Decimal('0'):
            return OrderValidationResult.rejected(
                OrderRejectionReason.INVALID_PRICE,
                f"Order price must be positive, got {price}"
            )
        
        # Default: allow order (subclasses should override for additional checks)
        return OrderValidationResult.success()
    
    async def fetch_order_by_client_id(self, client_order_id: str, symbol: str) -> Optional[Order]:
        """Fetch order by client order ID (for idempotent submission).
        
        Args:
            client_order_id: Client order ID
            symbol: Trading pair symbol
            
        Returns:
            Order if found, None otherwise
        """
        # Default implementation - subclasses should override
        return None

