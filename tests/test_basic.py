"""Basic tests for core components."""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timezone

from core.event_bus import EventBus, Event
from core.rate_limiter import RateLimiter
from core.memory.chrono import ChronologicalMemory
from core.agent_base import Agent, AgentConfig, AgentStatus


class TestEventBus:
    """Test event bus functionality."""
    
    def test_event_bus_creation(self):
        """Test that event bus can be created."""
        bus = EventBus()
        assert bus is not None
        
    @pytest.mark.asyncio
    async def test_event_subscribe_publish(self):
        """Test subscribing to and publishing events."""
        bus = EventBus()
        events_received = []
        
        def handler(event: Event):
            events_received.append(event)
            
        bus.subscribe("test_topic", handler)
        bus.publish("test_topic", {"data": "test"})
        
        # Process events
        bus.start()
        await asyncio.sleep(0.1)
        bus.stop()
        
        assert len(events_received) > 0
        assert events_received[0].data["data"] == "test"
        
    @pytest.mark.asyncio
    async def test_async_subscribe(self):
        """Test async event subscription."""
        bus = EventBus()
        events_received = []
        
        async def async_handler(event: Event):
            events_received.append(event)
            
        bus.subscribe("async_topic", async_handler, async_callback=True)
        await bus.publish_async("async_topic", {"data": "async_test"})
        
        bus.start()
        await asyncio.sleep(0.1)
        bus.stop()
        
        assert len(events_received) > 0


class TestRateLimiter:
    """Test rate limiter."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_acquire(self):
        """Test rate limiter token acquisition."""
        limiter = RateLimiter(calls_per_second=10.0)
        
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()
        
        # Should allow 2 calls quickly
        assert (end_time - start_time) < 0.5
        
    @pytest.mark.asyncio
    async def test_rate_limiter_throttling(self):
        """Test that rate limiter throttles excessive calls."""
        limiter = RateLimiter(calls_per_second=2.0)
        
        start_time = asyncio.get_event_loop().time()
        for _ in range(3):
            await limiter.acquire()
        end_time = asyncio.get_event_loop().time()
        
        # Should take at least 1 second for 3 calls at 2/sec
        assert (end_time - start_time) >= 0.9


class TestChronologicalMemory:
    """Test chronological memory."""
    
    def test_memory_creation(self):
        """Test memory can be created."""
        memory = ChronologicalMemory("test_namespace")
        assert memory.namespace == "test_namespace"
        assert len(memory.get_all()) == 0
        
    def test_memory_append(self):
        """Test appending to memory."""
        memory = ChronologicalMemory("test")
        memory.append({"key": "value", "number": 123})
        
        entries = memory.get_all()
        assert len(entries) == 1
        assert entries[0]["key"] == "value"
        assert entries[0]["number"] == 123
        
    def test_memory_pnl_summary(self):
        """Test PnL summary calculation."""
        memory = ChronologicalMemory("test_pnl")
        
        # Add some PnL entries
        memory.append({"pnl": 100.0})
        memory.append({"pnl": -50.0})
        memory.append({"pnl": 200.0})
        memory.append({"pnl": -30.0})
        
        summary = memory.get_pnl_summary()
        assert summary["total_pnl"] == 220.0
        assert summary["total_trades"] == 4
        assert summary["win_rate"] == 0.5  # 2 wins, 2 losses
        assert summary["avg_win"] == 150.0  # (100 + 200) / 2
        assert summary["avg_loss"] == -40.0  # (-50 + -30) / 2


class TestAgentBase:
    """Test agent base class."""
    
    def test_agent_creation(self):
        """Test agent can be created."""
        config = AgentConfig(
            name="test_agent",
            version="1.0.0",
            description="Test agent"
        )
        
        class TestAgent(Agent):
            async def run(self):
                pass
                
        agent = TestAgent(config)
        assert agent.config.name == "test_agent"
        assert agent.status == AgentStatus.INITIALIZED
        
    def test_agent_info(self):
        """Test agent info retrieval."""
        config = AgentConfig(
            name="test_agent",
            version="1.0.0",
            description="Test agent"
        )
        
        class TestAgent(Agent):
            async def run(self):
                pass
                
        agent = TestAgent(config)
        info = agent.get_info()
        
        assert info["name"] == "test_agent"
        assert info["version"] == "1.0.0"
        assert info["status"] == "initialized"

