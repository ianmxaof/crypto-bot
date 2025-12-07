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
    
    # Agent Marketplace
    st.subheader("🏪 Agent Marketplace")
    
    tab1, tab2 = st.tabs(["📊 Leaderboard", "⬆️ Upload Agent"])
    
    with tab1:
        try:
            from agents.marketplace import get_marketplace
            
            marketplace = get_marketplace()
            
            # Sort options
            col1, col2 = st.columns([3, 1])
            with col1:
                sort_by = st.selectbox(
                    "Sort By",
                    options=["sharpe", "apr", "downloads", "upload_date"],
                    format_func=lambda x: {
                        "sharpe": "Sharpe Ratio",
                        "apr": "APR (%)",
                        "downloads": "Downloads",
                        "upload_date": "Upload Date"
                    }[x],
                    key="marketplace_sort"
                )
            with col2:
                status_filter = st.selectbox(
                    "Status",
                    options=[None, "pending", "tested", "approved", "rejected"],
                    format_func=lambda x: "All" if x is None else x.title(),
                    key="marketplace_status"
                )
            
            # Get agents
            agents = marketplace.list_agents(sort_by=sort_by, status_filter=status_filter)
            
            if agents:
                # Display leaderboard
                leaderboard_data = []
                for agent in agents:
                    leaderboard_data.append({
                        "Rank": len(leaderboard_data) + 1,
                        "Name": agent.name,
                        "Author": agent.author,
                        "Sharpe": f"{agent.sharpe:.2f}",
                        "APR": f"{agent.apr:.1f}%",
                        "Max DD": f"{agent.max_drawdown*100:.1f}%",
                        "Downloads": agent.downloads,
                        "Status": agent.status,
                        "Upload Date": agent.upload_date[:10] if len(agent.upload_date) > 10 else agent.upload_date
                    })
                
                leaderboard_df = pd.DataFrame(leaderboard_data)
                st.dataframe(leaderboard_df, use_container_width=True, hide_index=True)
                
                # Download buttons
                st.subheader("Download Agent")
                selected_agent_name = st.selectbox(
                    "Select Agent to Download",
                    options=[a.name for a in agents],
                    key="download_agent_select"
                )
                
                if st.button("📥 Download Agent Code", key="download_agent_btn"):
                    selected_agent = next(a for a in agents if a.name == selected_agent_name)
                    agent_code = marketplace.get_agent_code(selected_agent.id)
                    if agent_code:
                        marketplace.increment_downloads(selected_agent.id)
                        st.download_button(
                            label="Download Code",
                            data=agent_code,
                            file_name=f"{selected_agent.name.replace(' ', '_')}.py",
                            mime="text/x-python"
                        )
                        st.success(f"Downloaded {selected_agent.name}")
            else:
                st.info("No agents in marketplace yet. Upload one to get started!")
                
        except Exception as e:
            st.warning(f"Marketplace unavailable: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    with tab2:
        try:
            from agents.marketplace import get_marketplace
            import asyncio
            
            marketplace = get_marketplace()
            
            st.markdown("### Upload a New Agent")
            st.info("Upload your custom trading agent code. It will be validated and tested in simulation.")
            
            with st.form("upload_agent_form"):
                agent_name = st.text_input("Agent Name", placeholder="e.g., Momentum Bot")
                agent_author = st.text_input("Author Name", placeholder="Your name or username")
                agent_description = st.text_area(
                    "Description",
                    placeholder="Describe what this agent does...",
                    height=100
                )
                agent_code = st.text_area(
                    "Agent Code (Python)",
                    placeholder="# Your agent code here\nfrom core.agent_base import Agent, AgentConfig\n...",
                    height=300
                )
                
                submitted = st.form_submit_button("Upload Agent", type="primary")
                
                if submitted:
                    if not all([agent_name, agent_author, agent_description, agent_code]):
                        st.error("Please fill in all fields")
                    else:
                        try:
                            agent_id = marketplace.add_agent(
                                name=agent_name,
                                author=agent_author,
                                description=agent_description,
                                code=agent_code
                            )
                            st.success(f"Agent '{agent_name}' uploaded successfully! (ID: {agent_id})")
                            
                            # Offer to test immediately
                            if st.button("🧪 Test Agent in Simulation", key="test_uploaded_agent"):
                                with st.spinner("Testing agent in 7-day simulation..."):
                                    try:
                                        from decimal import Decimal
                                        results = asyncio.run(
                                            marketplace.test_agent_in_simulation(
                                                agent_id,
                                                initial_capital=Decimal('10000'),
                                                simulation_days=7
                                            )
                                        )
                                        st.success("Agent tested successfully!")
                                        st.json(results)
                                    except Exception as e:
                                        st.error(f"Testing failed: {e}")
                        except ValueError as e:
                            st.error(f"Validation failed: {e}")
                        except Exception as e:
                            st.error(f"Upload failed: {e}")
                            import traceback
                            st.code(traceback.format_exc())
            
            # Show code template
            with st.expander("📝 Agent Code Template", expanded=False):
                st.code("""
from core.agent_base import Agent, AgentConfig
from decimal import Decimal
from typing import Dict, Optional

class MyCustomAgent(Agent):
    def __init__(self):
        super().__init__(AgentConfig(
            name="my_custom_agent",
            version="1.0.0",
            description="My custom trading agent"
        ))
    
    async def run(self):
        # Your agent logic here
        while not self._shutdown_event.is_set():
            # Trading logic
            await asyncio.sleep(60)
                """, language="python")
                
        except Exception as e:
            st.warning(f"Marketplace unavailable: {e}")
            import traceback
            st.code(traceback.format_exc())
        
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

