"""Base agent class with lifecycle management."""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent lifecycle status."""
    INITIALIZED = "initialized"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    version: str
    description: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self):
        return f"{self.name} v{self.version}"


class Agent:
    """Base class for all trading agents."""
    
    def __init__(self, config: AgentConfig):
        """Initialize agent.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        self.status = AgentStatus.INITIALIZED
        self._started_at: Optional[datetime] = None
        self._task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._error_count = 0
        self._max_errors = 10
        
        logger.info(f"Agent initialized: {self.config}")
        
    async def start(self):
        """Start the agent."""
        if self.status != AgentStatus.INITIALIZED and self.status != AgentStatus.STOPPED:
            logger.warning(f"Agent {self.config.name} already started or in invalid state: {self.status}")
            return
            
        self.status = AgentStatus.STARTING
        logger.info(f"Starting agent: {self.config.name}")
        
        try:
            await self.on_start()
            self._started_at = datetime.now(timezone.utc)
            self.status = AgentStatus.RUNNING
            
            # Start main task
            self._task = asyncio.create_task(self._run_with_error_handling())
            logger.info(f"Agent {self.config.name} started successfully")
            
        except Exception as e:
            self.status = AgentStatus.ERROR
            logger.error(f"Failed to start agent {self.config.name}: {e}", exc_info=True)
            raise
            
    async def stop(self):
        """Stop the agent gracefully."""
        if self.status == AgentStatus.STOPPED:
            return
            
        self.status = AgentStatus.STOPPING
        logger.info(f"Stopping agent: {self.config.name}")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel task
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        try:
            await self.on_stop()
        except Exception as e:
            logger.error(f"Error in on_stop for {self.config.name}: {e}")
            
        self.status = AgentStatus.STOPPED
        logger.info(f"Agent {self.config.name} stopped")
        
    async def pause(self):
        """Pause the agent (can be resumed)."""
        if self.status != AgentStatus.RUNNING:
            logger.warning(f"Cannot pause agent {self.config.name} in state {self.status}")
            return
            
        self.status = AgentStatus.PAUSED
        logger.info(f"Agent {self.config.name} paused")
        await self.on_pause()
        
    async def resume(self):
        """Resume a paused agent."""
        if self.status != AgentStatus.PAUSED:
            logger.warning(f"Cannot resume agent {self.config.name} in state {self.status}")
            return
            
        self.status = AgentStatus.RUNNING
        logger.info(f"Agent {self.config.name} resumed")
        await self.on_resume()
        
    async def _run_with_error_handling(self):
        """Run agent main loop with error handling."""
        try:
            await self.run()
        except asyncio.CancelledError:
            logger.info(f"Agent {self.config.name} task cancelled")
            raise
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error in agent {self.config.name} (error #{self._error_count}): {e}", exc_info=True)
            
            if self._error_count >= self._max_errors:
                self.status = AgentStatus.ERROR
                logger.critical(f"Agent {self.config.name} exceeded max errors ({self._max_errors}), stopping")
            else:
                # Wait before retrying
                await asyncio.sleep(min(2 ** self._error_count, 60))
                if self.status == AgentStatus.RUNNING:
                    # Restart run loop
                    self._task = asyncio.create_task(self._run_with_error_handling())
                    
    async def run(self):
        """Main agent loop - override in subclasses.
        
        This method should be an async generator or long-running coroutine.
        """
        raise NotImplementedError("Subclasses must implement run()")
        
    async def on_start(self):
        """Called when agent starts - override for initialization."""
        pass
        
    async def on_stop(self):
        """Called when agent stops - override for cleanup."""
        pass
        
    async def on_pause(self):
        """Called when agent is paused - override for pause handling."""
        pass
        
    async def on_resume(self):
        """Called when agent is resumed - override for resume handling."""
        pass
        
    def is_running(self) -> bool:
        """Check if agent is currently running."""
        return self.status == AgentStatus.RUNNING
        
    def get_uptime(self) -> Optional[float]:
        """Get agent uptime in seconds."""
        if self._started_at:
            return (datetime.now(timezone.utc) - self._started_at).total_seconds()
        return None
        
    def get_info(self) -> Dict[str, Any]:
        """Get agent information dictionary."""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "description": self.config.description,
            "status": self.status.value,
            "enabled": self.config.enabled,
            "uptime_seconds": self.get_uptime(),
            "error_count": self._error_count,
            "started_at": self._started_at.isoformat() if self._started_at else None
        }

