"""OKX exchange client implementation."""

import ccxt.pro as ccxtpro
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone

from .base import BaseExchange, Balance, Position, Order, FundingRate, ExchangeError

logger = logging.getLogger(__name__)


class OKXExchange(BaseExchange):
    """OKX exchange client using ccxt-pro."""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False, passphrase: Optional[str] = None):
        super().__init__(api_key, api_secret, testnet)
        config = {
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
                'test': testnet
            }
        }
        if passphrase:
            config['password'] = passphrase
        self.client = ccxtpro.okx(config)
        
    async def fetch_balance(self, currency: Optional[str] = None) -> Dict[str, Balance]:
        """Fetch account balance."""
        try:
            balance_data = await self.client.fetch_balance({'type': 'spot'})
            balances = {}
            
            for curr in balance_data.get('total', {}):
                total = Decimal(str(balance_data['total'][curr]))
                free = Decimal(str(balance_data['free'].get(curr, 0)))
                used = total - free
                balances[curr] = Balance(curr, total, free, used)
                
            return balances
            
        except Exception as e:
            logger.error(f"Error fetching OKX balance: {e}")
            raise ExchangeError(f"Failed to fetch balance: {e}") from e
            
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Fetch open positions."""
        try:
            positions_data = await self.client.fetch_positions(symbols=[symbol] if symbol else None)
            positions = []
            
            for pos_data in positions_data:
                if float(pos_data.get('contracts', 0)) == 0:
                    continue
                    
                symbol_str = pos_data['symbol']
                size = Decimal(str(abs(pos_data.get('contracts', 0))))
                entry_price = Decimal(str(pos_data.get('entryPrice', 0)))
                side = 'long' if float(pos_data.get('contracts', 0)) > 0 else 'short'
                unrealized_pnl = Decimal(str(pos_data.get('unrealizedPnl', 0)))
                leverage = Decimal(str(pos_data.get('leverage', 1)))
                
                positions.append(Position(symbol_str, size, entry_price, side, unrealized_pnl, leverage))
                
            return positions
            
        except Exception as e:
            logger.error(f"Error fetching OKX positions: {e}")
            raise ExchangeError(f"Failed to fetch positions: {e}") from e
            
    async def create_market_order(self, symbol: str, side: str, amount: Decimal,
                                   params: Optional[Dict] = None) -> Order:
        """Create a market order."""
        try:
            params = params or {}
            order_data = await self.client.create_market_order(
                symbol,
                side,
                float(amount),
                None,
                params
            )
            return self._parse_order(order_data)
        except Exception as e:
            logger.error(f"Error creating OKX market order: {e}")
            raise ExchangeError(f"Failed to create order: {e}") from e
            
    async def create_limit_order(self, symbol: str, side: str, amount: Decimal, price: Decimal,
                                  params: Optional[Dict] = None) -> Order:
        """Create a limit order."""
        try:
            params = params or {}
            order_data = await self.client.create_limit_order(
                symbol,
                side,
                float(amount),
                float(price),
                params
            )
            return self._parse_order(order_data)
        except Exception as e:
            logger.error(f"Error creating OKX limit order: {e}")
            raise ExchangeError(f"Failed to create order: {e}") from e
            
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        try:
            await self.client.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            logger.error(f"Error canceling OKX order: {e}")
            raise ExchangeError(f"Failed to cancel order: {e}") from e
            
    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        """Fetch order by ID."""
        try:
            order_data = await self.client.fetch_order(order_id, symbol)
            return self._parse_order(order_data)
        except Exception as e:
            logger.error(f"Error fetching OKX order: {e}")
            raise ExchangeError(f"Failed to fetch order: {e}") from e
            
    async def fetch_funding_rates(self, symbols: Optional[List[str]] = None) -> Dict[str, FundingRate]:
        """Fetch funding rates for perpetuals."""
        try:
            funding_data = await self.client.fetch_funding_rates(symbols or [])
            rates = {}
            
            for symbol, data in funding_data.items():
                rate = Decimal(str(data.get('fundingRate', 0)))
                timestamp = datetime.fromtimestamp(data.get('timestamp', 0) / 1000, tz=timezone.utc)
                next_funding = None
                if 'fundingTimestamp' in data:
                    next_funding = datetime.fromtimestamp(data['fundingTimestamp'] / 1000, tz=timezone.utc)
                    
                rates[symbol] = FundingRate(symbol, rate, timestamp, next_funding)
                
            return rates
            
        except Exception as e:
            logger.error(f"Error fetching OKX funding rates: {e}")
            raise ExchangeError(f"Failed to fetch funding rates: {e}") from e
            
    async def set_leverage(self, leverage: int, symbol: str) -> bool:
        """Set leverage for a symbol."""
        try:
            await self.client.set_leverage(leverage, symbol)
            return True
        except Exception as e:
            logger.error(f"Error setting OKX leverage: {e}")
            raise ExchangeError(f"Failed to set leverage: {e}") from e
            
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker/price data."""
        try:
            return await self.client.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Error fetching OKX ticker: {e}")
            raise ExchangeError(f"Failed to fetch ticker: {e}") from e
            
    async def close_position(self, symbol: str, side: Optional[str] = None) -> bool:
        """Close an open position."""
        try:
            positions = await self.fetch_positions(symbol)
            for pos in positions:
                if side is None or pos.side == side:
                    close_side = 'sell' if pos.side == 'long' else 'buy'
                    await self.create_market_order(symbol, close_side, pos.size)
            return True
        except Exception as e:
            logger.error(f"Error closing OKX position: {e}")
            raise ExchangeError(f"Failed to close position: {e}") from e
            
    def _parse_order(self, order_data: Dict) -> Order:
        """Parse order data from exchange format."""
        return Order(
            id=str(order_data.get('id', '')),
            symbol=order_data.get('symbol', ''),
            side=order_data.get('side', '').lower(),
            type=order_data.get('type', '').lower(),
            amount=Decimal(str(order_data.get('amount', 0))),
            price=Decimal(str(order_data.get('price', 0))) if order_data.get('price') else None,
            status=order_data.get('status', 'unknown').lower(),
            filled=Decimal(str(order_data.get('filled', 0))),
            remaining=Decimal(str(order_data.get('remaining', 0))),
            timestamp=datetime.fromtimestamp(order_data.get('timestamp', 0) / 1000, tz=timezone.utc) if order_data.get('timestamp') else None
        )
        
    async def close(self):
        """Close exchange connection."""
        await self.client.close()

