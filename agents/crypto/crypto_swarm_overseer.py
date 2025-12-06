"""Crypto swarm overseer for agent coordination and capital management."""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone

from core.agent_base import Agent, AgentConfig
from core.event_bus import event_bus
from core.memory.chrono import ChronologicalMemory

logger = logging.getLogger(__name__)


class StrategyAgent(Agent):
    """Base class for all strategy agents that can request capital."""
    
    async def evaluate_opportunity(self, market_state: Dict) -> Decimal:
        """Evaluate expected yield/return for capital allocation.
        
        Args:
            market_state: Current market state dictionary
            
        Returns:
            Expected yield as Decimal (e.g., 0.12 = 12% monthly)
        """
        raise NotImplementedError
        
    async def execute(self, allocation: Decimal) -> Dict:
        """Execute strategy with allocated capital.
        
        Args:
            allocation: Capital amount allocated to this strategy
            
        Returns:
            Execution result dictionary
        """
        raise NotImplementedError


class FundingRateAgentWrapper(StrategyAgent):
    """Wrapper for funding rate agent to work with overseer."""
    
    def __init__(self, funding_agent):
        """Initialize wrapper.
        
        Args:
            funding_agent: FundingRateAgent instance
        """
        super().__init__(funding_agent.config)
        self.agent = funding_agent
        
    async def evaluate_opportunity(self, market_state: Dict) -> Decimal:
        """Evaluate funding rate opportunity."""
        funding_rates = market_state.get("top_funding_rates", [])
        if not funding_rates:
            return Decimal('0')
            
        # Projected APR from top rates
        projected_apr = sum(rate for _, rate in funding_rates[:3]) * Decimal('3') * Decimal('365') * Decimal('100')
        return projected_apr / Decimal('100')  # Return as decimal
        
    async def execute(self, allocation: Decimal) -> Dict:
        """Signal deployment to funding agent."""
        event_bus.publish("crypto:deploy_capital", {
            "strategy": "funding",
            "amount_usdt": float(allocation),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, source=self.config.name)
        
        logger.info(f"FundingRateAgent deployed {allocation:.2f} USDT")
        return {"status": "deployed", "amount": float(allocation)}


class CryptoSwarmOverseer(Agent):
    """Overseer that coordinates multiple strategy agents and allocates capital."""
    
    def __init__(self, starting_capital: Decimal = Decimal('1000')):
        """Initialize crypto swarm overseer.
        
        Args:
            starting_capital: Starting capital in USDT
        """
        super().__init__(AgentConfig(
            name="crypto_swarm_overseer",
            version="0.1.0",
            description="Capital allocation brain for the entire crypto money printer swarm"
        ))
        self.strategies: List[StrategyAgent] = []
        self.total_capital = starting_capital
        self.risk_appetite = Decimal('0.95')  # 95% deployed max
        self.memory = ChronologicalMemory(namespace="crypto_pnl")
        
    def register_strategy(self, strategy: StrategyAgent):
        """Register a strategy agent.
        
        Args:
            strategy: Strategy agent instance
        """
        self.strategies.append(strategy)
        logger.info(f"Registered strategy: {strategy.config.name}")
        
    async def run(self):
        """Main overseer loop."""
        logger.info("CryptoSwarmOverseer started")
        
        # First run immediately
        await self.run_allocation_cycle()
        
        # Then every 6 hours
        while not self._shutdown_event.is_set():
            await asyncio.sleep(6 * 3600)  # 6 hours
            await self.run_allocation_cycle()
            
    async def run_allocation_cycle(self):
        """Run one allocation cycle."""
        logger.info("CryptoSwarmOverseer cycle starting...")
        
        try:
            # Refresh market state
            state = await self.refresh_market_state()
            
            # Update total capital (would fetch from exchanges in real implementation)
            # self.total_capital = await self._fetch_total_capital()
            
            deployable = self.total_capital * self.risk_appetite
            
            # Let every strategy bid for capital
            bids = []
            for agent in self.strategies:
                try:
                    expected_yield = await agent.evaluate_opportunity(state)
                    if expected_yield > Decimal('0'):
                        bids.append((expected_yield, agent))
                        logger.debug(f"{agent.config.name} bids with {expected_yield:.2%} expected yield")
                except Exception as e:
                    logger.error(f"{agent.config.name} failed eval: {e}")
                    
            if not bids:
                logger.warning("No strategies bidding for capital")
                return
                
            # Simple greedy allocation for now (later: Kelly, Sharpe-aware, etc.)
            bids.sort(reverse=True, key=lambda x: x[0])
            
            allocated = Decimal('0')
            for yield_, agent in bids:
                if allocated >= deployable:
                    break
                    
                # Allocate up to 50% of deployable per strategy
                allocation = min(
                    deployable - allocated,
                    deployable * Decimal('0.5')
                )
                
                try:
                    result = await agent.execute(allocation)
                    allocated += allocation
                    logger.info(f"Allocated ${allocation:.2f} to {agent.config.name}")
                except Exception as e:
                    logger.error(f"Failed to execute {agent.config.name}: {e}")
                    
            # Record cycle
            self.memory.append({
                "cycle": datetime.now(timezone.utc).isoformat(),
                "total_capital": float(self.total_capital),
                "deployed": float(allocated),
                "top_strategy_yields": [float(y) for y, _ in bids[:3]]
            })
            
            logger.info(f"Cycle complete — Deployed {allocated:.2f} / {deployable:.2f} USDT")
            
        except Exception as e:
            logger.error(f"Error in allocation cycle: {e}", exc_info=True)
            
    async def refresh_market_state(self) -> Dict:
        """Refresh market state from various sources.
        
        Returns:
            Market state dictionary
        """
        # In real implementation, would pull from market data APIs
        # For now, return placeholder
        return {
            "top_funding_rates": [
                ("PEPE/USDT", Decimal('0.0012')),
                ("WIF/USDT", Decimal('0.0010')),
                ("BONK/USDT", Decimal('0.0009'))
            ],
            "btc_dominance": 52.4,
            "fear_greed": 78,
            "vix_30d": 60,
            "mev_hits_last_24h": 5,
            "mev_avg_profit_usd": 120
        }
        
    async def _fetch_total_capital(self) -> Decimal:
        """Fetch total capital from all exchanges.
        
        Returns:
            Total capital in USDT
        """
        # Placeholder - would aggregate from all connected exchanges
        return self.total_capital

