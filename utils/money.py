"""Immutable Money type that prevents float/Decimal mixing and precision loss."""

import logging
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Union

logger = logging.getLogger(__name__)


class Money:
    """Immutable money type that prevents precision loss from float operations.
    
    This class enforces Decimal-only operations and prevents accidental
    float contamination that can cause rounding errors in financial calculations.
    """
    
    PRECISION = Decimal("0.00000001")  # 8 decimal places for crypto
    
    def __init__(self, value: Union[str, Decimal, "Money"]):
        """Initialize Money from string or Decimal.
        
        Args:
            value: Money value as string, Decimal, or Money instance
            
        Raises:
            TypeError: If value is a float
        """
        if isinstance(value, float):
            raise TypeError("Never construct Money from float - use Decimal or string")
        
        if isinstance(value, Money):
            self._value = value._value
        else:
            self._value = Decimal(str(value)).quantize(
                self.PRECISION, rounding=ROUND_DOWN
            )
    
    @property
    def value(self) -> Decimal:
        """Get the Decimal value."""
        return self._value
    
    def __str__(self) -> str:
        return str(self._value)
    
    def __repr__(self) -> str:
        return f"Money({self._value})"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Money):
            return self._value == other._value
        return False
    
    def __lt__(self, other) -> bool:
        if isinstance(other, Money):
            return self._value < other._value
        if isinstance(other, (Decimal, str)):
            return self._value < Decimal(str(other))
        raise TypeError(f"Cannot compare Money with {type(other)}")
    
    def __le__(self, other) -> bool:
        return self.__lt__(other) or self.__eq__(other)
    
    def __gt__(self, other) -> bool:
        return not self.__le__(other)
    
    def __ge__(self, other) -> bool:
        return not self.__lt__(other)
    
    def __add__(self, other: Union[Decimal, "Money"]) -> "Money":
        """Add Money values."""
        if isinstance(other, float):
            raise TypeError("Cannot add float to Money - use Decimal")
        if isinstance(other, Money):
            return Money(self._value + other._value)
        if isinstance(other, Decimal):
            return Money(self._value + other)
        if isinstance(other, (int, str)):
            return Money(self._value + Decimal(str(other)))
        raise TypeError(f"Cannot add {type(other)} to Money")
    
    def __sub__(self, other: Union[Decimal, "Money"]) -> "Money":
        """Subtract from Money."""
        if isinstance(other, float):
            raise TypeError("Cannot subtract float from Money - use Decimal")
        if isinstance(other, Money):
            return Money(self._value - other._value)
        if isinstance(other, Decimal):
            return Money(self._value - other)
        if isinstance(other, (int, str)):
            return Money(self._value - Decimal(str(other)))
        raise TypeError(f"Cannot subtract {type(other)} from Money")
    
    def __mul__(self, other: Union[Decimal, "Money"]) -> "Money":
        """Multiply Money by Decimal."""
        if isinstance(other, float):
            raise TypeError("Cannot multiply Money by float - use Decimal")
        if isinstance(other, Money):
            return Money(self._value * other._value)
        if isinstance(other, Decimal):
            return Money(self._value * other)
        if isinstance(other, (int, str)):
            return Money(self._value * Decimal(str(other)))
        raise TypeError(f"Cannot multiply Money by {type(other)}")
    
    def __truediv__(self, other: Union[Decimal, "Money"]) -> "Money":
        """Divide Money by Decimal."""
        if isinstance(other, float):
            raise TypeError("Cannot divide Money by float - use Decimal")
        if isinstance(other, Money):
            if other._value == 0:
                raise ZeroDivisionError("Cannot divide Money by zero")
            return Money(self._value / other._value)
        if isinstance(other, Decimal):
            if other == 0:
                raise ZeroDivisionError("Cannot divide Money by zero")
            return Money(self._value / other)
        if isinstance(other, (int, str)):
            divisor = Decimal(str(other))
            if divisor == 0:
                raise ZeroDivisionError("Cannot divide Money by zero")
            return Money(self._value / divisor)
        raise TypeError(f"Cannot divide Money by {type(other)}")
    
    def __radd__(self, other) -> "Money":
        return self.__add__(other)
    
    def __rsub__(self, other) -> "Money":
        if isinstance(other, float):
            raise TypeError("Cannot subtract Money from float - use Decimal")
        if isinstance(other, (Decimal, int, str)):
            return Money(Decimal(str(other)) - self._value)
        raise TypeError(f"Cannot subtract Money from {type(other)}")
    
    def __rmul__(self, other) -> "Money":
        return self.__mul__(other)
    
    def __rtruediv__(self, other) -> Decimal:
        """Divide Decimal by Money (returns Decimal, not Money)."""
        if isinstance(other, float):
            raise TypeError("Cannot divide float by Money - use Decimal")
        if isinstance(other, (Decimal, int, str)):
            return Decimal(str(other)) / self._value
        raise TypeError(f"Cannot divide {type(other)} by Money")
    
    def __neg__(self) -> "Money":
        """Negate Money."""
        return Money(-self._value)
    
    def __abs__(self) -> "Money":
        """Absolute value of Money."""
        return Money(abs(self._value))
    
    def for_exchange(self, tick_size: Decimal) -> Decimal:
        """Round to exchange's tick size for order submission.
        
        Args:
            tick_size: Exchange tick size (e.g., Decimal('0.01') for BTC)
            
        Returns:
            Decimal rounded to tick size
        """
        return self._value.quantize(tick_size, rounding=ROUND_DOWN)
    
    def to_decimal(self) -> Decimal:
        """Convert to Decimal (for compatibility with existing code)."""
        return self._value
    
    @classmethod
    def zero(cls) -> "Money":
        """Create zero Money."""
        return cls(Decimal('0'))
    
    @classmethod
    def from_float_safe(cls, value: float, precision: int = 8) -> "Money":
        """Safely convert float to Money by first converting to string.
        
        This is a convenience method for cases where you receive float
        from external APIs. Always prefer Decimal or string inputs.
        
        Args:
            value: Float value
            precision: Decimal precision to use
            
        Returns:
            Money instance
        """
        # Convert float to string first to avoid precision loss
        return cls(f"{value:.{precision}f}")

