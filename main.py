"""Main entry point for Crypto Swarm Trading Bot System."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import setup_logging
from config.settings import settings
from core.event_bus import event_bus
from agents.crypto.crypto_swarm_overseer import CryptoSwarmOverseer, FundingRateAgentWrapper
from agents.crypto.funding_rate_agent import FundingRateAgent
from exchanges.bybit_client import BybitExchange

logger = logging.getLogger(__name__)


async def main():
    """Main application entry point."""
    # Setup logging
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE
    )
    
    logger.info("=" * 60)
    logger.info("CRYPTO SWARM TRADING BOT SYSTEM")
    logger.info("=" * 60)
    
    # Validate settings
    try:
        settings.validate()
        logger.info("Configuration validated successfully")
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
        
    # Start event bus
    event_bus.start()
    logger.info("Event bus started")
    
    try:
        # Initialize exchange clients
        exchanges = []
        
        if settings.BYBIT_API_KEY and settings.BYBIT_API_SECRET:
            bybit = BybitExchange(
                settings.BYBIT_API_KEY,
                settings.BYBIT_API_SECRET,
                testnet=settings.BYBIT_TESTNET
            )
            exchanges.append(bybit)
            logger.info("Bybit exchange client initialized")
            
        # Create overseer
        overseer = CryptoSwarmOverseer(starting_capital=settings.STARTING_CAPITAL)
        
        # Register strategies
        if exchanges:
            # Register funding rate agent if Bybit is configured
            funding_agent = FundingRateAgent(
                exchanges[0],
                allocation_percent=settings.ALLOCATION_PERCENT
            )
            funding_wrapper = FundingRateAgentWrapper(funding_agent)
            overseer.register_strategy(funding_wrapper)
            logger.info("Funding rate agent registered")
            
        # Start overseer
        logger.info("Starting overseer...")
        await overseer.start()
        
        # Keep running until interrupted
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutdown signal received")
        finally:
            await overseer.stop()
            event_bus.stop()
            logger.info("Shutdown complete")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        event_bus.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

