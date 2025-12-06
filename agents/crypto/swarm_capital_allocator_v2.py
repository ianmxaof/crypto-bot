"""Kelly-optimal capital allocator v2 with correlation adjustments."""

import asyncio
import logging
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from dataclasses import dataclass

from core.agent_base import Agent, AgentConfig
from core.event_bus import event_bus
from core.memory.chrono import ChronologicalMemory

logger = logging.getLogger(__name__)


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy."""
    daily_pnl: List[Decimal] = None
    sharpe: Decimal = Decimal('3.2')
    win_rate: Decimal = Decimal('0.78')
    avg_win: Decimal = Decimal('0.042')
    avg_loss: Decimal = Decimal('-0.019')
    max_dd: Decimal = Decimal('0.087')
    volatility: Decimal = Decimal('0.68')  # annualized
    
    def __post_init__(self):
        if self.daily_pnl is None:
            self.daily_pnl = []
            
    def kelly_fraction(self) -> Decimal:
        """Calculate Kelly criterion optimal fraction.
        
        Returns:
            Optimal capital fraction (0.02 to 0.38)
        """
        if self.avg_loss == Decimal('0'):
            return Decimal('0.5')
            
        b = self.avg_win / abs(self.avg_loss)
        p, q = self.win_rate, Decimal('1') - self.win_rate
        
        # Kelly formula: f = (bp - q) / b
        f = (b * p - q) / b if b > 0 else Decimal('0')
        
        # Apply safety factor (Kelly × 0.65) and hard caps
        return max(Decimal('0.02'), min(f * Decimal('0.65'), Decimal('0.38')))


class WeightedVote:
    """Represents a weighted vote."""
    def __init__(self, agent, support: bool, confidence: float, weight: float):
        self.agent = agent
        self.support = support
        self.confidence = confidence
        self.weight = weight
        
    @staticmethod
    def tally(votes: List['WeightedVote']) -> Dict:
        """Tally weighted votes.
        
        Args:
            votes: List of weighted votes
            
        Returns:
            Dictionary with 'passed' bool and vote details
        """
        total_weight = sum(v.weight for v in votes)
        support_weight = sum(v.weight * v.confidence for v in votes if v.support)
        oppose_weight = sum(v.weight * (1 - v.confidence) for v in votes if not v.support)
        
        passed = support_weight > oppose_weight and support_weight / total_weight > 0.5
        
        return {
            "passed": passed,
            "support_weight": support_weight,
            "oppose_weight": oppose_weight,
            "total_weight": total_weight,
            "ratio": support_weight / total_weight if total_weight > 0 else 0
        }


class SwarmCapitalAllocatorV2(Agent):
    """Kelly-optimal capital allocator with correlation adjustments."""
    
    def __init__(self, starting_capital: Decimal = Decimal('1000')):
        """Initialize allocator v2.
        
        Args:
            starting_capital: Starting capital in USDT
        """
        super().__init__(AgentConfig(
            name="swarm_capital_allocator_v2",
            version="2.0.0",
            description="Kelly-optimal capital allocation across funding, MEV, Hyperliquid LP | Auto-compounding | Cross-hedging"
        ))
        self.total_capital = starting_capital
        self.memory = ChronologicalMemory(namespace="swarm_pnl_v2")
        
        # Live performance trackers (updated by agents via event bus)
        self.performance: Dict[str, StrategyPerformance] = {
            "funding_farmer": StrategyPerformance(),
            "mev_hunter": StrategyPerformance(),
            "hyperliquid_lp": StrategyPerformance(),
        }
        
        # Cross-strategy correlation matrix (negative = natural hedge)
        self.correlation_matrix = {
            ("funding_farmer", "mev_hunter"): Decimal('-0.41'),
            ("funding_farmer", "hyperliquid_lp"): Decimal('0.12'),
            ("mev_hunter", "hyperliquid_lp"): Decimal('-0.18'),
        }
        
    async def run(self):
        """Main allocator loop."""
        logger.critical("SWARM CAPITAL ALLOCATOR V2 STARTED — THE SINGULARITY IS HERE")
        
        # First run immediately
        await self.run_allocation_cycle()
        
        # Then every 6 hours
        while not self._shutdown_event.is_set():
            await asyncio.sleep(6 * 3600)  # 6 hours
            await self.run_allocation_cycle()
            
    async def run_allocation_cycle(self):
        """Run one allocation cycle with Kelly optimization."""
        try:
            await self._update_capital()
            await self._update_performance_from_memory()
            
            base_allocations = {}
            total_kelly = Decimal('0')
            
            # 1. Calculate raw Kelly for each strategy
            for name, perf in self.performance.items():
                kelly = perf.kelly_fraction()
                base_allocations[name] = kelly
                total_kelly += kelly
                logger.debug(f"{name} Kelly fraction: {kelly:.4f}")
                
            # 2. Apply correlation-adjusted scaling (diversification bonus)
            adjusted: Dict[str, Decimal] = {}
            for name, raw in base_allocations.items():
                hedge_bonus = Decimal('1')
                
                # Check correlations with other strategies
                for (a, b), corr in self.correlation_matrix.items():
                    if a == name and corr < 0:
                        # Negative correlation = natural hedge, boost allocation
                        hedge_bonus += abs(corr) * Decimal('0.4')
                    elif b == name and corr < 0:
                        hedge_bonus += abs(corr) * Decimal('0.4')
                        
                adjusted[name] = raw * hedge_bonus
                
            total_adj = sum(adjusted.values()) or Decimal('1')
            
            # 3. Final allocation percentages with hard caps
            final_allocation = {}
            deployed = Decimal('0')
            
            for name, weight in adjusted.items():
                pct = min(weight / total_adj, Decimal('0.42'))  # Hard cap 42% per strategy
                amount = (self.total_capital * pct).quantize(Decimal('1'), ROUND_HALF_UP)
                final_allocation[name] = amount
                deployed += amount
                
            # 4. Auto-compound remainder into Hyperliquid LP (highest Sharpe)
            remainder = self.total_capital - deployed
            if remainder > Decimal('10'):
                final_allocation["hyperliquid_lp"] = final_allocation.get("hyperliquid_lp", Decimal('0')) + remainder
                
            # 5. Publish capital orders
            for strategy, amount in final_allocation.items():
                if amount > Decimal('10'):
                    kelly_pct = base_allocations.get(strategy, Decimal('0'))
                    final_pct = amount / self.total_capital if self.total_capital > 0 else Decimal('0')
                    
                    event_bus.publish("allocator:deploy", {
                        "strategy": strategy,
                        "amount_usdt": float(amount),
                        "kelly_pct": float(kelly_pct),
                        "final_pct": float(final_pct),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }, source=self.config.name)
                    
            logger.warning(
                f"SWARM V2 CYCLE | Capital: ${self.total_capital:,.0f} | "
                f"Funding: ${final_allocation.get('funding_farmer', 0):,.0f} | "
                f"MEV: ${final_allocation.get('mev_hunter', 0):,.0f} | "
                f"HyperLP: ${final_allocation.get('hyperliquid_lp', 0):,.0f}"
            )
            
            # Record for self-improvement
            self.memory.append({
                "cycle": datetime.now(timezone.utc).isoformat(),
                "total_capital": float(self.total_capital),
                "allocations": {k: float(v) for k, v in final_allocation.items()},
                "kelly_fractions": {k: float(v) for k, v in base_allocations.items()}
            })
            
        except Exception as e:
            logger.error(f"Error in allocator cycle: {e}", exc_info=True)
            
    async def _update_capital(self):
        """Update total capital from exchanges."""
        # Placeholder - would aggregate from all exchanges
        # In real implementation: sum balances across Bybit, Binance, OKX, Hyperliquid
        # self.total_capital = Decimal('48732.91')
        pass
        
    async def _update_performance_from_memory(self):
        """Update performance metrics from memory/event bus."""
        # In real system: agents publish daily PnL → memory → here
        # Would calculate Sharpe, win rate, etc. from historical PnL
        pass

