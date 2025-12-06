"""MEV liquidation hunter agent."""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List

from core.agent_base import Agent, AgentConfig
from core.event_bus import event_bus
from core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class MEVWatcherAgent(Agent):
    """Agent that watches for MEV opportunities (liquidations, arbitrage, etc.)."""
    
    def __init__(self, min_profit_usd: Decimal = Decimal('15'), max_risk_per_shot: Decimal = Decimal('800')):
        """Initialize MEV watcher agent.
        
        Args:
            min_profit_usd: Minimum profit in USD to consider an opportunity
            max_risk_per_shot: Maximum capital to deploy per opportunity
        """
        super().__init__(AgentConfig(
            name="mev_watcher_v1",
            version="0.2.1",
            description="Real-time liquidation & CEX-DEX divergence hunter | 2025 Solana + EVM chains"
        ))
        self.min_profit_usd = min_profit_usd
        self.max_risk_per_shot = max_risk_per_shot
        self.active = True
        self.monitored_pairs = [
            "SOL-USDT", "ETH-USDT", "BTC-USDT",
            "JUP-USDT", "WIF-USDT", "BONK-USDT", "PEPE-USDT"
        ]
        self.rate_limiter = RateLimiter(calls_per_second=25)
        
    async def run(self):
        """Main agent loop."""
        logger.info(f"MEVWatcherAgent started - hunting opportunities >${self.min_profit_usd}")
        
        # Start background tasks
        liquidation_task = asyncio.create_task(self._run_liquidation_loop())
        arb_task = asyncio.create_task(self._run_arbitrage_loop())
        
        try:
            # Wait for shutdown
            await self._shutdown_event.wait()
        finally:
            liquidation_task.cancel()
            arb_task.cancel()
            try:
                await liquidation_task
            except asyncio.CancelledError:
                pass
            try:
                await arb_task
            except asyncio.CancelledError:
                pass
                
    async def _run_liquidation_loop(self):
        """Background loop for monitoring liquidations."""
        while self.active and not self._shutdown_event.is_set():
            try:
                # This will be populated by mev_helius_jito.py
                # For now, just log that we're monitoring
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in liquidation loop: {e}")
                await asyncio.sleep(5)
                
    async def _run_arbitrage_loop(self):
        """Background loop for monitoring CEX-DEX arbitrage."""
        while self.active and not self._shutdown_event.is_set():
            try:
                # Placeholder - would monitor price divergences
                await asyncio.sleep(0.9)
            except Exception as e:
                logger.error(f"Error in arbitrage loop: {e}")
                await asyncio.sleep(5)
                
    async def evaluate_opportunity(self, market_state: Dict) -> Decimal:
        """Evaluate expected yield for capital allocation.
        
        Args:
            market_state: Current market state dictionary
            
        Returns:
            Expected hourly yield as Decimal
        """
        recent_hits = market_state.get("mev_hits_last_24h", 0)
        avg_profit = market_state.get("mev_avg_profit_usd", 120)
        expected_hourly = (recent_hits / 24) * avg_profit / 400  # assume we catch 1 in 4
        return Decimal(str(expected_hourly))
        
    async def execute_liquidation_buy(self, liq: Dict, war_chest: Decimal):
        """Execute a buy after detecting a liquidation.
        
        Args:
            liq: Liquidation data dictionary
            war_chest: Available capital
        """
        symbol = liq.get('symbol', 'UNKNOWN')
        usd_size = min(
            Decimal(str(liq.get('usd_size', 0))) * Decimal('0.15'),
            war_chest * Decimal('0.3'),
            self.max_risk_per_shot
        )
        
        if usd_size < self.min_profit_usd:
            logger.debug(f"Liquidation opportunity too small: ${usd_size}")
            return
            
        event_bus.publish("mev:execute_buy", {
            "symbol": symbol,
            "usd_amount": float(usd_size),
            "reason": "liquidation_wick",
            "expected_profit_pct": 8.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, source=self.config.name)
        
        logger.info(f"MEV HIT → Buying ${usd_size:.1f} of {symbol} post-liquidation")
        
    async def execute_dex_arbitrage(self, div: Dict, war_chest: Decimal):
        """Execute a DEX arbitrage opportunity.
        
        Args:
            div: Divergence data dictionary
            war_chest: Available capital
        """
        profit_usd = Decimal(str(div.get('profit_usd', 0)))
        usd_size = min(
            profit_usd * Decimal('8'),
            war_chest * Decimal('0.25'),
            self.max_risk_per_shot
        )
        
        event_bus.publish("mev:arbitrage", {
            "buy_venue": div.get('cheap_venue'),
            "sell_venue": div.get('expensive_venue'),
            "symbol": div.get('symbol'),
            "usd_size": float(usd_size),
            "expected_profit_usd": float(profit_usd)
        }, source=self.config.name)
        
        logger.info(f"MEV ARB → ${usd_size:.1f} {div.get('symbol')} | Profit ${profit_usd:.1f}")

