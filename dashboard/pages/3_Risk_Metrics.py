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
from config.runtime_risks import (
    read_runtime_risks,
    update_runtime_risks,
    get_max_position_size,
    get_max_daily_loss_percent,
    get_max_drawdown_percent
)

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

# Editable Risk Controls
st.subheader("⚙️ Edit Risk Limits")
st.info("💡 Update risk limits in real-time. Changes take effect on the next simulation cycle.")

runtime_risks = read_runtime_risks()

col1, col2, col3 = st.columns(3)

with col1:
    max_pos = st.number_input(
        "Max Position Size ($)",
        value=int(runtime_risks.get('max_position_size_usd', 5000)),
        min_value=100,
        max_value=100000,
        step=100,
        help="Maximum position size per trade in USD"
    )

with col2:
    max_loss_pct = st.number_input(
        "Max Daily Loss (%)",
        value=float(runtime_risks.get('max_daily_loss_percent', 5.0)),
        min_value=0.1,
        max_value=50.0,
        step=0.5,
        format="%.1f",
        help="Maximum daily loss percentage before circuit breaker"
    )

with col3:
    max_dd_pct = st.number_input(
        "Max Drawdown (%)",
        value=float(runtime_risks.get('max_drawdown_percent', 15.0)),
        min_value=1.0,
        max_value=50.0,
        step=0.5,
        format="%.1f",
        help="Maximum drawdown percentage before trading halt"
    )

if st.button("Update Risks", type="primary", use_container_width=True):
    success = update_runtime_risks(
        max_position_size_usd=float(max_pos),
        max_daily_loss_percent=float(max_loss_pct),
        max_drawdown_percent=float(max_dd_pct)
    )
    if success:
        st.success("✅ Risks updated — next sim cycle applies")
        st.rerun()
    else:
        st.error("❌ Failed to update risks. Check logs for details.")

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

