"""Simple integration tests without network calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

print("=" * 80)
print("INTEGRATION TESTS (No Network Calls)")
print("=" * 80)

# Test 1: Marketplace Agent Upload
print("\n[TEST 1] Marketplace Agent Upload")
print("-" * 80)

try:
    from agents.marketplace import get_marketplace
    
    marketplace = get_marketplace()
    
    # Fixed test agent code
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
    
    print(f"✓ Agent uploaded! ID: {agent_id}")
    
    # Check if it appears in list
    agents = marketplace.list_agents()
    print(f"✓ Total agents: {len(agents)}")
    
    moon_bag = marketplace.get_agent(agent_id)
    if moon_bag:
        print(f"✓ Found: {moon_bag.name} by {moon_bag.author}")
        print(f"  Status: {moon_bag.status}")
    else:
        print("✗ Agent not found")
    
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Event Bus
print("\n[TEST 2] Event Bus - MEV Event")
print("-" * 80)

try:
    from core.event_bus import event_bus
    from datetime import datetime, timezone
    
    print("Publishing MEV event...")
    event_bus.publish("mev:liquidation_hit", {
        "profit": 750.0,
        "symbol": "BTC/USDT"
    }, source="test")
    
    print("✓ MEV event published")
    
    recent = event_bus.get_recent_events(count=5, topic="mev:liquidation_hit")
    print(f"✓ Found {len(recent)} MEV events in history")
    
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: Marketplace Event
print("\n[TEST 3] Marketplace Event for Council v3")
print("-" * 80)

try:
    from core.event_bus import event_bus
    from datetime import datetime, timezone
    
    print("Publishing marketplace agent event...")
    event_bus.publish("marketplace:agent_uploaded", {
        "agent_id": "test_123",
        "name": "Test Agent",
        "author": "Test"
    }, source="marketplace")
    
    print("✓ Marketplace event published")
    print("  (Council v3 would process this if running)")
    
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Tests complete!")
print("=" * 80)

