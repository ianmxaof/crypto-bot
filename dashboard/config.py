"""Dashboard configuration and styling."""

from typing import Dict, Any

# Chart colors
COLORS = {
    "profit": "#00ff00",
    "loss": "#ff0000",
    "neutral": "#888888",
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "tertiary": "#2ca02c",
}

# Agent colors for charts
AGENT_COLORS = {
    "funding_rate_farmer_v1": "#1f77b4",
    "mev_watcher": "#ff7f0e",
    "hyperliquid_lp": "#2ca02c",
    "swarm_council_v3": "#d62728",
    "default": "#888888",
}

# Update intervals (seconds)
UPDATE_INTERVALS = {
    "fast": 1,
    "normal": 5,
    "slow": 10,
    "manual": 0,
}

# Data limits
MAX_DATA_POINTS = 1000  # Maximum points to display in charts
MAX_RECENT_TRADES = 100  # Maximum recent trades to show

# Chart settings
CHART_HEIGHT = 400
CHART_THEME = "plotly_white"

# Dashboard settings
DEFAULT_UPDATE_INTERVAL = UPDATE_INTERVALS["normal"]
AUTO_REFRESH = True

