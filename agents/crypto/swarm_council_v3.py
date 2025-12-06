"""Strategy Council v3 - On-chain agent council for strategy invention and voting."""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from core.agent_base import Agent, AgentConfig
from core.event_bus import event_bus
from core.memory.chrono import ChronologicalMemory
from agents.crypto.swarm_capital_allocator_v2 import WeightedVote

logger = logging.getLogger(__name__)


@dataclass
class StrategyProposal:
    """Represents a strategy proposal."""
    id: str
    author: str
    name: str
    description: str
    expected_sharpe: float
    expected_apr: float
    max_drawdown: float
    code_template: str
    capital_request_usd: float
    timestamp: str


@dataclass
class Proposal:
    """Proposal wrapper for voting."""
    id: str
    data: StrategyProposal


class CouncilMember(Agent):
    """Permanent council seat with voting power."""
    
    def __init__(self, name: str, weight: float, specialty: str):
        """Initialize council member.
        
        Args:
            name: Member name
            weight: Voting weight (1.0 = standard, higher = more influence)
            specialty: Area of expertise
        """
        super().__init__(AgentConfig(
            name=name,
            version="v3-council",
            description=specialty
        ))
        self.weight = weight
        self.specialty = specialty
        
    async def evaluate_proposal(self, proposal: StrategyProposal) -> WeightedVote:
        """Evaluate a strategy proposal.
        
        Args:
            proposal: Strategy proposal to evaluate
            
        Returns:
            Weighted vote
        """
        # Simplified evaluation - would use RAG-OS in full implementation
        context = f"""
        Evaluate new crypto strategy: {proposal.name}
        Description: {proposal.description}
        Expected Sharpe: {proposal.expected_sharpe}, APR: {proposal.expected_apr}, MaxDD: {proposal.max_drawdown}
        """
        
        # Simple scoring based on Sharpe ratio and drawdown
        score = 50.0  # Base score
        
        if proposal.expected_sharpe > 3.0:
            score += 20
        if proposal.expected_apr > 300:
            score += 15
        if proposal.max_drawdown < 0.15:
            score += 15
            
        # Specialty adjustments
        if "MEV" in proposal.name and "MEV" in self.specialty:
            score += 10
        if "funding" in proposal.name.lower() and "Yield" in self.specialty:
            score += 10
            
        support = score > 78
        confidence = min(score / 100, 1.0)
        
        return WeightedVote(
            agent=self,
            support=support,
            confidence=confidence,
            weight=self.weight
        )
        
    async def current_regime(self) -> str:
        """Get current market regime."""
        return "high_vol_meme_season_dec_2025"
        
    async def similar_strategies(self) -> str:
        """Get similar strategies performance."""
        return "hyperliquid_lp_v2: 380% APR, 8.1% DD | mev_hunter: 720% APR, 34% DD"


# The Council - 7 permanent seats
COUNCIL = [
    CouncilMember("Risk_Warden", 1.8, "drawdown protection & black swan detection"),
    CouncilMember("Alpha_Seer", 1.6, "edge detection in chaos"),
    CouncilMember("Yield_Maximus", 1.5, "compounding efficiency"),
    CouncilMember("Entropy_Oracle", 2.0, "uses RAG-OS directly — highest weight"),
    CouncilMember("Meme_Priest", 1.3, "WIF/BONK/PEPE cultural signal"),
    CouncilMember("Onchain_Shaman", 1.4, "Solana/EVM flow interpreter"),
    CouncilMember("Future_You", 2.5, "long-term vision — highest veto power"),
]


class StrategyInventor(Agent):
    """Constantly proposes new strategies."""
    
    def __init__(self):
        """Initialize strategy inventor."""
        super().__init__(AgentConfig(
            name="strategy_inventor",
            version="v3",
            description="Generates new strategy proposals using market data and patterns"
        ))
        
    async def run(self):
        """Main inventor loop."""
        logger.info("StrategyInventor started - generating proposals every 24 hours")
        
        while not self._shutdown_event.is_set():
            try:
                await self.run_invention_cycle()
                await asyncio.sleep(24 * 3600)  # 24 hours
            except Exception as e:
                logger.error(f"Error in strategy inventor: {e}", exc_info=True)
                await asyncio.sleep(3600)  # Retry in 1 hour
                
    async def run_invention_cycle(self):
        """Generate a new strategy proposal."""
        # Simplified - would use RAG-OS in full implementation
        proposal = StrategyProposal(
            id=f"prop_{int(datetime.now(timezone.utc).timestamp())}",
            author="StrategyInventor",
            name="Enhanced Cross-Venue Arbitrage",
            description="Automated arbitrage between CEX and DEX with MEV protection",
            expected_sharpe=4.2,
            expected_apr=680.0,
            max_drawdown=0.11,
            code_template="# Placeholder strategy code",
            capital_request_usd=25000.0,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        logger.info(f"NEW STRATEGY PROPOSED → {proposal.name} | {proposal.expected_apr}% APR")
        event_bus.publish("council:new_proposal", proposal.__dict__, source=self.config.name)
        
    async def parse_proposal(self, raw: str) -> Optional[StrategyProposal]:
        """Parse a proposal from generated text."""
        # Placeholder - would parse from RAG-OS output
        return None


class SwarmCouncilV3(Agent):
    """Strategy council that votes on and deploys new strategies."""
    
    def __init__(self):
        """Initialize council v3."""
        super().__init__(AgentConfig(
            name="swarm_council_v3",
            version="3.0.0",
            description="LIVING FINANCIAL SINGULARITY - Strategy invention and voting"
        ))
        self.active_proposals: Dict[str, Proposal] = {}
        self.inventor = StrategyInventor()
        self.memory = ChronologicalMemory(namespace="council_proposals")
        
    async def run(self):
        """Main council loop."""
        logger.critical("SWARM COUNCIL V3 — THE FINANCIAL GOD IS AWAKE")
        
        # Start strategy inventor
        await self.inventor.start()
        
        # Subscribe to new proposals
        async for event in event_bus.subscribe_async("council:new_proposal"):
            try:
                proposal_data = event.data
                proposal = StrategyProposal(**proposal_data)
                await self.process_proposal(proposal)
            except Exception as e:
                logger.error(f"Error processing proposal: {e}", exc_info=True)
                
    async def process_proposal(self, proposal: StrategyProposal):
        """Process a new strategy proposal.
        
        Args:
            proposal: Strategy proposal to process
        """
        logger.warning(
            f"NEW STRATEGY PROPOSED → {proposal.name} | "
            f"{proposal.expected_apr}% APR | by {proposal.author}"
        )
        
        prop = Proposal(id=proposal.id, data=proposal)
        self.active_proposals[proposal.id] = prop
        
        # Council votes
        votes = []
        for member in COUNCIL:
            try:
                vote = await member.evaluate_proposal(proposal)
                votes.append(vote)
                
                # Future_You has veto power
                if member.name == "Future_You" and not vote.support:
                    logger.critical("FUTURE_YOU VETOED — proposal killed")
                    self.memory.append({
                        "proposal_id": proposal.id,
                        "proposal_name": proposal.name,
                        "status": "vetoed",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    return
                    
            except Exception as e:
                logger.error(f"Error getting vote from {member.name}: {e}")
                
        # Tally votes
        result = WeightedVote.tally(votes)
        
        if result["passed"]:
            logger.critical(
                f"PROPOSAL PASSED — DEPLOYING {proposal.name} WITH ${proposal.capital_request_usd:,.0f}"
            )
            
            event_bus.publish("allocator:deploy_new_strategy", {
                "name": proposal.name,
                "code": proposal.code_template,
                "capital_usd": proposal.capital_request_usd,
                "proposal_id": proposal.id
            }, source=self.config.name)
            
            # Auto-spawn new agent
            await self.birth_new_agent(proposal)
            
            self.memory.append({
                "proposal_id": proposal.id,
                "proposal_name": proposal.name,
                "status": "approved",
                "capital_allocated": proposal.capital_request_usd,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        else:
            logger.info(f"Proposal {proposal.name} rejected (support ratio: {result['ratio']:.2%})")
            self.memory.append({
                "proposal_id": proposal.id,
                "proposal_name": proposal.name,
                "status": "rejected",
                "support_ratio": result["ratio"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
    async def birth_new_agent(self, proposal: StrategyProposal):
        """Create and deploy a new agent from a proposal.
        
        Args:
            proposal: Approved strategy proposal
        """
        # Generate agent code
        class_name = proposal.name.replace(' ', '').replace('-', '')
        code = f'''# AUTO-GENERATED BY SWARM COUNCIL V3 — {proposal.name}
# Proposal ID: {proposal.id}
# Generated: {datetime.now(timezone.utc).isoformat()}

from core.agent_base import Agent, AgentConfig
from decimal import Decimal

class {class_name}Agent(Agent):
    def __init__(self):
        super().__init__(AgentConfig(
            name="{proposal.name.lower().replace(' ', '_')}",
            version="1.0.0",
            description="{proposal.description}"
        ))
        
    async def run(self):
        # {proposal.code_template}
        self.logger.info("I AM ALIVE — {proposal.name} making money")
        while not self._shutdown_event.is_set():
            await asyncio.sleep(60)
'''
        
        # In real implementation, would write to file and import
        # For now, just log
        logger.critical(f"NEW AGENT BIRTHED → {class_name}Agent")
        logger.debug(f"Generated code:\n{code}")
        
    async def on_stop(self):
        """Cleanup on stop."""
        await self.inventor.stop()


# Start the council
if __name__ == "__main__":
    council = SwarmCouncilV3()
    event_bus.start()
    asyncio.run(council.start())

