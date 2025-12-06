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
from exchanges.mock_exchange import MockExchange

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
        
        if settings.PAPER_TRADING:
            # Use mock exchange for paper trading
            logger.info("PAPER TRADING MODE ENABLED - Using mock exchange")
            mock_exchange = MockExchange(
                starting_balance=settings.SIMULATION_STARTING_BALANCE,
                fee_rate=settings.SIMULATION_FEES
            )
            exchanges.append(mock_exchange)
            logger.info(f"Mock exchange initialized with ${settings.SIMULATION_STARTING_BALANCE} starting balance")
        else:
            # Use real exchanges
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
            exchange = exchanges[0]
            # Register funding rate agent
            funding_agent = FundingRateAgent(
                exchange,
                allocation_percent=settings.ALLOCATION_PERCENT
            )
            funding_wrapper = FundingRateAgentWrapper(funding_agent)
            overseer.register_strategy(funding_wrapper)
            
            mode_str = "PAPER TRADING" if settings.PAPER_TRADING else "LIVE TRADING"
            logger.info(f"Funding rate agent registered ({mode_str})")
            
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
            
            # If paper trading, show final stats
            if settings.PAPER_TRADING and exchanges:
                mock_exchange = exchanges[0]
                if hasattr(mock_exchange, 'get_total_value'):
                    total_value = mock_exchange.get_total_value()
                    realized_pnl = mock_exchange.get_realized_pnl()
                    logger.info("=" * 60)
                    logger.info("PAPER TRADING FINAL STATS")
                    logger.info("=" * 60)
                    logger.info(f"Starting Capital: ${settings.SIMULATION_STARTING_BALANCE:,.2f}")
                    logger.info(f"Total Value: ${total_value:,.2f}")
                    logger.info(f"Realized P&L: ${realized_pnl:,.2f}")
                    logger.info(f"Return: {((total_value - settings.SIMULATION_STARTING_BALANCE) / settings.SIMULATION_STARTING_BALANCE * 100):.2f}%")
                    
            event_bus.stop()
            logger.info("Shutdown complete")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        event_bus.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

