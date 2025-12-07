"""Market data provider for fetching real-time and historical market data.

Supports CoinGecko API (free tier, no key required for basic usage) for
historical OHLCV data and live price feeds.
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
import aiohttp
import time

logger = logging.getLogger(__name__)

# CoinGecko API endpoints
COINGECKO_API_BASE = "https://api.coingecko.com/api/v3"
COINGECKO_RATE_LIMIT = 10  # Free tier: 10-50 calls/minute


@dataclass
class Candle:
    """OHLCV candle data."""
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


class MarketDataProvider:
    """Provider for fetching market data from various sources."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize market data provider.
        
        Args:
            api_key: Optional API key for premium features (not required for basic CoinGecko)
        """
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(minutes=5)  # Cache prices for 5 minutes
        self._last_call_time = 0.0
        self._min_call_interval = 0.1  # Rate limiting: 100ms between calls
        
        # Symbol mapping: exchange symbols to CoinGecko IDs
        self._symbol_map = {
            "BTC/USDT": "bitcoin",
            "BTCUSDT": "bitcoin",
            "ETH/USDT": "ethereum",
            "ETHUSDT": "ethereum",
            "SOL/USDT": "solana",
            "SOLUSDT": "solana",
            "PEPE/USDT": "pepe",
            "PEPEUSDT": "pepe",
            "WIF/USDT": "dogwifcoin",
            "WIFUSDT": "dogwifcoin",
            "BONK/USDT": "bonk",
            "BONKUSDT": "bonk",
            "DOGE/USDT": "dogecoin",
            "DOGEUSDT": "dogecoin",
        }
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format (remove /, convert to CoinGecko ID).
        
        Args:
            symbol: Exchange symbol (e.g., "BTC/USDT" or "BTCUSDT")
            
        Returns:
            CoinGecko ID or original symbol if not mapped
        """
        # Try direct mapping
        if symbol in self._symbol_map:
            return self._symbol_map[symbol]
        
        # Try removing / separator
        normalized = symbol.replace("/", "").upper()
        if normalized in self._symbol_map:
            return self._symbol_map[normalized]
        
        # Try with /USDT
        if not symbol.endswith("/USDT") and not symbol.endswith("USDT"):
            test_symbol = f"{symbol}/USDT"
            if test_symbol in self._symbol_map:
                return self._symbol_map[test_symbol]
        
        # Return original if no mapping found
        logger.warning(f"Symbol {symbol} not in mapping, using as-is")
        return symbol.lower()
    
    async def _rate_limit(self):
        """Apply rate limiting to API calls."""
        now = time.time()
        elapsed = now - self._last_call_time
        if elapsed < self._min_call_interval:
            await asyncio.sleep(self._min_call_interval - elapsed)
        self._last_call_time = time.time()
    
    async def get_current_price(self, symbol: str) -> Optional[Decimal]:
        """Get current price for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            
        Returns:
            Current price as Decimal, or None if fetch fails
        """
        cache_key = f"price_{symbol}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.now(timezone.utc) - cached_time < self._cache_ttl:
                return Decimal(str(cached_data))
        
        try:
            await self._rate_limit()
            coin_id = self._normalize_symbol(symbol)
            
            session = await self._get_session()
            url = f"{COINGECKO_API_BASE}/simple/price"
            params = {
                "ids": coin_id,
                "vs_currencies": "usd",
                "include_24hr_change": "false"
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if coin_id in data and "usd" in data[coin_id]:
                        price = Decimal(str(data[coin_id]["usd"]))
                        # Cache the result
                        self._cache[cache_key] = (price, datetime.now(timezone.utc))
                        return price
                    else:
                        logger.warning(f"Price data not found for {coin_id}")
                        return None
                else:
                    logger.warning(f"CoinGecko API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching current price for {symbol}: {e}")
            return None
    
    async def get_historical_ohlcv(
        self,
        symbol: str,
        days: int = 30,
        interval: str = "4h"
    ) -> List[Candle]:
        """Get historical OHLCV (candlestick) data.
        
        Args:
            symbol: Trading symbol (e.g., "BTC/USDT")
            days: Number of days of history to fetch
            interval: Candle interval ("1h", "4h", "1d")
            
        Returns:
            List of Candle objects, sorted by timestamp
        """
        try:
            await self._rate_limit()
            coin_id = self._normalize_symbol(symbol)
            
            # Map interval to CoinGecko days parameter
            # CoinGecko returns daily data, we'll need to aggregate if needed
            session = await self._get_session()
            url = f"{COINGECKO_API_BASE}/coins/{coin_id}/ohlc"
            params = {
                "vs_currency": "usd",
                "days": str(days)
            }
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    candles = []
                    
                    for item in data:
                        # CoinGecko OHLC format: [timestamp_ms, open, high, low, close]
                        timestamp_ms, open_price, high_price, low_price, close_price = item
                        timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
                        
                        candles.append(Candle(
                            timestamp=timestamp,
                            open=Decimal(str(open_price)),
                            high=Decimal(str(high_price)),
                            low=Decimal(str(low_price)),
                            close=Decimal(str(close_price)),
                            volume=Decimal('0')  # CoinGecko free tier doesn't include volume
                        ))
                    
                    # Sort by timestamp
                    candles.sort(key=lambda x: x.timestamp)
                    logger.info(f"Fetched {len(candles)} candles for {symbol} ({days} days)")
                    return candles
                else:
                    logger.warning(f"CoinGecko API error fetching OHLCV: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching historical OHLCV for {symbol}: {e}")
            return []
    
    async def subscribe_live_price(
        self,
        symbol: str,
        callback: Callable[[Decimal], None],
        interval_seconds: int = 60
    ) -> 'PriceSubscription':
        """Subscribe to live price updates (polling-based).
        
        Args:
            symbol: Trading symbol
            callback: Function to call with new price
            interval_seconds: Polling interval in seconds
            
        Returns:
            PriceSubscription object that can be cancelled
        """
        subscription = PriceSubscription(symbol, callback, interval_seconds, self)
        await subscription.start()
        return subscription


class PriceSubscription:
    """Subscription for live price updates."""
    
    def __init__(
        self,
        symbol: str,
        callback: Callable[[Decimal], None],
        interval_seconds: int,
        provider: MarketDataProvider
    ):
        self.symbol = symbol
        self.callback = callback
        self.interval_seconds = interval_seconds
        self.provider = provider
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the subscription."""
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Started live price subscription for {self.symbol}")
    
    async def _poll_loop(self):
        """Poll for price updates."""
        while self._running:
            try:
                price = await self.provider.get_current_price(self.symbol)
                if price:
                    self.callback(price)
                await asyncio.sleep(self.interval_seconds)
            except Exception as e:
                logger.error(f"Error in price subscription for {self.symbol}: {e}")
                await asyncio.sleep(self.interval_seconds)
    
    async def stop(self):
        """Stop the subscription."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Stopped live price subscription for {self.symbol}")


# Global instance (singleton pattern)
_provider_instance: Optional[MarketDataProvider] = None


def get_market_data_provider(api_key: Optional[str] = None) -> MarketDataProvider:
    """Get global market data provider instance.
    
    Args:
        api_key: Optional API key
        
    Returns:
        MarketDataProvider instance
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = MarketDataProvider(api_key=api_key)
    return _provider_instance

