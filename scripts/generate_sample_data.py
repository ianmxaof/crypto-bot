"""Generate sample data for dashboard testing."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import random

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory.chrono import ChronologicalMemory
from config.settings import settings

# Ensure memory directory exists
settings.MEMORY_DIR.mkdir(parents=True, exist_ok=True)

memory = ChronologicalMemory(
    namespace="crypto_pnl",
    persist_path=settings.MEMORY_DIR / "crypto_pnl.json"
)


def generate_sample_data(days: int = 7, trades_per_day: int = 10):
    """Generate sample trading data for testing.
    
    Args:
        days: Number of days of data to generate
        trades_per_day: Number of trades per day
    """
    print(f"Generating {days} days of sample data ({trades_per_day} trades/day)...")
    
    agents = ["funding_rate_farmer_v1", "mev_watcher", "hyperliquid_lp"]
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "PEPE/USDT"]
    
    start_time = datetime.now(timezone.utc) - timedelta(days=days)
    current_balance = float(settings.SIMULATION_STARTING_BALANCE)
    cumulative_pnl = 0.0
    
    for day in range(days):
        for trade_num in range(trades_per_day):
            # Calculate timestamp
            hours_offset = (day * 24) + (trade_num * (24 / trades_per_day))
            timestamp = start_time + timedelta(hours=hours_offset)
            
            # Random trade
            agent = random.choice(agents)
            symbol = random.choice(symbols)
            side = random.choice(["buy", "sell"])
            
            # Generate PnL (slightly positive bias)
            pnl = random.uniform(-50, 100)
            cumulative_pnl += pnl
            current_balance += pnl
            
            # Create entry
            entry = {
                "timestamp": timestamp.isoformat(),
                "agent": agent,
                "symbol": symbol,
                "side": side,
                "pnl": pnl,
                "profit": pnl,  # Alias
                "balance": current_balance,
                "total_value": current_balance,
                "size": random.uniform(0.01, 1.0),
                "price": random.uniform(100, 100000),
                "trade_id": f"trade_{day}_{trade_num}",
            }
            
            memory.append(entry)
    
    print(f"✅ Generated {days * trades_per_day} trades")
    print(f"   Final balance: ${current_balance:,.2f}")
    print(f"   Total P&L: ${cumulative_pnl:,.2f}")
    print(f"   Data saved to: {memory.persist_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sample data for dashboard")
    parser.add_argument("--days", type=int, default=7, help="Number of days of data")
    parser.add_argument("--trades", type=int, default=10, help="Trades per day")
    
    args = parser.parse_args()
    
    generate_sample_data(days=args.days, trades_per_day=args.trades)

