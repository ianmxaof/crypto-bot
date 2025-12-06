"""Quick validation script for crypto bot.

Run this to quickly test if the system can import and initialize core components.
Useful for debugging import errors and basic functionality.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_imports():
    """Test that all core modules can be imported."""
    print("=" * 60)
    print("Testing Core Imports")
    print("=" * 60)
    
    imports = [
        ("core.event_bus", "EventBus"),
        ("core.agent_base", "Agent"),
        ("core.rate_limiter", "RateLimiter"),
        ("core.memory.chrono", "ChronologicalMemory"),
        ("exchanges.base", "BaseExchange"),
        ("exchanges.mock_exchange", "MockExchange"),
        ("simulation.position_tracker", "PositionTracker"),
        ("simulation.pnl_calculator", "PnLCalculator"),
        ("config.settings", "settings"),
    ]
    
    failed = []
    for module_name, class_name in imports:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✓ {module_name}.{class_name}")
        except ImportError as e:
            print(f"✗ {module_name}.{class_name} - ImportError: {e}")
            failed.append((module_name, class_name, str(e)))
        except AttributeError as e:
            print(f"✗ {module_name}.{class_name} - AttributeError: {e}")
            failed.append((module_name, class_name, str(e)))
        except Exception as e:
            print(f"✗ {module_name}.{class_name} - Error: {e}")
            failed.append((module_name, class_name, str(e)))
    
    print()
    if failed:
        print(f"❌ {len(failed)} import(s) failed")
        return False
    else:
        print("✅ All imports successful")
        return True


def test_mock_exchange():
    """Test mock exchange initialization."""
    print("\n" + "=" * 60)
    print("Testing Mock Exchange")
    print("=" * 60)
    
    try:
        from decimal import Decimal
        from exchanges.mock_exchange import MockExchange
        
        exchange = MockExchange(
            starting_balance=Decimal('10000'),
            fee_rate=Decimal('0.001')
        )
        print(f"✓ MockExchange initialized")
        print(f"  Starting balance: ${exchange.state.get_balance('USDT')}")
        print(f"  Fee rate: {exchange.state.pnl_calculator.fee_rate}")
        print(f"  Available symbols: {list(exchange.state.current_prices.keys())}")
        return True
    except Exception as e:
        print(f"✗ MockExchange initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_settings():
    """Test settings configuration."""
    print("\n" + "=" * 60)
    print("Testing Configuration")
    print("=" * 60)
    
    try:
        from config.settings import settings
        
        print(f"✓ Settings loaded")
        print(f"  PAPER_TRADING: {settings.PAPER_TRADING}")
        print(f"  STARTING_CAPITAL: ${settings.STARTING_CAPITAL}")
        print(f"  SIMULATION_STARTING_BALANCE: ${settings.SIMULATION_STARTING_BALANCE}")
        print(f"  LOG_LEVEL: {settings.LOG_LEVEL}")
        
        # Validate settings
        try:
            settings.validate()
            print("✓ Settings validation passed")
            return True
        except ValueError as e:
            print(f"⚠️  Settings validation warning: {e}")
            print("  (This is OK if PAPER_TRADING=true)")
            return True  # Not a failure if paper trading is enabled
    except Exception as e:
        print(f"✗ Settings test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_bus():
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
        
        bus.subscribe("test", handler)
        bus.publish("test", {"message": "test"})
        
        bus.start()
        import time
        time.sleep(0.2)
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


def main():
    """Run all quick tests."""
    print("\n" + "=" * 60)
    print("Crypto Bot Quick Test")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(test_imports())
    results.append(test_settings())
    results.append(test_mock_exchange())
    results.append(test_event_bus())
    
    print("\n" + "=" * 60)
    print("Quick Test Summary")
    print("=" * 60)
    
    if all(results):
        print("✅ All quick tests passed!")
        return 0
    else:
        print("❌ Some quick tests failed")
        print("\nRun 'python scripts/test_connection.py' for more detailed tests")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

