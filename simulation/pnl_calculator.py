"""Calculate P&L for simulated positions."""

import logging
from typing import Dict, List
from decimal import Decimal

from exchanges.base import Position

logger = logging.getLogger(__name__)


class PnLCalculator:
    """Calculate profit and loss for positions."""
    
    def __init__(self, fee_rate: Decimal = Decimal('0.001')):
        """Initialize PnL calculator.
        
        Args:
            fee_rate: Trading fee rate (0.001 = 0.1%)
        """
        self.fee_rate = fee_rate
        
    def calculate_unrealized_pnl(self, position: Position, current_price: Decimal) -> Decimal:
        """Calculate unrealized P&L for a position.
        
        Args:
            position: Position to calculate P&L for
            current_price: Current market price
            
        Returns:
            Unrealized P&L
        """
        if position.side == "long":
            pnl = (current_price - position.entry_price) * position.size
        else:  # short
            pnl = (position.entry_price - current_price) * position.size
            
        return pnl
        
    def calculate_realized_pnl(self, entry_price: Decimal, exit_price: Decimal,
                               size: Decimal, side: str) -> Decimal:
        """Calculate realized P&L for a closed position.
        
        Args:
            entry_price: Entry price
            exit_price: Exit price
            size: Position size
            side: 'long' or 'short'
            
        Returns:
            Realized P&L (after fees)
        """
        if side == "long":
            gross_pnl = (exit_price - entry_price) * size
        else:  # short
            gross_pnl = (entry_price - exit_price) * size
            
        # Subtract fees (entry + exit)
        fees = (entry_price + exit_price) * size * self.fee_rate
        net_pnl = gross_pnl - fees
        
        return net_pnl
        
    def calculate_total_unrealized_pnl(self, positions: List[Position],
                                       current_prices: Dict[str, Decimal]) -> Decimal:
        """Calculate total unrealized P&L for all positions.
        
        Args:
            positions: List of positions
            current_prices: Dictionary of symbol -> current price
            
        Returns:
            Total unrealized P&L
        """
        total = Decimal('0')
        for position in positions:
            if position.symbol in current_prices:
                pnl = self.calculate_unrealized_pnl(position, current_prices[position.symbol])
                total += pnl
        return total
        
    def estimate_slippage(self, order_size: Decimal, side: str,
                         current_price: Decimal, market_impact_bps: Decimal = Decimal('5')) -> Decimal:
        """Estimate slippage for an order.
        
        Args:
            order_size: Order size in base currency
            side: 'buy' or 'sell'
            current_price: Current market price
            market_impact_bps: Market impact in basis points (default 5 bps = 0.05%)
            
        Returns:
            Estimated slippage amount (price adjustment)
        """
        impact = current_price * (market_impact_bps / Decimal('10000'))
        # Slippage is worse for larger orders
        size_factor = min(Decimal('1.0'), order_size / Decimal('100'))  # Linear up to 100 units
        slippage = impact * size_factor
        
        # Buy orders pay more (slippage up), sell orders receive less (slippage down)
        if side == "buy":
            return slippage
        else:
            return -slippage

