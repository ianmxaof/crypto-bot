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
from dashboard.utils import to_float, safe_subtract, safe_calculate_return, safe_format_currency
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

# Get data with error handling
try:
    balance_df = data_service.get_balance_history(limit=data_limit)
except Exception as e:
    import logging
    import pandas as pd
    logging.getLogger(__name__).error(f"Error fetching balance history: {e}", exc_info=True)
    balance_df = pd.DataFrame(columns=['timestamp', 'balance', 'free', 'used'])
    st.error(f"Error loading balance data: {e}")

try:
    summary = data_service.get_pnl_summary()
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"Error fetching PnL summary: {e}", exc_info=True)
    summary = {}
    st.error(f"Error loading summary data: {e}")

# Balance overview
st.subheader("Balance Overview")
col1, col2, col3 = st.columns(3)

with col1:
    current_balance = summary.get('current_balance', settings.SIMULATION_STARTING_BALANCE)
    st.metric("Current Balance", safe_format_currency(current_balance))

with col2:
    try:
        starting_balance = to_float(settings.SIMULATION_STARTING_BALANCE)
        current_balance_float = to_float(current_balance)
        change = safe_subtract(current_balance, settings.SIMULATION_STARTING_BALANCE)
        change_pct = safe_calculate_return(current_balance, settings.SIMULATION_STARTING_BALANCE)
        delta_display = f"{change_pct:.2f}%" if change_pct != 0 else None
        st.metric("Change from Start", safe_format_currency(change), delta=delta_display)
    except Exception as e:
        st.warning(f"Error calculating balance change: {e}")
        st.metric("Change from Start", "$0.00")

with col3:
    total_pnl = summary.get('total_pnl', 0.0)
    st.metric("Realized P&L", f"${total_pnl:,.2f}")

# Balance chart with error handling
try:
    if not balance_df.empty:
        plot_balance_history(balance_df, "Balance History")
except Exception as e:
    import logging
    logging.getLogger(__name__).error(f"Error plotting balance history: {e}", exc_info=True)
    st.error(f"Error displaying balance chart: {e}")

# Balance breakdown (simplified - would need position data)
st.subheader("Balance Breakdown")
st.info("💡 Position details would be shown here when positions are tracked in memory")

