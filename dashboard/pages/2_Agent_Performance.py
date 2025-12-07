"""Agent Performance dashboard page."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from dashboard.components import (
    plot_agent_performance, plot_agent_timeline, display_trades_table
)
from dashboard.config import MAX_DATA_POINTS

# Page configuration
st.set_page_config(
    page_title="Agent Performance",
    page_icon="🤖",
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

st.title("🤖 Agent Performance")

agent_perf_df = data_service.get_agent_performance()
pnl_df = data_service.get_pnl_data(limit=data_limit)

# Agent Roster
st.subheader("📋 Agent Roster")
try:
    # Get agents from simulation state or memory
    from config.simulation_state import read_simulation_state
    sim_state = read_simulation_state()
    
    # Default agent list (can be enhanced to read from actual overseer)
    default_agents = ['Funding Rate', 'MEV Hunter', 'Hyperliquid LP']
    
    # Create agent roster table
    if not agent_perf_df.empty:
        # Use actual agent data
        roster_data = []
        for _, row in agent_perf_df.iterrows():
            agent_name = row['agent']
            status = "Active" if sim_state.get('running', False) else "Idle"
            pnl = row['total_pnl']
            trades = int(row['trade_count'])
            roster_data.append({
                "Agent": agent_name,
                "Status": status,
                "PnL": f"${pnl:,.2f}",
                "Trades": trades
            })
        roster_df = pd.DataFrame(roster_data)
    else:
        # Use default agents with placeholder data
        roster_data = []
        for agent in default_agents:
            status = "Active" if sim_state.get('running', False) else "Idle"
            roster_data.append({
                "Agent": agent,
                "Status": status,
                "PnL": "$0.00",
                "Trades": 0
            })
        roster_df = pd.DataFrame(roster_data)
    
    st.dataframe(roster_df, use_container_width=True, hide_index=True)
    
    # Marketplace stub (future enhancement)
    with st.expander("🔮 Agent Marketplace (Coming Soon)", expanded=False):
        st.info("Upload and share custom agents. Leaderboard sorting by sim PnL coming soon!")
        st.button("Upload Agent", disabled=True, help="Feature coming soon")
        
except Exception as e:
    st.warning(f"Could not load agent roster: {e}")

st.divider()

if not agent_perf_df.empty:
    # Agent performance breakdown
    col1, col2 = st.columns([1, 1])
    
    with col1:
        plot_agent_performance(agent_perf_df, "PnL Contribution by Agent")
    
    with col2:
        st.subheader("Agent Performance Table")
        st.dataframe(agent_perf_df, use_container_width=True, hide_index=True)
    
    # Agent activity timeline
    if not pnl_df.empty and 'agent' in pnl_df.columns:
        plot_agent_timeline(pnl_df, "Agent Activity Timeline")
    
    # Individual agent details
    st.subheader("Agent Details")
    selected_agent = st.selectbox("Select Agent", agent_perf_df['agent'].tolist())
    
    if selected_agent:
        agent_data = agent_perf_df[agent_perf_df['agent'] == selected_agent].iloc[0]
        agent_trades = pnl_df[pnl_df['agent'] == selected_agent] if not pnl_df.empty else pd.DataFrame()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total P&L", f"${agent_data['total_pnl']:,.2f}")
        with col2:
            st.metric("Trade Count", int(agent_data['trade_count']))
        with col3:
            st.metric("Win Rate", f"{agent_data['win_rate']*100:.1f}%")
        with col4:
            st.metric("Avg P&L", f"${agent_data['avg_pnl']:,.2f}")
        
        if not agent_trades.empty:
            st.subheader(f"{selected_agent} Trade History")
            display_trades_table(agent_trades, limit=20)
else:
    st.warning("No agent performance data available. Run some simulations first.")

