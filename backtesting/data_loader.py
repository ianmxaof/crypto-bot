"""Load historical data for backtesting."""

import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads historical data for backtesting."""
    
    def __init__(self, data_dir: Path):
        """Initialize data loader.
        
        Args:
            data_dir: Directory containing historical data
        """
        self.data_dir = Path(data_dir)
        self.funding_rates_dir = self.data_dir / "funding_rates"
        self.prices_dir = self.data_dir / "prices"
        
    def load_funding_rates(self, symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load historical funding rates for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with columns: timestamp, rate
        """
        # Normalize symbol for filename
        filename = symbol.replace("/", "_").replace(":", "_") + ".csv"
        filepath = self.funding_rates_dir / filename
        
        if not filepath.exists():
            logger.warning(f"Funding rate file not found: {filepath}")
            return pd.DataFrame(columns=["timestamp", "rate"])
            
        try:
            df = pd.read_csv(filepath)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]
            df = df.sort_values("timestamp")
            return df
        except Exception as e:
            logger.error(f"Error loading funding rates from {filepath}: {e}")
            return pd.DataFrame(columns=["timestamp", "rate"])
            
    def load_prices(self, symbol: str, start_date: datetime, end_date: datetime,
                   timeframe: str = "1h") -> pd.DataFrame:
        """Load historical price data for a symbol.
        
        Args:
            symbol: Trading symbol
            start_date: Start date
            end_date: End date
            timeframe: Timeframe (1h, 4h, 1d, etc.)
            
        Returns:
            DataFrame with OHLCV columns
        """
        filename = f"{symbol.replace('/', '_').replace(':', '_')}_{timeframe}.parquet"
        filepath = self.prices_dir / filename
        
        if not filepath.exists():
            # Try CSV as fallback
            csv_path = self.prices_dir / filename.replace(".parquet", ".csv")
            if csv_path.exists():
                filepath = csv_path
            else:
                logger.warning(f"Price file not found: {filepath}")
                return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
                
        try:
            if filepath.suffix == ".parquet":
                df = pd.read_parquet(filepath)
            else:
                df = pd.read_csv(filepath)
                
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]
                df = df.sort_values("timestamp")
                
            return df
        except Exception as e:
            logger.error(f"Error loading prices from {filepath}: {e}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
            
    def get_available_symbols(self) -> List[str]:
        """Get list of symbols with available data.
        
        Returns:
            List of available symbols
        """
        symbols = set()
        
        # From funding rates
        if self.funding_rates_dir.exists():
            for file in self.funding_rates_dir.glob("*.csv"):
                symbol = file.stem.replace("_", "/")
                symbols.add(symbol)
                
        # From prices
        if self.prices_dir.exists():
            for file in self.prices_dir.glob("*.csv"):
                symbol = file.stem.split("_")[0].replace("_", "/")
                symbols.add(symbol)
            for file in self.prices_dir.glob("*.parquet"):
                symbol = file.stem.split("_")[0].replace("_", "/")
                symbols.add(symbol)
                
        return sorted(list(symbols))

