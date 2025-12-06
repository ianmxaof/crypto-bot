"""Script to run backtests."""

import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from backtesting.backtester import Backtester
from backtesting.reporter import BacktestReporter
from strategies.funding_rate import FundingRateStrategy
from utils.logger import setup_logging


def main():
    """Run a backtest."""
    setup_logging(log_level="INFO")
    
    # Configuration
    initial_capital = Decimal('1000')
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    # Use historical data directory from settings
    data_dir = settings.HISTORICAL_DATA_DIR
    
    print("=" * 80)
    print("CRYPTO BOT BACKTEST")
    print("=" * 80)
    print(f"Strategy: Funding Rate Arbitrage")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Data Directory: {data_dir}")
    print("=" * 80)
    print()
    
    # Create strategy
    strategy = FundingRateStrategy()
    
    # Create backtester
    backtester = Backtester(
        strategy=strategy,
        initial_capital=initial_capital,
        data_dir=data_dir,
        start_date=start_date,
        end_date=end_date
    )
    
    # Run backtest
    print("Running backtest...")
    results = backtester.run()
    
    # Generate report
    print("\n")
    reporter = BacktestReporter()
    report = reporter.generate_report(results)
    print(report)
    
    # Save report
    report_path = Path("reports") / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    reporter.generate_report(results, report_path)
    
    print(f"\nFull report saved to: {report_path}")


if __name__ == "__main__":
    main()

