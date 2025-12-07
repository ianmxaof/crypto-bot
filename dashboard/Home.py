"""Streamlit dashboard home page with sidebar controls for crypto trading bot real-time monitoring."""

import streamlit as st
import sys
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.data_service import DashboardDataService
from dashboard.config import UPDATE_INTERVALS, DEFAULT_UPDATE_INTERVAL, MAX_DATA_POINTS
from config.settings import settings
from config.simulation_state import read_simulation_state
from datetime import datetime, timezone

# Page configuration
st.set_page_config(
    page_title="Crypto Swarm Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize data service
@st.cache_resource
def get_data_service():
    """Get cached data service instance."""
    return DashboardDataService()

data_service = get_data_service()

# Sidebar controls
st.sidebar.title("🎛️ Dashboard Controls")

# Update interval
update_interval = st.sidebar.selectbox(
    "Update Interval",
    options=list(UPDATE_INTERVALS.keys()),
    index=1,  # Default to "normal"
    format_func=lambda x: f"{x.title()} ({UPDATE_INTERVALS[x]}s)" if UPDATE_INTERVALS[x] > 0 else "Manual"
)

# Auto-refresh toggle
auto_refresh = st.sidebar.checkbox("Auto Refresh", value=True)

# Manual refresh button
if st.sidebar.button("🔄 Refresh Now"):
    data_service.clear_cache()
    st.rerun()

# Data limit
data_limit = st.sidebar.slider(
    "Data Points",
    min_value=100,
    max_value=5000,
    value=MAX_DATA_POINTS,
    step=100
)

# Store data_limit in session state so pages can access it
st.session_state['data_limit'] = data_limit

# Initialize session state for cross-tab data sharing
if 'logs' not in st.session_state:
    st.session_state['logs'] = []
if 'last_update' not in st.session_state:
    st.session_state['last_update'] = None
if 'simulation_state' not in st.session_state:
    st.session_state['simulation_state'] = {}

# Update shared data in session state
try:
    # Update logs from memory
    pnl_data = data_service.get_pnl_data(limit=1000)
    st.session_state['logs'] = pnl_data.to_dict('records') if not pnl_data.empty else []
    
    # Update simulation state
    sim_state = read_simulation_state()
    st.session_state['simulation_state'] = sim_state
    
    # Update last update timestamp
    st.session_state['last_update'] = datetime.now(timezone.utc).isoformat()
except Exception as e:
    # If update fails, keep existing session state
    pass

# Auto-refresh logic
if auto_refresh and UPDATE_INTERVALS[update_interval] > 0:
    time.sleep(UPDATE_INTERVALS[update_interval])
    st.rerun()

# Footer
st.sidebar.divider()
st.sidebar.caption(f"📊 Crypto Swarm Trading Bot Dashboard")
st.sidebar.caption(f"Mode: {'Paper Trading' if settings.PAPER_TRADING else 'Live Trading'}")

# Main content area - welcome message for home page
st.title("📊 Crypto Swarm Trading Bot Dashboard")
st.markdown("Welcome to the dashboard! Use the navigation menu on the left to explore different sections.")
st.info("💡 Select a page from the sidebar navigation to view detailed metrics and charts.")

