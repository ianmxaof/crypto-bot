"""Collect and aggregate trading metrics."""

import logging
from typing import Dict, List
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collect and aggregate trading metrics."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: List[Dict] = []
        
    def record_metric(self, name: str, value: Decimal, timestamp: Optional[datetime] = None):
        """Record a metric.
        
        Args:
            name: Metric name
            value: Metric value
            timestamp: Timestamp (default: now)
        """
        self.metrics.append({
            "name": name,
            "value": float(value),
            "timestamp": (timestamp or datetime.now(timezone.utc)).isoformat()
        })
        
    def get_latest_metrics(self) -> Dict:
        """Get latest metrics.
        
        Returns:
            Dictionary of latest metric values
        """
        latest = {}
        for metric in reversed(self.metrics):
            if metric["name"] not in latest:
                latest[metric["name"]] = metric["value"]
        return latest
        
    def get_metrics_summary(self) -> Dict:
        """Get metrics summary.
        
        Returns:
            Summary dictionary
        """
        if not self.metrics:
            return {}
            
        # Group by name
        by_name = {}
        for metric in self.metrics:
            name = metric["name"]
            if name not in by_name:
                by_name[name] = []
            by_name[name].append(metric["value"])
            
        # Calculate summaries
        summary = {}
        for name, values in by_name.items():
            summary[name] = {
                "latest": values[-1],
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "count": len(values)
            }
            
        return summary

