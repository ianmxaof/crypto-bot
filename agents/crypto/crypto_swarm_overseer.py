"""Crypto swarm overseer for agent coordination and capital management."""

import asyncio
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone

from core.agent_base import Agent, AgentConfig
from core.event_bus import event_bus
from core.memory.chrono import ChronologicalMemory
from config.settings import settings

logger = logging.getLogger(__name__)

# Import simulation state for runtime control
try:
    from config.simulation_state import (
        get_simulation_running,
        get_simulation_speed,
        get_simulation_days
    )
except ImportError:
    # Fallback if simulation_state module isn't available
    logger.warning("simulation_state module not available, simulation controls disabled")
    def get_simulation_running(): return False
    def get_simulation_speed(): return 100.0
    def get_simulation_days(): return 30

# Polling interval for simulation state (seconds)
# Polling every 3 seconds gives <0.1% CPU overhead and instant control
SIMULATION_STATE_POLL_INTERVAL = 3.0

# Base cycle interval (6 hours in seconds)
BASE_CYCLE_INTERVAL = 6 * 3600  # 21600 seconds


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
        self.starting_capital = starting_capital  # Track for PnL calculation
        self.risk_appetite = Decimal('0.95')  # 95% deployed max
        # Initialize memory with persist path for dashboard access
        self.memory = ChronologicalMemory(
            namespace="crypto_pnl",
            persist_path=settings.MEMORY_DIR / "crypto_pnl.json"
        )
        self.last_logged_balance = starting_capital  # Track for PnL delta calculation
        
    def register_strategy(self, strategy: StrategyAgent):
        """Register a strategy agent.
        
        Args:
            strategy: Strategy agent instance
        """
        self.strategies.append(strategy)
        logger.info(f"Registered strategy: {strategy.config.name}")
        
    async def run(self):
        """Main overseer loop with simulation control support."""
        logger.info("CryptoSwarmOverseer started")
        
        # Track simulation start time for duration control
        simulation_start_time: Optional[datetime] = None
        last_running_state = False
        
        # First run immediately (if simulation is running)
        try:
            if get_simulation_running():
                await self.run_allocation_cycle()
                simulation_start_time = datetime.now(timezone.utc)
                last_running_state = True
                logger.info("Initial allocation cycle completed (simulation running)")
        except Exception as e:
            logger.warning(f"Error checking initial simulation state: {e}")
        
        # Main loop with simulation control polling
        while not self._shutdown_event.is_set():
            try:
                # Poll simulation state every 3 seconds
                is_running = get_simulation_running()
                speed = get_simulation_speed()
                target_days = get_simulation_days()
                
                # Log state changes
                if is_running != last_running_state:
                    if is_running:
                        simulation_start_time = datetime.now(timezone.utc)
                        logger.info(f"Simulation STARTED - Speed: {speed}x, Target: {target_days} days")
                    else:
                        logger.info("Simulation STOPPED")
                    last_running_state = is_running
                
                # Check if simulation should be running
                if not is_running:
                    # Wait and continue polling
                    await asyncio.sleep(SIMULATION_STATE_POLL_INTERVAL)
                    continue
                
                # Check if we've exceeded target duration
                if simulation_start_time and target_days > 0:
                    elapsed = datetime.now(timezone.utc) - simulation_start_time
                    elapsed_days = elapsed.total_seconds() / (24 * 3600)
                    
                    if elapsed_days >= target_days:
                        logger.info(f"Simulation target duration ({target_days} days) reached. Stopping.")
                        # Optionally auto-stop by updating state (requires write access)
                        # For now, just log - user can stop from dashboard
                        await asyncio.sleep(SIMULATION_STATE_POLL_INTERVAL)
                        continue
                
                # Calculate adjusted cycle interval based on speed multiplier
                # Base: 6 hours, at 100x speed: 216 seconds (3.6 minutes)
                adjusted_interval = BASE_CYCLE_INTERVAL / speed
                
                # Ensure minimum interval of 1 second for safety
                adjusted_interval = max(adjusted_interval, 1.0)
                
                # Wait for the adjusted interval (but check state periodically)
                wait_start = datetime.now(timezone.utc)
                while (datetime.now(timezone.utc) - wait_start).total_seconds() < adjusted_interval:
                    if self._shutdown_event.is_set():
                        break
                    
                    # Check state during wait (every 3 seconds)
                    check_interval = min(SIMULATION_STATE_POLL_INTERVAL, 
                                       adjusted_interval - (datetime.now(timezone.utc) - wait_start).total_seconds())
                    if check_interval > 0:
                        await asyncio.sleep(check_interval)
                        
                        # Re-check if still running
                        if not get_simulation_running():
                            logger.info("Simulation stopped during wait period")
                            break
                
                # Run allocation cycle if still running and not shutdown
                if not self._shutdown_event.is_set() and get_simulation_running():
                    await self.run_allocation_cycle()
                
            except Exception as e:
                logger.error(f"Error in overseer main loop: {e}", exc_info=True)
                # Wait before retrying
                await asyncio.sleep(SIMULATION_STATE_POLL_INTERVAL)
            
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
                    
            # Calculate PnL (change since last log)
            current_balance = float(self.total_capital)
            pnl_delta = current_balance - float(self.last_logged_balance)
            
            # Calculate drawdown (simplified - would need peak tracking in real implementation)
            peak = max(float(self.starting_capital), current_balance)
            drawdown = ((peak - current_balance) / peak * 100) if peak > 0 else 0.0
            
            # Record cycle with comprehensive logging for dashboard
            self.memory.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "pnl": pnl_delta,
                "balance": current_balance,
                "agent": self.config.name,
                "symbol": "SIM",  # Simulation cycle
                "side": "N/A",
                "amount": float(allocated),
                "price": 0.0,
                "drawdown": drawdown,
                "total_capital": current_balance,
                "deployed": float(allocated),
                "top_strategy_yields": [float(y) for y, _ in bids[:3]]
            })
            
            # Update last logged balance for next cycle
            self.last_logged_balance = self.total_capital
            
            logger.info(f"Cycle complete — Deployed {allocated:.2f} / {deployable:.2f} USDT | Balance: ${current_balance:,.2f} | PnL: ${pnl_delta:+,.2f}")
            
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

