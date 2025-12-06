"""Standalone script to test exchange connections."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings
from exchanges.bybit_client import BybitExchange
from exchanges.mock_exchange import MockExchange
from utils.logger import setup_logging


async def test_bybit_connection():
    """Test Bybit exchange connection."""
    print("=" * 60)
    print("Testing Bybit Exchange Connection")
    print("=" * 60)
    
    if not settings.BYBIT_API_KEY or not settings.BYBIT_API_SECRET:
        print("ERROR: BYBIT_API_KEY and BYBIT_API_SECRET not configured")
        print("Set them in .env file or environment variables")
        return False
        
    try:
        print(f"Initializing Bybit client (testnet={settings.BYBIT_TESTNET})...")
        exchange = BybitExchange(
            settings.BYBIT_API_KEY,
            settings.BYBIT_API_SECRET,
            testnet=settings.BYBIT_TESTNET
        )
        
        print("Fetching balance...")
        balance = await exchange.fetch_balance('USDT')
        
        if 'USDT' in balance:
            usdt_bal = balance['USDT']
            print(f"✓ Connection successful!")
            print(f"  USDT Balance: {usdt_bal.total}")
            print(f"  Free: {usdt_bal.free}")
            print(f"  Used: {usdt_bal.used}")
            return True
        else:
            print("✓ Connection successful, but no USDT balance found")
            print(f"  Available currencies: {list(balance.keys())}")
            return True
            
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'exchange' in locals():
            await exchange.close()


async def test_mock_exchange():
    """Test mock exchange functionality."""
    print("\n" + "=" * 60)
    print("Testing Mock Exchange")
    print("=" * 60)
    
    try:
        from decimal import Decimal
        
        print("Initializing mock exchange...")
        exchange = MockExchange(
            starting_balance=Decimal('10000'),
            fee_rate=Decimal('0.001')
        )
        
        print("Fetching balance...")
        balance = await exchange.fetch_balance('USDT')
        
        if 'USDT' in balance:
            usdt_bal = balance['USDT']
            print(f"✓ Mock exchange initialized successfully!")
            print(f"  USDT Balance: {usdt_bal.total}")
            print(f"  Free: {usdt_bal.free}")
            print(f"  Used: {usdt_bal.used}")
            
            # Test order placement
            print("\nTesting order placement...")
            try:
                order = await exchange.create_market_order(
                    'BTC/USDT',
                    'buy',
                    Decimal('0.01')
                )
                print(f"✓ Order created: {order.id}")
                print(f"  Status: {order.status}")
                print(f"  Filled: {order.filled}")
                
                # Check position
                positions = await exchange.fetch_positions('BTC/USDT')
                if positions:
                    pos = positions[0]
                    print(f"✓ Position created: {pos.size} {pos.symbol} @ {pos.entry_price}")
                
                return True
            except Exception as e:
                print(f"⚠️  Order test failed: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("✗ Mock exchange balance not found")
            return False
            
    except Exception as e:
        print(f"✗ Mock exchange test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'exchange' in locals():
            await exchange.close()


async def test_event_bus():
    """Test event bus functionality."""
    print("\n" + "=" * 60)
    print("Testing Event Bus")
    print("=" * 60)
    
    try:
        from core.event_bus import EventBus, Event
        
        bus = EventBus()
        events_received = []
        
        def handler(event: Event):
            events_received.append(event)
            print(f"  Received event: {event.topic} - {event.data}")
            
        bus.subscribe("test", handler)
        bus.publish("test", {"message": "Hello from test"})
        
        bus.start()
        await asyncio.sleep(0.2)
        bus.stop()
        
        if events_received:
            print("✓ Event bus working correctly")
            return True
        else:
            print("✗ Event bus not receiving events")
            return False
            
    except Exception as e:
        print(f"✗ Event bus test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all connection tests."""
    setup_logging(log_level="INFO")
    
    print("\nCrypto Bot Connection Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test event bus (always works, no config needed)
    results.append(await test_event_bus())
    
    # Test mock exchange (always works, no config needed)
    # This is especially important when PAPER_TRADING is enabled
    if settings.PAPER_TRADING:
        print("\n" + "=" * 60)
        print("Paper Trading Mode Detected")
        print("=" * 60)
        print("Testing mock exchange (required for paper trading)...")
        results.append(await test_mock_exchange())
    else:
        # Test mock exchange anyway to ensure it works
        results.append(await test_mock_exchange())
    
    # Test Bybit if configured
    if settings.BYBIT_API_KEY and settings.BYBIT_API_SECRET:
        results.append(await test_bybit_connection())
    else:
        print("\n" + "=" * 60)
        print("Bybit Connection Test Skipped")
        print("=" * 60)
        print("Set BYBIT_API_KEY and BYBIT_API_SECRET to test exchange connection")
        
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    if all(results):
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

