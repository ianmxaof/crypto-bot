"""Event-driven communication system for agent coordination."""

import asyncio
import logging
from typing import Dict, List, Callable, Any, AsyncIterator
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Represents an event in the system."""
    topic: str
    data: Dict[str, Any]
    timestamp: str
    source: str = "unknown"


class EventBus:
    """Event bus supporting async pub/sub pattern for agent communication."""
    
    # Critical event topics that should never be dropped
    CRITICAL_TOPICS = {
        "risk:circuit_breaker",
        "risk:position_limit",
        "risk:alert",
        "system:error",
        "system:critical"
    }
    
    def __init__(self, max_queue_size: int = 10000):
        """Initialize event bus.
        
        Args:
            max_queue_size: Maximum queue size before backpressure kicks in
        """
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._max_queue_size = max_queue_size
        self._running = False
        self._task: asyncio.Task = None
        self._dropped_events = 0
        self._shutdown = asyncio.Event()
        
    def subscribe(self, topic: str, callback: Callable, async_callback: bool = False):
        """Subscribe to events on a topic.
        
        Args:
            topic: Event topic to subscribe to
            callback: Function to call when event is published
            async_callback: Whether the callback is async
        """
        if async_callback:
            self._async_subscribers[topic].append(callback)
        else:
            self._subscribers[topic].append(callback)
        logger.debug(f"Subscribed to topic '{topic}'")
        
    def unsubscribe(self, topic: str, callback: Callable):
        """Unsubscribe from events on a topic."""
        if callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)
        if callback in self._async_subscribers[topic]:
            self._async_subscribers[topic].remove(callback)
        logger.debug(f"Unsubscribed from topic '{topic}'")
        
    def publish(self, topic: str, data: Dict[str, Any], source: str = "unknown"):
        """Publish an event synchronously (queues for async processing).
        
        Args:
            topic: Event topic
            data: Event data payload
            source: Source identifier
        """
        event = Event(
            topic=topic,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source
        )
        try:
            self._event_queue.put_nowait(event)
        except asyncio.QueueFull:
            # Critical events should never be dropped
            if topic in self.CRITICAL_TOPICS:
                # For critical events, log error and try to process immediately
                logger.critical(
                    f"Event queue full but CRITICAL event received: {topic}. "
                    f"Queue size: {self._event_queue.qsize()}"
                )
                # Try to make room by dropping oldest non-critical event
                try:
                    # This is a best-effort attempt
                    dropped = self._event_queue.get_nowait()
                    self._dropped_events += 1
                    logger.warning(f"Dropped non-critical event to make room: {dropped.topic}")
                    self._event_queue.put_nowait(event)
                except asyncio.QueueEmpty:
                    # If we can't make room, log critical error
                    logger.critical(f"CRITICAL event {topic} may be lost due to full queue!")
            else:
                # Non-critical events can be dropped
                self._dropped_events += 1
                if self._dropped_events % 100 == 0:  # Log every 100 dropped events
                    logger.warning(
                        f"Event queue full, dropped {self._dropped_events} events. "
                        f"Queue size: {self._event_queue.qsize()}, topic: {topic}"
                    )
            
    async def publish_async(self, topic: str, data: Dict[str, Any], source: str = "unknown"):
        """Publish an event asynchronously."""
        event = Event(
            topic=topic,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source=source
        )
        await self._event_queue.put(event)
        
    async def _process_events(self):
        """Background task to process queued events."""
        while self._running and not self._shutdown.is_set():
            try:
                # Wait for event with timeout to allow shutdown
                try:
                    event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                    
                # Notify sync subscribers (run in executor to avoid blocking)
                for callback in self._subscribers.get(event.topic, []):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(event))
                        else:
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(None, callback, event)
                    except Exception as e:
                        logger.error(f"Error in sync subscriber for {event.topic}: {e}")
                        
                # Notify async subscribers
                for callback in self._async_subscribers.get(event.topic, []):
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Error in async subscriber for {event.topic}: {e}")
                        
                # Also notify wildcard subscribers (*)
                for callback in self._subscribers.get("*", []):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            asyncio.create_task(callback(event))
                        else:
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(None, callback, event)
                    except Exception as e:
                        logger.error(f"Error in wildcard subscriber: {e}")
                        
                for callback in self._async_subscribers.get("*", []):
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Error in wildcard async subscriber: {e}")
                
                # Mark event as processed
                self._event_queue.task_done()
                        
            except Exception as e:
                logger.error(f"Error processing event: {e}")
                # Still mark as done to prevent queue blocking
                try:
                    self._event_queue.task_done()
                except ValueError:
                    pass  # Already marked as done
                
    def start(self):
        """Start the event bus background processor."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._process_events())
            logger.info("Event bus started")
            
    def stop(self):
        """Stop the event bus background processor."""
        if self._running:
            self._running = False
            self._shutdown.set()
            if self._task:
                self._task.cancel()
            logger.info("Event bus stopped")
    
    async def shutdown(self, timeout: float = 30.0):
        """Graceful shutdown - process remaining events then stop.
        
        Args:
            timeout: Maximum time to wait for queue to drain
        """
        self._shutdown.set()
        
        # Wait for queue to drain
        try:
            await asyncio.wait_for(self._drain_queue(), timeout=timeout)
        except asyncio.TimeoutError:
            remaining = self._event_queue.qsize()
            logger.warning(
                f"Shutdown timeout, {remaining} events not processed. "
                f"Dropped {self._dropped_events} events total."
            )
        
        self.stop()
    
    async def _drain_queue(self):
        """Drain the event queue by processing all remaining events."""
        while not self._event_queue.empty():
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=0.1)
                # Process event synchronously during shutdown
                for callback in self._subscribers.get(event.topic, []):
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.error(f"Error in subscriber during shutdown: {e}")
                
                for callback in self._async_subscribers.get(event.topic, []):
                    try:
                        await callback(event)
                    except Exception as e:
                        logger.error(f"Error in async subscriber during shutdown: {e}")
                
                self._event_queue.task_done()
            except asyncio.TimeoutError:
                break
        
        await self._event_queue.join()
    
    def get_queue_size(self) -> int:
        """Get current queue size.
        
        Returns:
            Number of events in queue
        """
        return self._event_queue.qsize()
    
    def get_dropped_count(self) -> int:
        """Get number of dropped events.
        
        Returns:
            Total number of dropped events
        """
        return self._dropped_events
            
    async def subscribe_async(self, topic: str) -> AsyncIterator[Event]:
        """Create an async iterator that yields events for a topic.
        
        Usage:
            async for event in event_bus.subscribe_async("my_topic"):
                print(event.data)
        """
        queue: asyncio.Queue = asyncio.Queue()
        
        async def handler(event: Event):
            await queue.put(event)
            
        self.subscribe(topic, handler, async_callback=True)
        
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            self.unsubscribe(topic, handler)


# Global event bus instance
event_bus = EventBus()

