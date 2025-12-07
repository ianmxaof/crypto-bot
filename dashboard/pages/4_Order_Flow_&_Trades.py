"""Order Flow & Trades dashboard page."""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from dashboard.components import (
    plot_order_flow_heatmap, display_trades_table
)
from dashboard.config import MAX_DATA_POINTS

# Page configuration
st.set_page_config(
    page_title="Order Flow & Trades",
    page_icon="📈",
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

st.title("📈 Order Flow & Trades")

order_flow_df = data_service.get_order_flow_data(limit=data_limit)
recent_trades_df = data_service.get_recent_trades(limit=100)

# Order flow heatmap
if not order_flow_df.empty:
    st.subheader("Order Activity Heatmap")
    plot_order_flow_heatmap(order_flow_df, "Order Activity by Symbol and Time")

# Recent trades
st.subheader("Recent Trades")
display_trades_table(recent_trades_df, limit=50)

# Trade statistics
if not recent_trades_df.empty:
    st.subheader("Trade Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_trades = len(recent_trades_df)
        st.metric("Total Trades", total_trades)
    
    with col2:
        if 'pnl' in recent_trades_df.columns:
            profitable = (recent_trades_df['pnl'] > 0).sum()
            st.metric("Profitable Trades", profitable)
    
    with col3:
        if 'symbol' in recent_trades_df.columns:
            unique_symbols = recent_trades_df['symbol'].nunique()
            st.metric("Symbols Traded", unique_symbols)
    
    with col4:
        if 'agent' in recent_trades_df.columns:
            unique_agents = recent_trades_df['agent'].nunique()
            st.metric("Active Agents", unique_agents)

