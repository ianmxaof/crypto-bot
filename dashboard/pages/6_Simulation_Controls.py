"""Simulation Controls dashboard page."""

import streamlit as st
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="Simulation Controls",
    page_icon="🎮",
    layout="wide"
)

# Initialize data service
@st.cache_resource
def get_data_service():
    """Get cached data service instance."""
    return DashboardDataService()

data_service = get_data_service()

st.title("🎮 Simulation Controls")

st.info("💡 Simulation controls will be available when integrated with the main bot process")

# Simulation status
st.subheader("Simulation Status")
col1, col2 = st.columns(2)

with col1:
    mode = "🟢 Paper Trading" if settings.PAPER_TRADING else "🔴 Live Trading"
    st.write(f"**Current Mode:** {mode}")
    st.write(f"**Starting Balance:** ${settings.SIMULATION_STARTING_BALANCE:,.2f}")
    st.write(f"**Fee Rate:** {settings.SIMULATION_FEES * 100:.3f}%")

with col2:
    st.write(f"**Memory Directory:** {settings.MEMORY_DIR}")
    st.write(f"**Log Level:** {settings.LOG_LEVEL}")

# Data export
st.subheader("Data Export")
pnl_df = data_service.get_pnl_data(limit=10000)

if not pnl_df.empty:
    csv = pnl_df.to_csv(index=False)
    st.download_button(
        label="📥 Download PnL Data (CSV)",
        data=csv,
        file_name=f"pnl_data_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# Clear data
st.subheader("Data Management")
if st.button("🗑️ Clear Cache", help="Clear dashboard cache (does not delete stored data)"):
    data_service.clear_cache()
    st.success("Cache cleared!")
    st.rerun()

