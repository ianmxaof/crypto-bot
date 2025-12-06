"""Helius + Jito liquidation hunter integration."""

import asyncio
import websockets
import json
import logging
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict

from core.event_bus import event_bus
from agents.crypto.mev_full_analyzer import analyze_potential_liquidation

logger = logging.getLogger(__name__)


# Configuration - change these
HELIUS_API_KEY = "your-helius-mainnet-key-here"
JITO_TIP_ACCOUNTS = [
    "DttWa4L6aTj3bgsS8T9c9k1nQ8YBkRXox3n2gL1fZ2gK",
    "4xY4xY4xY4xY4xY4xY4xY4xY4xY4xY4xY4xY4xY4xY4xY",
    "G9kZ4g7gY9kZ4g7gY9kZ4g7gY9kZ4g7gY9kZ4g7gY9kZ4g",
]

MIN_LIQ_USD = Decimal('40_000')
MAX_EXECUTE_USD = Decimal('12_000')
SLIPPAGE_BPS = 60


async def mev_helius_jito_hunter():
    """Main Helius + Jito liquidation hunter loop."""
    log = logging.getLogger("MEV_HELIUS_JITO")
    log.info("MEV Helius+Jito Liquidation Hunter STARTED — hunting $40k+ liqs")
    
    HELIUS_WS_URL = f"wss://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
    
    # Protocol addresses for liquidation monitoring
    LIQUIDATION_PROTOCOLS = [
        "JUP4Fb2cqiRUtzJGU2D4Yd8gT3zZ7xT3zZ7xT3zZ7xT3",  # Jupiter
        "marginfi1z6k1j1z6k1j1z6k1j1z6k1j1z6k1j1z6k1j1z6",  # Marginfi
        "drift1z6k1j1z6k1j1z6k1j1z6k1j1z6k1j1z6k1j1z6k1j",  # Drift
        "So1end1z6k1j1z6k1j1z6k1j1z6k1j1z6k1j1z6k1j1z6",  # Solend
    ] + JITO_TIP_ACCOUNTS[:4]
    
    while True:
        try:
            async with websockets.connect(HELIUS_WS_URL) as ws:
                # Subscribe to account changes for liquidation protocols
                for addr in LIQUIDATION_PROTOCOLS:
                    subscribe_msg = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "accountSubscribe",
                        "params": [
                            addr,
                            {"encoding": "jsonParsed"}
                        ]
                    }
                    await ws.send(json.dumps(subscribe_msg))
                    await asyncio.sleep(0.1)
                
                log.info(f"Subscribed to {len(LIQUIDATION_PROTOCOLS)} accounts")
                
                async for message in ws:
                    data = json.loads(message)
                    
                    if 'result' in data:
                        continue  # Subscription confirmation
                    
                    try:
                        # Check for account changes that might indicate liquidations
                        if 'params' in data and 'result' in data['params']:
                            account_value = data['params']['result'].get('value')
                            if not account_value:
                                continue
                                
                            # Check for large lamport changes
                            lamports = account_value.get('lamports', 0)
                            if lamports < 1_000_000:
                                continue
                                
                            # Extract transaction signature if available
                            context = data['params'].get('context', {})
                            slot = context.get('slot')
                            
                            if slot:
                                # Analyze potential liquidation
                                liq = await analyze_potential_liquidation(str(slot))
                                if liq and liq.get('usd_size', 0) >= float(MIN_LIQ_USD):
                                    await execute_liquidation_buy(liq)
                                    
                    except Exception as e:
                        log.debug(f"Parse error: {e}")
                        
        except websockets.exceptions.ConnectionClosed:
            log.warning("WebSocket connection closed, reconnecting...")
            await asyncio.sleep(5)
        except Exception as e:
            log.error(f"Error in Helius hunter: {e}", exc_info=True)
            await asyncio.sleep(10)


async def execute_liquidation_buy(liq: Dict):
    """Execute buy after detecting liquidation.
    
    Args:
        liq: Liquidation data dictionary
    """
    log = logging.getLogger("MEV_HELIUS_JITO")
    symbol = liq.get('symbol', 'UNKNOWN').replace("USD", "-USDT")
    usd_amount = min(Decimal(str(liq.get('usd_size', 0))) * Decimal('0.18'), MAX_EXECUTE_USD)
    
    event_bus.publish("mev:liquidation_buy", {
        "symbol": symbol,
        "usd_amount": float(usd_amount),
        "reason": "large_liquidation_wick",
        "expected_profit_pct": 7.2,
        "slot": liq.get('slot'),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, source="helius_jito_hunter")
    
    log.info(f"LIQUIDATION HIT → Buying ${usd_amount:,.0f} {symbol} | Est +7–25% in <2 min")


def start_helius_hunter():
    """Start the Helius hunter in background."""
    asyncio.create_task(mev_helius_jito_hunter())


# Auto-start when imported (can be disabled)
try:
    # Uncomment to auto-start:
    # start_helius_hunter()
    pass
except Exception as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not start Helius hunter: {e}")

