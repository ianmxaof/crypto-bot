"""Risk Metrics dashboard page."""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from dashboard.components import (
    plot_drawdown, display_metrics_table
)
from dashboard.config import MAX_DATA_POINTS

# Page configuration
st.set_page_config(
    page_title="Risk Metrics",
    page_icon="⚠️",
    layout="wide"
)

# Initialize data service
@st.cache_resource
def get_data_service():
    """Get cached data service instance."""
    return DashboardDataService()

data_service = get_data_service()

# Get data limit from session state (set by Home.py sidebar)
data_limit = st.session_state.get('data_limit', MAX_DATA_POINTS)

st.title("⚠️ Risk Metrics")

risk_metrics = data_service.get_risk_metrics()
balance_df = data_service.get_balance_history(limit=data_limit)

# Risk limits
st.subheader("Risk Limits")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Max Position Size", f"${risk_metrics['max_position_size_usd']:,.2f}")
with col2:
    st.metric("Max Daily Loss %", f"{risk_metrics['max_daily_loss_percent']:.1f}%")
with col3:
    st.metric("Max Daily Loss USD", f"${risk_metrics['max_daily_loss_usd']:,.2f}")

st.divider()

# Current risk status
st.subheader("Current Risk Status")
col1, col2, col3 = st.columns(3)

with col1:
    current_dd = risk_metrics.get('current_drawdown_pct', 0.0)
    dd_color = "normal" if abs(current_dd) < 5 else "inverse"
    st.metric("Current Drawdown", f"{current_dd:.2f}%", delta=None)
with col2:
    max_dd = risk_metrics.get('max_drawdown_pct', 0.0)
    st.metric("Max Drawdown", f"{max_dd:.2f}%")
with col3:
    daily_pnl = risk_metrics.get('daily_pnl', 0.0)
    st.metric("Daily P&L", f"${daily_pnl:,.2f}")

# Drawdown chart
if not balance_df.empty:
    plot_drawdown(balance_df, "Drawdown Over Time")

# Risk metrics table
st.subheader("All Risk Metrics")
display_metrics_table(risk_metrics, "Risk Metrics")

