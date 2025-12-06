"""Enforce position and loss limits."""

import logging
from decimal import Decimal
from datetime import datetime, timezone, date
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RiskLimits:
    """Enforce trading risk limits."""
    
    def __init__(self, max_position_size_usd: Decimal, max_daily_loss_percent: Decimal,
                 max_daily_loss_usd: Decimal):
        """Initialize risk limits.
        
        Args:
            max_position_size_usd: Maximum position size in USD
            max_daily_loss_percent: Maximum daily loss as percentage (0.05 = 5%)
            max_daily_loss_usd: Maximum daily loss in USD
        """
        self.max_position_size_usd = max_position_size_usd
        self.max_daily_loss_percent = max_daily_loss_percent
        self.max_daily_loss_usd = max_daily_loss_usd
        self.daily_pnl: Dict[date, Decimal] = {}
        self.current_date = date.today()
        
    def check_position_size(self, position_size_usd: Decimal) -> tuple[bool, Optional[str]]:
        """Check if position size is within limits.
        
        Args:
            position_size_usd: Position size in USD
            
        Returns:
            Tuple of (allowed, error_message)
        """
        if position_size_usd > self.max_position_size_usd:
            return False, f"Position size ${position_size_usd:,.2f} exceeds limit ${self.max_position_size_usd:,.2f}"
        return True, None
        
    def check_daily_loss(self, starting_capital: Decimal, current_value: Decimal) -> tuple[bool, Optional[str]]:
        """Check if daily loss is within limits.
        
        Args:
            starting_capital: Starting capital for the day
            current_value: Current portfolio value
            
        Returns:
            Tuple of (allowed, error_message)
        """
        # Update date tracking
        today = date.today()
        if today != self.current_date:
            self.daily_pnl = {}
            self.current_date = today
            
        daily_loss = starting_capital - current_value
        
        # Check absolute loss limit
        if daily_loss > self.max_daily_loss_usd:
            return False, f"Daily loss ${daily_loss:,.2f} exceeds limit ${self.max_daily_loss_usd:,.2f}"
            
        # Check percentage loss limit
        if starting_capital > 0:
            loss_percent = daily_loss / starting_capital
            if loss_percent > self.max_daily_loss_percent:
                return False, f"Daily loss {loss_percent*100:.2f}% exceeds limit {self.max_daily_loss_percent*100:.2f}%"
                
        return True, None
        
    def record_trade_pnl(self, pnl: Decimal):
        """Record P&L from a trade.
        
        Args:
            pnl: Profit/loss from the trade
        """
        today = date.today()
        if today not in self.daily_pnl:
            self.daily_pnl[today] = Decimal('0')
        self.daily_pnl[today] += pnl
        
    def get_daily_pnl(self, target_date: Optional[date] = None) -> Decimal:
        """Get daily P&L for a date.
        
        Args:
            target_date: Date to check (default: today)
            
        Returns:
            Daily P&L
        """
        target_date = target_date or date.today()
        return self.daily_pnl.get(target_date, Decimal('0'))

