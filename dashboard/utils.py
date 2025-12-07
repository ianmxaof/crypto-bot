"""Dashboard utility functions for type conversion and safe calculations."""

from decimal import Decimal
from typing import Union, Any


def to_decimal(value: Any) -> Decimal:
    """Convert value to Decimal safely.
    
    Args:
        value: Value to convert (Decimal, float, int, str, or None)
        
    Returns:
        Decimal representation of the value, or Decimal('0') if None/invalid
    """
    if value is None:
        return Decimal('0')
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (ValueError, TypeError):
        return Decimal('0')


def to_float(value: Any) -> float:
    """Convert value to float safely.
    
    Args:
        value: Value to convert (Decimal, float, int, str, or None)
        
    Returns:
        float representation of the value, or 0.0 if None/invalid
    """
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(str(value))
    except (ValueError, TypeError):
        return 0.0


def safe_calculate_return(current: Any, starting: Any) -> float:
    """Calculate return percentage safely, handling Decimal/float mixing.
    
    Args:
        current: Current balance value
        starting: Starting balance value
        
    Returns:
        Return percentage as float, or 0.0 if calculation fails
    """
    try:
        current_dec = to_decimal(current)
        starting_dec = to_decimal(starting)
        
        if starting_dec == 0:
            return 0.0
        
        return float((current_dec - starting_dec) / starting_dec * Decimal('100'))
    except (ValueError, TypeError, ZeroDivisionError) as e:
        # Log error but don't crash - return 0.0
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error calculating return percentage: {e}")
        return 0.0


def safe_subtract(a: Any, b: Any) -> float:
    """Safely subtract two values, handling Decimal/float mixing.
    
    Args:
        a: First value
        b: Second value
        
    Returns:
        Result as float
    """
    try:
        a_dec = to_decimal(a)
        b_dec = to_decimal(b)
        return float(a_dec - b_dec)
    except (ValueError, TypeError) as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Error in safe_subtract: {e}")
        return 0.0


def safe_format_currency(value: Any) -> str:
    """Safely format a currency value for display.
    
    Args:
        value: Value to format
        
    Returns:
        Formatted string like "$1,234.56"
    """
    try:
        float_val = to_float(value)
        return f"${float_val:,.2f}"
    except Exception:
        return "$0.00"

