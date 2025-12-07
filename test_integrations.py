"""Test script for new integrations."""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("INTEGRATION TESTS")
print("=" * 80)

# Test 1: Backtesting
print("\n[TEST 1] Backtesting with BTC/USDT (Nov 1 - Dec 7, 2025)")
print("-" * 80)

try:
    from backtesting.backtester import Backtester
    from strategies.funding_rate import FundingRateStrategy
    
    start_date = datetime(2025, 11, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 12, 7, tzinfo=timezone.utc)
    
    backtester = Backtester(
        strategy=FundingRateStrategy(),
        initial_capital=Decimal('10000'),
        data_dir=Path("data"),
        start_date=start_date,
        end_date=end_date,
        use_real_data=True,
        symbol="BTC/USDT"
    )
    
    print(f"Running backtest: {start_date.date()} to {end_date.date()}")
    print("Fetching historical data from CoinGecko...")
    
    results = backtester.run()
    
    print(f"✓ Backtest completed!")
    print(f"  Final value: ${results.get('equity_curve', [10000])[-1]:,.2f}")
    print(f"  Used real data: {results.get('used_real_data', False)}")
    print(f"  Equity curve points: {len(results.get('equity_curve', []))}")
    
    if results.get('metrics'):
        metrics = results['metrics']
        print(f"  Sharpe ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"  Max drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")
    
except Exception as e:
    print(f"✗ Backtest failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Marketplace Agent Upload
print("\n[TEST 2] Marketplace Agent Upload")
print("-" * 80)

try:
    from agents.marketplace import get_marketplace
    
    marketplace = get_marketplace()
    
    # Fixed test agent code (StrategyAgent doesn't exist, use Agent instead)
    test_agent_code = """
from core.agent_base import Agent, AgentConfig
import asyncio

class MoonBagAgent(Agent):
    def __init__(self):
        super().__init__(AgentConfig(
            name="moon_bag_agent",
            version="1.0.0",
            description="MOON BAG ACTIVATED — Buying PEPE"
        ))
    
    async def run(self):
        self.logger.info("MOON BAG ACTIVATED — Buying PEPE")
        while not self._shutdown_event.is_set():
            await asyncio.sleep(60)
"""
    
    print("Uploading test agent...")
    agent_id = marketplace.add_agent(
        name="Moon Bag Agent",
        author="Test User",
        description="MOON BAG ACTIVATED — Buying PEPE",
        code=test_agent_code
    )
    
    print(f"✓ Agent uploaded successfully! ID: {agent_id}")
    
    # Check if it appears in list
    agents = marketplace.list_agents()
    print(f"  Total agents in marketplace: {len(agents)}")
    
    moon_bag = marketplace.get_agent(agent_id)
    if moon_bag:
        print(f"  Agent found: {moon_bag.name} by {moon_bag.author}")
        print(f"  Status: {moon_bag.status}")
    else:
        print("  ✗ Agent not found after upload")
    
    # Test agent code retrieval
    code = marketplace.get_agent_code(agent_id)
    if code and "MoonBagAgent" in code:
        print("  ✓ Agent code retrievable")
    else:
        print("  ✗ Agent code not retrievable")
        
except Exception as e:
    print(f"✗ Marketplace test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: MEV Event and Council v3
print("\n[TEST 3] MEV Event and Council v3 Integration")
print("-" * 80)

try:
    from core.event_bus import event_bus
    
    print("Publishing fake MEV hit event...")
    
    # Publish a fake MEV event
    event_bus.publish("mev:liquidation_hit", {
        "profit": 750.0,
        "symbol": "BTC/USDT",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, source="test")
    
    print("✓ MEV event published")
    
    # Check if event is in history
    recent_events = event_bus.get_recent_events(count=10, topic="mev:liquidation_hit")
    if recent_events:
        print(f"✓ Event found in history: {len(recent_events)} MEV events")
        for event in recent_events[:1]:
            print(f"  Event: {event.get('topic')} - Profit: ${event.get('data', {}).get('profit', 'N/A')}")
    else:
        print("  ⚠ No MEV events in history (may need to check event bus implementation)")
    
    # Test marketplace agent event
    print("\nPublishing marketplace agent uploaded event...")
    event_bus.publish("marketplace:agent_uploaded", {
        "agent_id": "test_agent_123",
        "name": "Test Agent",
        "author": "Test Author",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, source="marketplace")
    
    print("✓ Marketplace agent event published")
    
    # Check Council v3 subscription (would need to be running)
    print("  Note: Council v3 would need to be running to process events")
    print("  Events are published and available for subscription")
    
except Exception as e:
    print(f"✗ Event bus test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Notification Providers
print("\n[TEST 4] Notification Providers")
print("-" * 80)

try:
    from monitoring.alerting import PushoverProvider, TwilioProvider, AlertingSystem
    
    # Test Pushover (without actual API keys - just check initialization)
    print("Testing Pushover provider initialization...")
    pushover = PushoverProvider("test_key", "test_user")
    print("✓ Pushover provider initialized")
    
    # Test Twilio (without actual credentials)
    print("Testing Twilio provider initialization...")
    twilio = TwilioProvider("test_sid", "test_token", "+1234567890", "+0987654321")
    print("✓ Twilio provider initialized")
    
    # Test AlertingSystem
    print("Testing AlertingSystem...")
    alerting = AlertingSystem(
        enabled=True,
        pushover_api_key="test_key",
        pushover_user_key="test_user"
    )
    print(f"✓ AlertingSystem initialized with {len(alerting.providers)} providers")
    print(f"  PnL threshold: ${alerting.pnl_threshold}")
    print(f"  Drawdown threshold: {alerting.drawdown_threshold*100}%")
    print(f"  MEV profit threshold: ${alerting.mev_profit_threshold}")
    
except Exception as e:
    print(f"✗ Notification test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)
print("All integration tests completed. Check results above.")
print("\nNote: Some tests require:")
print("  - CoinGecko API access for backtesting")
print("  - Actual API keys for Pushover/Twilio")
print("  - Council v3 running to process events")
print("=" * 80)

