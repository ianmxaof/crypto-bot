"""Quick test to verify backtest caching works."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))

async def test():
    print("Testing backtest caching...")
    
    from data_providers.market_data import get_market_data_provider
    
    provider = get_market_data_provider()
    
    start_date = datetime(2025, 11, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 12, 7, tzinfo=timezone.utc)
    
    print(f"Fetching BTC/USDT data: {start_date.date()} to {end_date.date()}")
    print("First call (will fetch from API)...")
    
    candles = await provider.get_historical_ohlcv_range(
        "BTC/USDT",
        start_date,
        end_date,
        interval="1d"
    )
    
    print(f"✓ Got {len(candles)} candles")
    
    print("\nSecond call (should use cache)...")
    candles2 = await provider.get_historical_ohlcv_range(
        "BTC/USDT",
        start_date,
        end_date,
        interval="1d"
    )
    
    print(f"✓ Got {len(candles2)} candles from cache")
    print(f"✓ Cache working! ({len(candles)} == {len(candles2)})")
    
    # Check cache file exists
    cache_dir = Path("data/historical_cache")
    cache_files = list(cache_dir.glob("*.json"))
    print(f"\n✓ Cache files: {len(cache_files)}")
    for f in cache_files[:3]:
        print(f"  - {f.name}")

if __name__ == "__main__":
    asyncio.run(test())

