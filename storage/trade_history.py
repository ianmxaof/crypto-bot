"""Persist trade history to storage."""

import json
import logging
from typing import List, Dict
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class TradeHistoryStorage:
    """Store and retrieve trade history."""
    
    def __init__(self, storage_path: Path):
        """Initialize trade history storage.
        
        Args:
            storage_path: Path to store trade history
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
    def save_trade(self, trade: Dict):
        """Save a trade to history.
        
        Args:
            trade: Trade dictionary
        """
        timestamp = trade.get("timestamp", datetime.now().isoformat())
        date_str = timestamp.split("T")[0]  # Extract date
        
        # Save to daily file
        filename = f"trades_{date_str}.json"
        filepath = self.storage_path / filename
        
        # Load existing trades for the day
        trades = self._load_trades_for_date(date_str)
        trades.append(trade)
        
        # Save back
        try:
            with open(filepath, 'w') as f:
                json.dump(trades, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
            
    def load_trades(self, start_date: str, end_date: str) -> List[Dict]:
        """Load trades for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of trades
        """
        all_trades = []
        # Load trades for each day in range
        # Simplified - would use date range iteration in production
        return all_trades
        
    def _load_trades_for_date(self, date_str: str) -> List[Dict]:
        """Load trades for a specific date.
        
        Args:
            date_str: Date string (YYYY-MM-DD)
            
        Returns:
            List of trades
        """
        filename = f"trades_{date_str}.json"
        filepath = self.storage_path / filename
        
        if not filepath.exists():
            return []
            
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load trades for {date_str}: {e}")
            return []

