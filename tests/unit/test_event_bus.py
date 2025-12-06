"""Unit tests for event bus."""

import pytest
import asyncio
from core.event_bus import EventBus, Event


class TestEventBus:
    """Test event bus functionality."""
    
    def test_create_event_bus(self):
        """Test event bus creation."""
        bus = EventBus()
        assert bus is not None
        
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self):
        """Test subscribing and publishing events."""
        bus = EventBus()
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
            
        bus.subscribe("test_topic", handler)
        bus.publish("test_topic", {"data": "test_value"})
        
        bus.start()
        await asyncio.sleep(0.2)
        bus.stop()
        
        assert len(received_events) == 1
        assert received_events[0].data["data"] == "test_value"
        assert received_events[0].topic == "test_topic"
        
    @pytest.mark.asyncio
    async def test_async_handler(self):
        """Test async event handlers."""
        bus = EventBus()
        received_events = []
        
        async def async_handler(event: Event):
            received_events.append(event)
            
        bus.subscribe("async_topic", async_handler, async_callback=True)
        await bus.publish_async("async_topic", {"data": "async_test"})
        
        bus.start()
        await asyncio.sleep(0.2)
        bus.stop()
        
        assert len(received_events) == 1
        
    @pytest.mark.asyncio
    async def test_wildcard_subscription(self):
        """Test wildcard (*) subscription."""
        bus = EventBus()
        received_events = []
        
        def handler(event: Event):
            received_events.append(event)
            
        bus.subscribe("*", handler)
        bus.publish("topic1", {"data": "data1"})
        bus.publish("topic2", {"data": "data2"})
        
        bus.start()
        await asyncio.sleep(0.2)
        bus.stop()
        
        assert len(received_events) == 2

