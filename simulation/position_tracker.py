"""Track simulated trading positions."""

import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone

from exchanges.base import Position

logger = logging.getLogger(__name__)


class PositionTracker:
    """Tracks positions for simulation/paper trading."""
    
    def __init__(self):
        """Initialize position tracker."""
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        
    def add_position(self, position: Position):
        """Add or update a position.
        
        Args:
            position: Position to add/update
        """
        self.positions[position.symbol] = position
        logger.debug(f"Position tracked: {position.symbol} {position.side} {position.size}")
        
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position if exists, None otherwise
        """
        return self.positions.get(symbol)
        
    def get_all_positions(self) -> List[Position]:
        """Get all tracked positions.
        
        Returns:
            List of all positions
        """
        return list(self.positions.values())
        
    def update_position_size(self, symbol: str, size_delta: Decimal, current_price: Decimal):
        """Update position size (for partial fills).
        
        Args:
            symbol: Trading symbol
            size_delta: Change in position size (positive for long, negative for short)
            current_price: Current market price
        """
        if symbol not in self.positions:
            # Create new position
            side = "long" if size_delta > 0 else "short"
            position = Position(
                symbol=symbol,
                size=abs(size_delta),
                entry_price=current_price,
                side=side
            )
            self.add_position(position)
        else:
            pos = self.positions[symbol]
            current_size = pos.size if pos.side == "long" else -pos.size
            
            new_size = current_size + size_delta
            
            if abs(new_size) < Decimal('0.0001'):  # Position closed
                del self.positions[symbol]
            else:
                # Update position
                pos.side = "long" if new_size > 0 else "short"
                pos.size = abs(new_size)
                # Update entry price (weighted average)
                if abs(current_size) > Decimal('0.0001'):
                    pos.entry_price = (
                        (pos.entry_price * abs(current_size) + current_price * abs(size_delta)) /
                        abs(new_size)
                    )
                else:
                    pos.entry_price = current_price
                    
    def close_position(self, symbol: str):
        """Close a position.
        
        Args:
            symbol: Trading symbol
        """
        if symbol in self.positions:
            del self.positions[symbol]
            logger.debug(f"Position closed: {symbol}")
            
    def clear_all(self):
        """Clear all positions."""
        self.positions.clear()

