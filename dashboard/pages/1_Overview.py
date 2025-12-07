"""Overview dashboard page."""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from dashboard.components import (
    plot_pnl_curve, plot_balance_history, metric_card
)
from dashboard.config import MAX_DATA_POINTS
from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="Overview",
    page_icon="📊",
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

st.title("📊 Overview Dashboard")

# Get summary data
summary = data_service.get_pnl_summary()
pnl_df = data_service.get_pnl_data(limit=data_limit)
balance_df = data_service.get_balance_history(limit=data_limit)

# Key metrics row
col1, col2, col3, col4 = st.columns(4)

with col1:
    current_balance = summary.get('current_balance', settings.SIMULATION_STARTING_BALANCE)
    metric_card("Current Balance", f"${current_balance:,.2f}")

with col2:
    total_pnl = summary.get('total_pnl', 0.0)
    pnl_color = "normal" if total_pnl >= 0 else "inverse"
    metric_card("Total P&L", f"${total_pnl:,.2f}", help_text="Cumulative profit/loss")

with col3:
    win_rate = summary.get('win_rate', 0.0) * 100
    metric_card("Win Rate", f"{win_rate:.1f}%", help_text="Percentage of profitable trades")

with col4:
    sharpe = summary.get('sharpe_ratio', 0.0)
    metric_card("Sharpe Ratio", f"{sharpe:.2f}", help_text="Risk-adjusted return metric")

st.divider()

# System status
st.subheader("System Status")
status_col1, status_col2, status_col3 = st.columns(3)

with status_col1:
    mode = "🟢 Paper Trading" if settings.PAPER_TRADING else "🔴 Live Trading"
    st.write(f"**Mode:** {mode}")

with status_col2:
    total_trades = summary.get('total_trades', 0)
    st.write(f"**Total Trades:** {total_trades}")

with status_col3:
    max_dd = summary.get('max_drawdown_pct', 0.0)
    st.write(f"**Max Drawdown:** {max_dd:.2f}%")

st.divider()

# Charts
col1, col2 = st.columns(2)

with col1:
    plot_pnl_curve(pnl_df, "Cumulative P&L Over Time")

with col2:
    plot_balance_history(balance_df, "Portfolio Balance")

# Additional metrics
st.subheader("Performance Metrics")
metrics_col1, metrics_col2 = st.columns(2)

with metrics_col1:
    st.write(f"**Average Win:** ${summary.get('avg_win', 0.0):,.2f}")
    st.write(f"**Average Loss:** ${summary.get('avg_loss', 0.0):,.2f}")
    st.write(f"**Max Win:** ${summary.get('max_win', 0.0):,.2f}")
    st.write(f"**Max Loss:** ${summary.get('max_loss', 0.0):,.2f}")

with metrics_col2:
    st.write(f"**Starting Capital:** ${settings.SIMULATION_STARTING_BALANCE:,.2f}")
    if current_balance > 0:
        return_pct = ((current_balance - settings.SIMULATION_STARTING_BALANCE) / settings.SIMULATION_STARTING_BALANCE) * 100
        st.write(f"**Return:** {return_pct:.2f}%")
    st.write(f"**Realized P&L:** ${total_pnl:,.2f}")

