"""Data service for fetching and aggregating dashboard data."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import pandas as pd

from core.memory.chrono import ChronologicalMemory
from monitoring.metrics_collector import MetricsCollector
from config.settings import settings
from dashboard.utils import to_float
from config.simulation_state import (
    get_progress_percentage,
    get_elapsed_sim_days,
    get_cycle_count,
    get_current_phase,
    read_simulation_state
)

logger = logging.getLogger(__name__)


class DashboardDataService:
    """Service for fetching and aggregating data for the dashboard."""
    
    def __init__(self):
        """Initialize data service."""
        # Ensure memory directory exists
        settings.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        
        self.memory = ChronologicalMemory(
            namespace="crypto_pnl",
            persist_path=settings.MEMORY_DIR / "crypto_pnl.json"
        )
        self.metrics_collector = MetricsCollector()
        self._cache: Dict[str, Any] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(seconds=2)  # Cache for 2 seconds
        self._last_sim_state_hash: Optional[str] = None  # Track simulation state changes
    
    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached data is still valid."""
        if key not in self._cache_time:
            return False
        
        # Check TTL
        if datetime.now(timezone.utc) - self._cache_time[key] >= self._cache_ttl:
            return False
        
        # Check if simulation state changed (invalidate cache on state changes)
        try:
            current_state = read_simulation_state()
            # Create a simple hash of state for comparison
            state_hash = str(current_state.get('running', False)) + str(current_state.get('last_updated', ''))
            if self._last_sim_state_hash is not None and state_hash != self._last_sim_state_hash:
                # State changed, invalidate cache
                self._last_sim_state_hash = state_hash
                return False
            self._last_sim_state_hash = state_hash
        except Exception:
            pass
        
        return True
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached data if valid."""
        if self._is_cache_valid(key):
            return self._cache.get(key)
        return None
    
    def _set_cache(self, key: str, value: Any):
        """Set cached data."""
        self._cache[key] = value
        self._cache_time[key] = datetime.now(timezone.utc)
    
    def get_pnl_data(self, limit: int = 1000) -> pd.DataFrame:
        """Get PnL data as DataFrame.
        
        Args:
            limit: Maximum number of data points
            
        Returns:
            DataFrame with timestamp, pnl, agent, balance columns
        """
        cache_key = f"pnl_data_{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        entries = self.memory.get_recent(limit)
        if not entries:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=['timestamp', 'pnl', 'agent', 'balance', 'cumulative_pnl'])
        
        # Convert to DataFrame
        data = []
        cumulative_pnl = 0.0
        
        for entry in entries:
            timestamp = entry.get('timestamp', datetime.now(timezone.utc).isoformat())
            pnl = float(entry.get('pnl', entry.get('profit', 0.0)))
            agent = entry.get('agent', entry.get('source', 'unknown'))
            balance = float(entry.get('balance', entry.get('total_value', 0.0)))
            
            cumulative_pnl += pnl
            
            data.append({
                'timestamp': pd.to_datetime(timestamp),
                'pnl': pnl,
                'agent': agent,
                'balance': balance,
                'cumulative_pnl': cumulative_pnl,
                'trade_id': entry.get('trade_id', ''),
                'symbol': entry.get('symbol', ''),
            })
        
        df = pd.DataFrame(data)
        
        # Sort by timestamp
        if not df.empty:
            df = df.sort_values('timestamp')
        
        self._set_cache(cache_key, df)
        return df
    
    def get_pnl_summary(self) -> Dict[str, Any]:
        """Get PnL summary statistics.
        
        Returns:
            Dictionary with summary metrics
        """
        cache_key = "pnl_summary"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        summary = self.memory.get_pnl_summary()
        
        # Add additional calculated metrics
        df = self.get_pnl_data(limit=1000)
        if not df.empty:
            # Calculate max drawdown
            if 'balance' in df.columns and len(df) > 1:
                peak = df['balance'].expanding().max()
                drawdown = (df['balance'] - peak) / peak * 100
                summary['max_drawdown_pct'] = float(drawdown.min())
            else:
                summary['max_drawdown_pct'] = 0.0
            
            # Current balance
            if 'balance' in df.columns:
                summary['current_balance'] = to_float(df['balance'].iloc[-1])
            else:
                summary['current_balance'] = to_float(settings.SIMULATION_STARTING_BALANCE)
        else:
            summary['max_drawdown_pct'] = 0.0
            summary['current_balance'] = to_float(settings.SIMULATION_STARTING_BALANCE)
        
        self._set_cache(cache_key, summary)
        return summary
    
    def get_agent_performance(self) -> pd.DataFrame:
        """Get performance breakdown by agent.
        
        Returns:
            DataFrame with agent performance metrics
        """
        cache_key = "agent_performance"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        df = self.get_pnl_data(limit=10000)
        
        if df.empty:
            return pd.DataFrame(columns=['agent', 'total_pnl', 'trade_count', 'win_rate', 'avg_pnl'])
        
        # Group by agent
        agent_stats = []
        for agent in df['agent'].unique():
            agent_df = df[df['agent'] == agent]
            pnls = agent_df['pnl'].tolist()
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            
            agent_stats.append({
                'agent': agent,
                'total_pnl': float(agent_df['pnl'].sum()),
                'trade_count': len(agent_df),
                'win_rate': len(wins) / len(pnls) if pnls else 0.0,
                'avg_pnl': float(agent_df['pnl'].mean()) if len(agent_df) > 0 else 0.0,
                'max_win': float(max(wins)) if wins else 0.0,
                'max_loss': float(min(losses)) if losses else 0.0,
            })
        
        result_df = pd.DataFrame(agent_stats)
        result_df = result_df.sort_values('total_pnl', ascending=False)
        
        self._set_cache(cache_key, result_df)
        return result_df
    
    def get_recent_trades(self, limit: int = 100) -> pd.DataFrame:
        """Get recent trades.
        
        Args:
            limit: Maximum number of trades
            
        Returns:
            DataFrame with recent trades
        """
        cache_key = f"recent_trades_{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        entries = self.memory.get_recent(limit)
        
        trades = []
        for entry in entries:
            if 'pnl' in entry or 'profit' in entry or 'symbol' in entry:
                trades.append({
                    'timestamp': pd.to_datetime(entry.get('timestamp', datetime.now(timezone.utc).isoformat())),
                    'symbol': entry.get('symbol', ''),
                    'agent': entry.get('agent', entry.get('source', 'unknown')),
                    'pnl': float(entry.get('pnl', entry.get('profit', 0.0))),
                    'side': entry.get('side', ''),
                    'size': float(entry.get('size', entry.get('amount', 0.0))),
                    'price': float(entry.get('price', 0.0)),
                })
        
        if not trades:
            return pd.DataFrame(columns=['timestamp', 'symbol', 'agent', 'pnl', 'side', 'size', 'price'])
        
        df = pd.DataFrame(trades)
        df = df.sort_values('timestamp', ascending=False)
        
        self._set_cache(cache_key, df)
        return df
    
    def get_balance_history(self, limit: int = 1000) -> pd.DataFrame:
        """Get balance history.
        
        Args:
            limit: Maximum number of data points
            
        Returns:
            DataFrame with timestamp and balance columns
        """
        df = self.get_pnl_data(limit=limit)
        
        if df.empty:
            return pd.DataFrame(columns=['timestamp', 'balance', 'free', 'used'])
        
        # Extract balance data
        if 'balance' in df.columns:
            balance_df = df[['timestamp', 'balance']].copy()
            balance_df['free'] = balance_df['balance']  # Simplified
            balance_df['used'] = 0.0  # Simplified
        else:
            balance_df = pd.DataFrame(columns=['timestamp', 'balance', 'free', 'used'])
        
        return balance_df
    
    def get_order_flow_data(self, limit: int = 1000) -> pd.DataFrame:
        """Get order flow data for heatmap.
        
        Args:
            limit: Maximum number of orders
            
        Returns:
            DataFrame with order flow data
        """
        cache_key = f"order_flow_{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        entries = self.memory.get_recent(limit)
        
        orders = []
        for entry in entries:
            if 'symbol' in entry and ('side' in entry or 'order' in str(entry).lower()):
                orders.append({
                    'timestamp': pd.to_datetime(entry.get('timestamp', datetime.now(timezone.utc).isoformat())),
                    'symbol': entry.get('symbol', ''),
                    'side': entry.get('side', 'unknown'),
                    'amount': float(entry.get('size', entry.get('amount', 1.0))),
                    'agent': entry.get('agent', entry.get('source', 'unknown')),
                })
        
        if not orders:
            return pd.DataFrame(columns=['timestamp', 'symbol', 'side', 'amount', 'agent'])
        
        df = pd.DataFrame(orders)
        df = df.sort_values('timestamp')
        
        self._set_cache(cache_key, df)
        return df
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics.
        
        Returns:
            Dictionary with risk metrics
        """
        cache_key = "risk_metrics"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        df = self.get_pnl_data(limit=1000)
        
        metrics = {
            'max_position_size_usd': to_float(settings.MAX_POSITION_SIZE_USD),
            'max_daily_loss_percent': to_float(settings.MAX_DAILY_LOSS_PERCENT),
            'max_daily_loss_usd': to_float(settings.MAX_DAILY_LOSS_USD),
        }
        
        if not df.empty and 'balance' in df.columns:
            # Calculate drawdown
            peak = df['balance'].expanding().max()
            drawdown = (df['balance'] - peak) / peak * 100
            metrics['current_drawdown_pct'] = float(drawdown.iloc[-1])
            metrics['max_drawdown_pct'] = float(drawdown.min())
            
            # Current balance
            metrics['current_balance'] = float(df['balance'].iloc[-1])
            
            # Daily P&L (last 24 hours)
            if len(df) > 1:
                now = datetime.now(timezone.utc)
                day_ago = now - timedelta(days=1)
                recent_df = df[df['timestamp'] >= day_ago]
                if not recent_df.empty:
                    metrics['daily_pnl'] = float(recent_df['pnl'].sum())
                else:
                    metrics['daily_pnl'] = 0.0
            else:
                metrics['daily_pnl'] = 0.0
        else:
            metrics['current_drawdown_pct'] = 0.0
            metrics['max_drawdown_pct'] = 0.0
            metrics['current_balance'] = to_float(settings.SIMULATION_STARTING_BALANCE)
            metrics['daily_pnl'] = 0.0
        
        self._set_cache(cache_key, metrics)
        return metrics
    
    def get_simulation_progress(self) -> Dict[str, Any]:
        """Get simulation progress information.
        
        Returns:
            Dictionary with progress metrics
        """
        cache_key = "simulation_progress"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached
        
        state = read_simulation_state()
        
        progress = {
            'is_running': state.get('running', False),
            'progress_pct': get_progress_percentage(),
            'elapsed_sim_days': get_elapsed_sim_days(),
            'target_days': state.get('days', 30),
            'cycle_count': get_cycle_count(),
            'current_phase': get_current_phase(),
            'speed': state.get('speed', 100),
            'start_time': state.get('start_time'),
            'elapsed_real_seconds': state.get('elapsed_real_seconds', 0.0)
        }
        
        self._set_cache(cache_key, progress)
        return progress
    
    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        self._cache_time.clear()
        logger.debug("Dashboard cache cleared")
    
    def get_recent_events(self, limit: int = 100, topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent events from event bus.
        
        Args:
            limit: Maximum number of events to retrieve
            topic: Optional topic filter (None for all topics)
            
        Returns:
            List of event dictionaries
        """
        cache_key = f"events_{limit}_{topic or 'all'}"
        if self._is_cache_valid(cache_key):
            return self._get_cached(cache_key)
        
        try:
            from core.event_bus import event_bus
            events = event_bus.get_recent_events(count=limit, topic=topic)
            self._set_cache(cache_key, events)
            return events
        except Exception as e:
            logger.warning(f"Error fetching events: {e}")
            return []
    
    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event bus statistics.
        
        Returns:
            Dictionary with event statistics
        """
        cache_key = "event_stats"
        if self._is_cache_valid(cache_key):
            return self._get_cached(cache_key)
        
        try:
            from core.event_bus import event_bus
            stats = {
                "queue_size": event_bus.get_queue_size(),
                "dropped_events": event_bus.get_dropped_count(),
                "max_queue_size": event_bus._max_queue_size
            }
            
            # Get event counts by topic
            events = event_bus.get_recent_events(count=1000)
            topic_counts = {}
            for event in events:
                topic = event.get("topic", "unknown")
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            stats["events_by_topic"] = topic_counts
            stats["total_events"] = len(events)
            
            self._set_cache(cache_key, stats)
            return stats
        except Exception as e:
            logger.warning(f"Error fetching event statistics: {e}")
            return {
                "queue_size": 0,
                "dropped_events": 0,
                "max_queue_size": 10000,
                "events_by_topic": {},
                "total_events": 0
            }

