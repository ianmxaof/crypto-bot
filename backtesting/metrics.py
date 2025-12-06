"""Calculate performance metrics from backtest results."""

import logging
from typing import List, Dict
from decimal import Decimal
import math

logger = logging.getLogger(__name__)


class BacktestMetrics:
    """Calculate comprehensive performance metrics."""
    
    def __init__(self, initial_capital: Decimal):
        """Initialize metrics calculator.
        
        Args:
            initial_capital: Starting capital
        """
        self.initial_capital = initial_capital
        
    def calculate(self, equity_curve: List[Decimal], returns: List[Decimal],
                  trades: List[Dict]) -> Dict:
        """Calculate all metrics from backtest data.
        
        Args:
            equity_curve: List of portfolio values over time
            returns: List of periodic returns
            trades: List of trade dictionaries
            
        Returns:
            Dictionary of calculated metrics
        """
        if not equity_curve:
            return {}
            
        final_value = equity_curve[-1]
        total_return = (final_value - self.initial_capital) / self.initial_capital
        
        # Calculate drawdown
        max_dd = self._calculate_max_drawdown(equity_curve)
        
        # Calculate Sharpe ratio
        sharpe = self._calculate_sharpe(returns)
        
        # Calculate Sortino ratio (downside deviation only)
        sortino = self._calculate_sortino(returns)
        
        # Trade statistics
        trade_stats = self._calculate_trade_stats(trades)
        
        return {
            "initial_capital": float(self.initial_capital),
            "final_value": float(final_value),
            "total_return": float(total_return),
            "total_return_pct": float(total_return * 100),
            "max_drawdown": float(max_dd),
            "max_drawdown_pct": float(max_dd * 100),
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            **trade_stats
        }
        
    def _calculate_max_drawdown(self, equity_curve: List[Decimal]) -> Decimal:
        """Calculate maximum drawdown.
        
        Args:
            equity_curve: List of portfolio values
            
        Returns:
            Maximum drawdown as decimal (0.1 = 10%)
        """
        if not equity_curve:
            return Decimal('0')
            
        peak = equity_curve[0]
        max_dd = Decimal('0')
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak
            if dd > max_dd:
                max_dd = dd
                
        return max_dd
        
    def _calculate_sharpe(self, returns: List[Decimal], risk_free_rate: Decimal = Decimal('0.02')) -> float:
        """Calculate Sharpe ratio.
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Annual risk-free rate (default 2%)
            
        Returns:
            Sharpe ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
            
        returns_float = [float(r) for r in returns]
        mean_return = sum(returns_float) / len(returns_float)
        
        # Annualized return (assuming returns are daily)
        annual_return = mean_return * 365
        
        # Calculate standard deviation
        variance = sum((r - mean_return) ** 2 for r in returns_float) / (len(returns_float) - 1)
        std_dev = math.sqrt(variance)
        annual_std = std_dev * math.sqrt(365)
        
        if annual_std == 0:
            return 0.0
            
        sharpe = (annual_return - float(risk_free_rate)) / annual_std
        return sharpe
        
    def _calculate_sortino(self, returns: List[Decimal], risk_free_rate: Decimal = Decimal('0.02')) -> float:
        """Calculate Sortino ratio (downside deviation only).
        
        Args:
            returns: List of periodic returns
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Sortino ratio
        """
        if not returns or len(returns) < 2:
            return 0.0
            
        returns_float = [float(r) for r in returns]
        mean_return = sum(returns_float) / len(returns_float)
        annual_return = mean_return * 365
        
        # Downside deviation (only negative returns)
        downside_returns = [min(0, r - mean_return) for r in returns_float]
        downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_std = math.sqrt(downside_variance) * math.sqrt(365)
        
        if downside_std == 0:
            return 0.0
            
        sortino = (annual_return - float(risk_free_rate)) / downside_std
        return sortino
        
    def _calculate_trade_stats(self, trades: List[Dict]) -> Dict:
        """Calculate trade statistics.
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            Dictionary of trade statistics
        """
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0
            }
            
        winning_trades = [t for t in trades if t.get("pnl", 0) > 0]
        losing_trades = [t for t in trades if t.get("pnl", 0) < 0]
        
        total_gross_profit = sum(t.get("pnl", 0) for t in winning_trades)
        total_gross_loss = abs(sum(t.get("pnl", 0) for t in losing_trades))
        
        profit_factor = total_gross_profit / total_gross_loss if total_gross_loss > 0 else 0.0
        
        return {
            "total_trades": len(trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(trades) if trades else 0.0,
            "avg_win": total_gross_profit / len(winning_trades) if winning_trades else 0.0,
            "avg_loss": -total_gross_loss / len(losing_trades) if losing_trades else 0.0,
            "profit_factor": profit_factor,
            "largest_win": max((t.get("pnl", 0) for t in winning_trades), default=0.0),
            "largest_loss": min((t.get("pnl", 0) for t in losing_trades), default=0.0)
        }

