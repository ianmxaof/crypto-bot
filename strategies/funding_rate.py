"""Core funding rate arbitrage strategy logic."""

import logging
from typing import List, Tuple, Dict
from decimal import Decimal

from exchanges.base import BaseExchange, FundingRate

logger = logging.getLogger(__name__)


class FundingRateStrategy:
    """Core logic for funding rate arbitrage."""
    
    def __init__(self, min_funding_rate: Decimal = Decimal('0.0001')):
        """Initialize funding rate strategy.
        
        Args:
            min_funding_rate: Minimum funding rate to consider (0.01% = 0.0001)
        """
        self.min_funding_rate = min_funding_rate
        
    def get_top_funding_coins(self, funding_rates: Dict[str, FundingRate], 
                              top_n: int = 3, min_volume: Decimal = Decimal('0')) -> List[Tuple[str, FundingRate, Decimal]]:
        """Get top N coins by funding rate with volume weighting.
        
        Args:
            funding_rates: Dictionary of symbol -> FundingRate
            top_n: Number of top coins to return
            min_volume: Minimum volume filter (not used in current implementation)
            
        Returns:
            List of (symbol, FundingRate, score) tuples sorted by score
        """
        candidates = []
        
        for symbol, rate_data in funding_rates.items():
            # Filter USDT pairs only
            if not symbol.endswith('USDT') and 'USDT' not in symbol:
                continue
                
            rate = rate_data.rate
            if rate <= self.min_funding_rate:
                continue
                
            # Simple scoring: funding rate * (1 + volume_bias)
            # In real implementation, would include actual volume data
            score = rate * Decimal('1.5')  # Placeholder volume bias
            
            candidates.append((symbol, rate_data, score))
            
        # Sort by score descending
        candidates.sort(key=lambda x: x[2], reverse=True)
        
        return candidates[:top_n]
        
    def calculate_allocation(self, total_capital: Decimal, num_coins: int, 
                            allocation_percent: Decimal = Decimal('0.95')) -> Decimal:
        """Calculate allocation per coin.
        
        Args:
            total_capital: Total capital available
            num_coins: Number of coins to allocate to
            allocation_percent: Percentage of capital to deploy (0.95 = 95%)
            
        Returns:
            Allocation amount per coin
        """
        deployable = total_capital * allocation_percent
        return deployable / Decimal(str(num_coins))
        
    def should_rebalance(self, current_positions: Dict[str, Decimal], 
                        target_positions: Dict[str, Decimal],
                        drift_threshold: Decimal = Decimal('0.02')) -> bool:
        """Check if positions need rebalancing.
        
        Args:
            current_positions: Current position sizes by symbol
            target_positions: Target position sizes by symbol
            drift_threshold: Maximum allowed drift (0.02 = 2%)
            
        Returns:
            True if rebalancing needed
        """
        for symbol in target_positions:
            target = target_positions[symbol]
            current = current_positions.get(symbol, Decimal('0'))
            
            if target == Decimal('0'):
                if current != Decimal('0'):
                    return True
                continue
                
            drift = abs(current - target) / target
            if drift > drift_threshold:
                return True
                
        return False

