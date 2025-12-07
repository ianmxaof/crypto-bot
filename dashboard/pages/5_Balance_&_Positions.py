"""Balance & Positions dashboard page."""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from dashboard.components import (
    plot_balance_history
)
from dashboard.config import MAX_DATA_POINTS
from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="Balance & Positions",
    page_icon="💰",
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

st.title("💰 Balance & Positions")

balance_df = data_service.get_balance_history(limit=data_limit)
summary = data_service.get_pnl_summary()

# Balance overview
st.subheader("Balance Overview")
col1, col2, col3 = st.columns(3)

with col1:
    current_balance = summary.get('current_balance', settings.SIMULATION_STARTING_BALANCE)
    st.metric("Current Balance", f"${current_balance:,.2f}")

with col2:
    starting_balance = float(settings.SIMULATION_STARTING_BALANCE)
    change = current_balance - starting_balance
    change_pct = (change / starting_balance * 100) if starting_balance > 0 else 0
    st.metric("Change from Start", f"${change:,.2f}", delta=f"{change_pct:.2f}%")

with col3:
    total_pnl = summary.get('total_pnl', 0.0)
    st.metric("Realized P&L", f"${total_pnl:,.2f}")

# Balance chart
if not balance_df.empty:
    plot_balance_history(balance_df, "Balance History")

# Balance breakdown (simplified - would need position data)
st.subheader("Balance Breakdown")
st.info("💡 Position details would be shown here when positions are tracked in memory")

