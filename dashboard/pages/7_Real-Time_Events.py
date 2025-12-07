"""Real-Time Events dashboard page."""

import streamlit as st
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService

# Page configuration
st.set_page_config(
    page_title="Real-Time Events",
    page_icon="📡",
    layout="wide"
)

# Initialize data service
@st.cache_resource
def get_data_service():
    """Get cached data service instance."""
    return DashboardDataService()

data_service = get_data_service()

st.title("📡 Real-Time Events")

st.info("💡 Event log integration will show live events from the event bus")

# Event statistics
st.subheader("Event Statistics")
st.write("Event bus monitoring would be displayed here")

# System health
st.subheader("System Health")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Data Points", len(data_service.get_pnl_data(limit=100)))

with col2:
    st.metric("Cache Status", "✅ Active")

with col3:
    last_update = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.metric("Last Update", last_update)

