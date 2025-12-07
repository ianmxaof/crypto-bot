"""Community agent marketplace for sharing and discovering trading agents."""

import json
import logging
import ast
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)

MARKETPLACE_DIR = Path(__file__).parent.parent / "data" / "marketplace"
AGENTS_FILE = MARKETPLACE_DIR / "agents.json"
CUSTOM_AGENTS_DIR = Path(__file__).parent / "custom"

# Ensure directories exist
MARKETPLACE_DIR.mkdir(parents=True, exist_ok=True)
CUSTOM_AGENTS_DIR.mkdir(parents=True, exist_ok=True)


class AgentMetadata:
    """Metadata for a marketplace agent."""
    
    def __init__(
        self,
        id: str,
        name: str,
        author: str,
        description: str,
        code: str,
        upload_date: str,
        metrics: Optional[Dict[str, float]] = None,
        sharpe: float = 0.0,
        apr: float = 0.0,
        max_drawdown: float = 0.0,
        downloads: int = 0,
        status: str = "pending"  # pending, tested, approved, rejected
    ):
        self.id = id
        self.name = name
        self.author = author
        self.description = description
        self.code = code
        self.upload_date = upload_date
        self.metrics = metrics or {}
        self.sharpe = sharpe
        self.apr = apr
        self.max_drawdown = max_drawdown
        self.downloads = downloads
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "code": self.code,
            "upload_date": self.upload_date,
            "metrics": self.metrics,
            "sharpe": self.sharpe,
            "apr": self.apr,
            "max_drawdown": self.max_drawdown,
            "downloads": self.downloads,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMetadata':
        """Create from dictionary."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            author=data.get("author", ""),
            description=data.get("description", ""),
            code=data.get("code", ""),
            upload_date=data.get("upload_date", ""),
            metrics=data.get("metrics", {}),
            sharpe=data.get("sharpe", 0.0),
            apr=data.get("apr", 0.0),
            max_drawdown=data.get("max_drawdown", 0.0),
            downloads=data.get("downloads", 0),
            status=data.get("status", "pending")
        )


class AgentMarketplace:
    """Marketplace for trading agents."""
    
    def __init__(self):
        """Initialize marketplace."""
        self._agents: Dict[str, AgentMetadata] = {}
        self._load_agents()
    
    def _load_agents(self):
        """Load agents from storage."""
        if AGENTS_FILE.exists():
            try:
                with open(AGENTS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for agent_data in data.get("agents", []):
                        agent = AgentMetadata.from_dict(agent_data)
                        self._agents[agent.id] = agent
                logger.info(f"Loaded {len(self._agents)} agents from marketplace")
            except Exception as e:
                logger.error(f"Error loading agents: {e}")
                self._agents = {}
        else:
            self._agents = {}
    
    def _save_agents(self):
        """Save agents to storage."""
        try:
            data = {
                "agents": [agent.to_dict() for agent in self._agents.values()],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            with open(AGENTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self._agents)} agents to marketplace")
        except Exception as e:
            logger.error(f"Error saving agents: {e}")
            raise
    
    def validate_agent_code(self, code: str) -> tuple[bool, Optional[str]]:
        """Validate agent code syntax.
        
        Args:
            code: Python code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Parse code to check syntax
            ast.parse(code)
            
            # Check for required imports/classes
            if "Agent" not in code and "StrategyAgent" not in code:
                return False, "Code must define an Agent or StrategyAgent class"
            
            # Basic safety check - no dangerous operations
            dangerous_patterns = [
                "__import__",
                "eval(",
                "exec(",
                "open(",
                "file(",
                "input(",
                "raw_input(",
            ]
            for pattern in dangerous_patterns:
                if pattern in code:
                    return False, f"Code contains potentially unsafe operation: {pattern}"
            
            return True, None
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def add_agent(
        self,
        name: str,
        author: str,
        description: str,
        code: str
    ) -> Optional[str]:
        """Add a new agent to the marketplace.
        
        Args:
            name: Agent name
            author: Author name
            description: Agent description
            code: Agent code
            
        Returns:
            Agent ID if successful, None if validation failed
        """
        # Validate code
        is_valid, error = self.validate_agent_code(code)
        if not is_valid:
            logger.warning(f"Agent validation failed: {error}")
            raise ValueError(f"Invalid agent code: {error}")
        
        # Create agent metadata
        agent_id = str(uuid.uuid4())
        agent = AgentMetadata(
            id=agent_id,
            name=name,
            author=author,
            description=description,
            code=code,
            upload_date=datetime.now(timezone.utc).isoformat(),
            status="pending"
        )
        
        # Save agent code to file
        agent_file = CUSTOM_AGENTS_DIR / f"{agent_id}.py"
        try:
            with open(agent_file, 'w', encoding='utf-8') as f:
                f.write(code)
        except Exception as e:
            logger.error(f"Error saving agent code: {e}")
            raise
        
        # Add to marketplace
        self._agents[agent_id] = agent
        self._save_agents()
        
        # Publish event for Council v3 evaluation
        try:
            from core.event_bus import event_bus
            event_bus.publish("marketplace:agent_uploaded", {
                "agent_id": agent_id,
                "name": name,
                "author": author,
                "timestamp": agent.upload_date
            }, source="marketplace")
        except Exception as e:
            logger.debug(f"Event bus not available: {e}")
        
        logger.info(f"Added agent '{name}' by {author} to marketplace (ID: {agent_id})")
        return agent_id
    
    def get_agent(self, agent_id: str) -> Optional[AgentMetadata]:
        """Get agent by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent metadata or None if not found
        """
        return self._agents.get(agent_id)
    
    def list_agents(
        self,
        sort_by: str = "sharpe",
        status_filter: Optional[str] = None
    ) -> List[AgentMetadata]:
        """List all agents.
        
        Args:
            sort_by: Sort field ("sharpe", "apr", "downloads", "upload_date")
            status_filter: Filter by status ("pending", "tested", "approved", "rejected")
            
        Returns:
            List of agents, sorted
        """
        agents = list(self._agents.values())
        
        # Filter by status
        if status_filter:
            agents = [a for a in agents if a.status == status_filter]
        
        # Sort
        reverse = True  # Default to descending
        if sort_by == "sharpe":
            agents.sort(key=lambda x: x.sharpe, reverse=reverse)
        elif sort_by == "apr":
            agents.sort(key=lambda x: x.apr, reverse=reverse)
        elif sort_by == "downloads":
            agents.sort(key=lambda x: x.downloads, reverse=reverse)
        elif sort_by == "upload_date":
            agents.sort(key=lambda x: x.upload_date, reverse=reverse)
        else:
            # Default: sort by sharpe
            agents.sort(key=lambda x: x.sharpe, reverse=reverse)
        
        return agents
    
    def get_leaderboard(self, limit: int = 10) -> List[AgentMetadata]:
        """Get top agents by Sharpe ratio.
        
        Args:
            limit: Number of agents to return
            
        Returns:
            List of top agents
        """
        agents = self.list_agents(sort_by="sharpe", status_filter="tested")
        return agents[:limit]
    
    def update_agent_metrics(
        self,
        agent_id: str,
        metrics: Dict[str, float],
        sharpe: Optional[float] = None,
        apr: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        status: Optional[str] = None
    ) -> bool:
        """Update agent metrics after testing.
        
        Args:
            agent_id: Agent ID
            metrics: Dictionary of metrics
            sharpe: Sharpe ratio
            apr: APR
            max_drawdown: Max drawdown
            status: Status update
            
        Returns:
            True if successful
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent {agent_id} not found")
            return False
        
        agent = self._agents[agent_id]
        agent.metrics.update(metrics)
        
        if sharpe is not None:
            agent.sharpe = sharpe
        if apr is not None:
            agent.apr = apr
        if max_drawdown is not None:
            agent.max_drawdown = max_drawdown
        if status is not None:
            agent.status = status
        
        self._save_agents()
        logger.info(f"Updated metrics for agent {agent_id}")
        return True
    
    def increment_downloads(self, agent_id: str) -> bool:
        """Increment download count for an agent.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            True if successful
        """
        if agent_id not in self._agents:
            return False
        
        self._agents[agent_id].downloads += 1
        self._save_agents()
        return True
    
    def get_agent_code(self, agent_id: str) -> Optional[str]:
        """Get agent code by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent code or None if not found
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        
        # Try to read from file first
        agent_file = CUSTOM_AGENTS_DIR / f"{agent_id}.py"
        if agent_file.exists():
            try:
                with open(agent_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Error reading agent file: {e}")
        
        # Fallback to stored code
        return agent.code


# Global marketplace instance
_marketplace_instance: Optional[AgentMarketplace] = None


def get_marketplace() -> AgentMarketplace:
    """Get global marketplace instance.
    
    Returns:
        AgentMarketplace instance
    """
    global _marketplace_instance
    if _marketplace_instance is None:
        _marketplace_instance = AgentMarketplace()
    return _marketplace_instance


async def test_agent_in_simulation(
    agent_id: str,
    initial_capital: Decimal = Decimal('10000'),
    simulation_days: int = 7
) -> Dict[str, Any]:
    """Test an agent in a simulation.
    
    Args:
        agent_id: Agent ID to test
        initial_capital: Starting capital
        simulation_days: Number of days to simulate
        
    Returns:
        Dictionary with test results (metrics, sharpe, apr, etc.)
    """
    marketplace = get_marketplace()
    agent = marketplace.get_agent(agent_id)
    
    if not agent:
        raise ValueError(f"Agent {agent_id} not found")
    
    try:
        # Import agent code dynamically
        import importlib.util
        import sys
        
        # Create a module from the code
        spec = importlib.util.spec_from_loader(
            f"agent_{agent_id}",
            loader=None
        )
        module = importlib.util.module_from_spec(spec)
        
        # Execute agent code in module namespace
        exec(agent.code, module.__dict__)
        
        # Find Agent class in module
        agent_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                hasattr(obj, '__bases__') and
                any('Agent' in str(base) for base in obj.__bases__)):
                agent_class = obj
                break
        
        if not agent_class:
            raise ValueError("No Agent class found in code")
        
        # Create agent instance
        agent_instance = agent_class()
        
        # Run simulation (simplified - would use actual simulation framework)
        # For now, return mock metrics
        # In production, this would:
        # 1. Create mock exchange
        # 2. Run agent for simulation_days
        # 3. Calculate metrics from results
        
        logger.info(f"Testing agent {agent_id} in simulation")
        
        # Placeholder: Return mock results
        # TODO: Integrate with actual simulation framework
        results = {
            "sharpe": 1.5,  # Mock value
            "apr": 120.0,   # Mock value
            "max_drawdown": 0.05,  # Mock value
            "total_return": 0.15,  # Mock value
            "win_rate": 0.65,  # Mock value
            "trades": 42,  # Mock value
            "status": "tested"
        }
        
        # Update agent metrics
        marketplace.update_agent_metrics(
            agent_id,
            metrics=results,
            sharpe=results["sharpe"],
            apr=results["apr"],
            max_drawdown=results["max_drawdown"],
            status="tested"
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Error testing agent {agent_id}: {e}", exc_info=True)
        raise ValueError(f"Agent testing failed: {e}")

