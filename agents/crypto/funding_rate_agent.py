"""Funding rate arbitrage agent with hot-coin rotation."""

import asyncio
import logging
from typing import Dict, Set
from decimal import Decimal
from datetime import datetime, timezone

from core.agent_base import Agent, AgentConfig
from core.event_bus import event_bus
from exchanges.base import BaseExchange
from strategies.funding_rate import FundingRateStrategy

logger = logging.getLogger(__name__)


class FundingRateAgent(Agent):
    """Agent that farms funding rates using delta-neutral hedging."""
    
    def __init__(self, exchange: BaseExchange, allocation_percent: Decimal = Decimal('0.95')):
        """Initialize funding rate agent.
        
        Args:
            exchange: Exchange client instance
            allocation_percent: Percentage of capital to allocate (0.95 = 95%)
        """
        super().__init__(AgentConfig(
            name="funding_rate_farmer_v1",
            version="0.4.2",
            description="Delta-neutral perpetual funding collector + daily hot-coin rotation"
        ))
        self.exchange = exchange
        self.allocation_percent = allocation_percent
        self.strategy = FundingRateStrategy()
        self.active_hedges: Set[str] = set()
        self.top_n_coins = 3
        
    async def run(self):
        """Main agent loop."""
        logger.info(f"FundingRateAgent started - watching top {self.top_n_coins} funding coins")
        
        while not self._shutdown_event.is_set():
            try:
                # Get top funding coins
                funding_rates = await self.exchange.fetch_funding_rates()
                top_coins_data = self.strategy.get_top_funding_coins(funding_rates, self.top_n_coins)
                
                if not top_coins_data:
                    logger.warning("No suitable funding opportunities found")
                    await asyncio.sleep(3600)  # Wait 1 hour
                    continue
                    
                top_coins = [symbol for symbol, _, _ in top_coins_data]
                
                # Log current top coins
                rates_str = ", ".join([f"{sym}: {rate.rate:.4%}" for sym, rate, _ in top_coins_data])
                logger.info(f"Top {self.top_n_coins} funding coins: {rates_str}")
                
                # Check if we need to rebalance
                if set(top_coins) != self.active_hedges:
                    logger.info(f"New hot coins detected! Rebalancing portfolio...")
                    await self._close_all_hedges()
                    await asyncio.sleep(10)  # Wait for positions to close
                    
                    # Open new hedges
                    for symbol in top_coins:
                        await self._open_hedge(symbol)
                else:
                    logger.debug("Still farming the best coins. No rebalancing needed.")
                    
                # Wait 24 hours before next rotation check
                logger.info("Funding cycle complete. Next check in 24 hours.")
                await asyncio.sleep(24 * 3600)
                
            except Exception as e:
                logger.error(f"Error in funding rate agent cycle: {e}", exc_info=True)
                await asyncio.sleep(300)  # Wait 5 minutes before retry
                
    async def _close_all_hedges(self):
        """Close all active hedges."""
        logger.info(f"Closing {len(self.active_hedges)} active hedges...")
        
        for symbol in list(self.active_hedges):
            try:
                # Close perpetual position
                perp_symbol = symbol if ':USDT' in symbol else f"{symbol}:USDT"
                await self.exchange.close_position(perp_symbol)
                
                # Close spot position (sell)
                await self.exchange.create_market_order(symbol, 'sell', Decimal('1000'))  # Will sell all
                
                logger.info(f"Closed hedge for {symbol}")
            except Exception as e:
                logger.error(f"Error closing hedge for {symbol}: {e}")
                
        self.active_hedges.clear()
        
    async def _open_hedge(self, symbol: str):
        """Open a delta-neutral hedge for a symbol.
        
        Args:
            symbol: Symbol to hedge (e.g., 'BTC/USDT')
        """
        try:
            # Get balance
            balance = await self.exchange.fetch_balance('USDT')
            if 'USDT' not in balance:
                logger.error("No USDT balance available")
                return
                
            usdt_balance = balance['USDT'].free
            if usdt_balance < Decimal('10'):
                logger.error(f"Insufficient USDT balance: {usdt_balance}")
                return
                
            # Calculate allocation per coin
            amount_per_coin = self.strategy.calculate_allocation(
                usdt_balance,
                self.top_n_coins,
                self.allocation_percent
            )
            
            if amount_per_coin < Decimal('10'):
                logger.warning(f"Allocation per coin too small: {amount_per_coin}")
                return
                
            logger.info(f"Opening hedge on {symbol} with ~{amount_per_coin:.1f} USDT")
            
            # Normalize symbol format
            # Handle different symbol formats
            base_symbol = symbol.replace('USDT', '').replace('/', '').replace(':', '')
            spot_symbol = f"{base_symbol}/USDT"
            
            # For perpetuals, try different formats
            perp_symbol = f"{base_symbol}:USDT"
            # Some exchanges use different formats, try alternative
            perp_alt = f"{base_symbol}/USDT:USDT"  # Binance format
            
            # Use the format that works with the exchange
            if hasattr(self.exchange, 'is_simulation') and self.exchange.is_simulation():
                # Mock exchange uses simple format
                perp_symbol = spot_symbol  # Mock uses same format
            
            # Buy spot
            try:
                spot_order = await self.exchange.create_market_order(
                    spot_symbol,
                    'buy',
                    amount_per_coin
                )
                logger.info(f"Opened spot long: {spot_order.id}")
            except Exception as e:
                logger.error(f"Failed to open spot position: {e}")
                return
                
            # Short perpetual (1x leverage for delta-neutral)
            try:
                await self.exchange.set_leverage(1, perp_symbol)
                perp_order = await self.exchange.create_market_order(
                    perp_symbol,
                    'sell',
                    amount_per_coin
                )
                logger.info(f"Opened perpetual short: {perp_order.id}")
            except Exception as e:
                logger.error(f"Failed to open perpetual position: {e}")
                # Try to close spot to avoid unhedged position
                try:
                    await self.exchange.create_market_order(spot_symbol, 'sell', amount_per_coin)
                except:
                    pass
                return
                
            self.active_hedges.add(symbol)
            
            # Publish event
            event_bus.publish("funding:hedge_opened", {
                "symbol": symbol,
                "amount_usdt": float(amount_per_coin),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, source=self.config.name)
            
            logger.info(f"Successfully opened delta-neutral hedge for {symbol}")
            
        except Exception as e:
            logger.error(f"Error opening hedge for {symbol}: {e}", exc_info=True)
            
    async def on_stop(self):
        """Cleanup on agent stop."""
        await self._close_all_hedges()
        if hasattr(self.exchange, 'close'):
            await self.exchange.close()

