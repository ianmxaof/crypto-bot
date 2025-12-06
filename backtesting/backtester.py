"""Main backtesting engine."""

import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path

from backtesting.data_loader import DataLoader
from backtesting.metrics import BacktestMetrics
from exchanges.mock_exchange import MockExchange
from strategies.funding_rate import FundingRateStrategy

logger = logging.getLogger(__name__)


class Backtester:
    """Main backtesting engine for strategy validation."""
    
    def __init__(self, strategy, initial_capital: Decimal, data_dir: Path,
                 start_date: datetime, end_date: datetime):
        """Initialize backtester.
        
        Args:
            strategy: Strategy instance to backtest
            initial_capital: Starting capital
            data_dir: Directory with historical data
            start_date: Backtest start date
            end_date: Backtest end date
        """
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.data_loader = DataLoader(data_dir)
        self.start_date = start_date
        self.end_date = end_date
        self.metrics_calc = BacktestMetrics(initial_capital)
        
    def run(self) -> Dict:
        """Run the backtest.
        
        Returns:
            Dictionary with backtest results and metrics
        """
        logger.info(f"Starting backtest: {self.start_date} to {self.end_date}")
        logger.info(f"Initial capital: ${self.initial_capital:,.2f}")
        
        # Create mock exchange for backtest
        exchange = MockExchange(
            starting_balance=self.initial_capital,
            fee_rate=Decimal('0.001')
        )
        
        # Load historical data
        symbols = self.data_loader.get_available_symbols()
        if not symbols:
            logger.warning("No historical data found, using default prices")
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
            
        # Get funding rates for all symbols
        funding_data = {}
        for symbol in symbols[:10]:  # Limit to first 10 for performance
            rates = self.data_loader.load_funding_rates(symbol, self.start_date, self.end_date)
            if not rates.empty:
                funding_data[symbol] = rates
                
        if not funding_data:
            logger.warning("No funding rate data found, creating synthetic data")
            # Create synthetic funding rates for testing
            funding_data = self._create_synthetic_funding_rates()
            
        # Run simulation day by day
        current_date = self.start_date
        equity_curve = [self.initial_capital]
        returns = []
        trades = []
        
        positions = {}
        
        while current_date <= self.end_date:
            # Get funding rates for this date
            daily_rates = {}
            for symbol, df in funding_data.items():
                # Get rate closest to current date
                relevant = df[df["timestamp"] <= current_date]
                if not relevant.empty:
                    rate_row = relevant.iloc[-1]
                    daily_rates[symbol] = Decimal(str(rate_row["rate"]))
                    
            if daily_rates:
                # Use strategy to select top coins
                from exchanges.base import FundingRate
                from datetime import timezone
                
                funding_rates_dict = {
                    sym: FundingRate(sym, rate, current_date, current_date)
                    for sym, rate in daily_rates.items()
                }
                
                top_coins_data = self.strategy.get_top_funding_coins(funding_rates_dict, top_n=3)
                
                # Update positions if needed
                new_symbols = {sym for sym, _, _ in top_coins_data}
                old_symbols = set(positions.keys())
                
                # Use asyncio to run async exchange operations
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    # Close old positions
                    for symbol in old_symbols - new_symbols:
                        try:
                            loop.run_until_complete(exchange.close_position(symbol))
                            positions.pop(symbol)
                        except Exception as e:
                            logger.debug(f"Error closing position {symbol}: {e}")
                            
                    # Open new positions
                    for symbol, rate_data, score in top_coins_data:
                        if symbol not in positions:
                            try:
                                # Allocate capital
                                balance = loop.run_until_complete(exchange.fetch_balance("USDT"))
                                if "USDT" in balance and balance["USDT"].free > Decimal('100'):
                                    amount_per_coin = balance["USDT"].free / Decimal('3')
                                    
                                    # Buy spot
                                    loop.run_until_complete(exchange.create_market_order(symbol, "buy", amount_per_coin))
                                    # Short perpetual
                                    loop.run_until_complete(exchange.set_leverage(1, symbol))
                                    loop.run_until_complete(exchange.create_market_order(symbol, "sell", amount_per_coin))
                                    
                                    positions[symbol] = current_date
                            except Exception as e:
                                logger.debug(f"Error opening position {symbol}: {e}")
                finally:
                    loop.close()
                            
            # Record equity (sync call)
            total_value = exchange.get_total_value()
            equity_curve.append(total_value)
            
            if len(equity_curve) > 1:
                prev_value = equity_curve[-2]
                if prev_value > 0:
                    period_return = (total_value - prev_value) / prev_value
                    returns.append(period_return)
                    
            # Move to next day
            current_date += timedelta(days=1)
            
        # Calculate metrics
        metrics = self.metrics_calc.calculate(equity_curve, returns, trades)
        
        logger.info(f"Backtest complete. Final value: ${equity_curve[-1]:,.2f}")
        
        return {
            "metrics": metrics,
            "equity_curve": [float(v) for v in equity_curve],
            "trades": trades,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat()
        }
        
    def _create_synthetic_funding_rates(self) -> Dict:
        """Create synthetic funding rates for testing when no data available."""
        import pandas as pd
        
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT", "WIF/USDT"]
        dates = pd.date_range(self.start_date, self.end_date, freq="8H")
        
        funding_data = {}
        for symbol in symbols:
            # Generate synthetic rates (higher for meme coins)
            base_rate = Decimal('0.0012') if "PEPE" in symbol or "WIF" in symbol else Decimal('0.0001')
            rates = [base_rate * Decimal(str(1 + 0.5 * (i % 10) / 10)) for i in range(len(dates))]
            
            df = pd.DataFrame({
                "timestamp": dates,
                "rate": [float(r) for r in rates]
            })
            funding_data[symbol] = df
            
        return funding_data

