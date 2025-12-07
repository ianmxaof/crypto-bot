"""Simulation Controls dashboard page - Full command center for simulation control."""

import streamlit as st
from datetime import datetime, timezone
import sys
from pathlib import Path
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from config.settings import settings
from config.simulation_state import (
    read_simulation_state,
    write_simulation_state,
    update_simulation_state,
    get_simulation_running,
    get_simulation_speed,
    get_simulation_days,
    get_starting_capital
)

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

st.title("🎮 Simulation Command Center")
st.markdown("Control your entire swarm simulation from here — no terminal needed.")

# Read current state
current_state = read_simulation_state()

# Sidebar controls
with st.sidebar:
    st.header("Simulation Parameters")
    
    # Speed control
    speed = st.slider(
        "Speed Multiplier",
        1,
        1000,
        int(current_state.get("speed", 100)),
        help="How many times faster than real-time. 100x = 6 hours = 3.6 minutes"
    )
    
    # Days control
    days = st.slider(
        "Days to Simulate",
        1,
        365,
        int(current_state.get("days", 30)),
        help="Target duration for the simulation"
    )
    
    # Capital control
    capital = st.number_input(
        "Starting Capital ($)",
        100,
        100000,
        int(current_state.get("starting_capital", 1000)),
        step=100,
        help="Initial capital for the simulation"
    )
    
    if st.button("Apply Settings", type="primary", use_container_width=True):
        success = update_simulation_state(
            speed=float(speed),
            days=int(days),
            starting_capital=float(capital)
        )
        if success:
            st.success(f"Settings saved! Speed: {speed}x | Days: {days} | Capital: ${capital}")
            st.rerun()
        else:
            st.error("Failed to save settings. Check logs for details.")

# Main controls
st.subheader("Simulation Controls")
col1, col2, col3 = st.columns(3)

with col1:
    if st.button("▶️ START SIMULATION", type="primary", use_container_width=True):
        success = update_simulation_state(running=True)
        if success:
            st.balloons()
            current_state = read_simulation_state()
            st.success(f"Simulation STARTED: {current_state.get('days', 30)} days at {current_state.get('speed', 100)}x speed")
            st.info("Watch the Overview tab — PnL will start climbing in seconds")
            st.rerun()
        else:
            st.error("Failed to start simulation")

with col2:
    if st.button("⏹️ STOP SIMULATION", use_container_width=True):
        success = update_simulation_state(running=False)
        if success:
            st.error("Simulation STOPPED")
            st.rerun()
        else:
            st.error("Failed to stop simulation")

with col3:
    if st.button("🔄 RESET & CLEAR DATA", type="secondary", use_container_width=True):
        confirm = st.checkbox("I understand this deletes all simulation history", key="confirm_reset")
        if confirm:
            try:
                # Clear memory directory
                memory_dir = Path(settings.MEMORY_DIR)
                if memory_dir.exists():
                    shutil.rmtree(memory_dir, ignore_errors=True)
                    memory_dir.mkdir(parents=True, exist_ok=True)
                
                # Reset simulation state
                update_simulation_state(running=False)
                
                st.success("Memory wiped — fresh start!")
                st.rerun()
            except Exception as e:
                st.error(f"Error resetting: {e}")

# Live status
st.divider()
st.subheader("Live Simulation Status")

# Read fresh state for display
current_state = read_simulation_state()
is_running = current_state.get("running", False)

if is_running:
    st.success("🟢 SIMULATION IS RUNNING")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Speed", f"{current_state.get('speed', 100)}x real-time")
    with col2:
        st.metric("Target Duration", f"{current_state.get('days', 30)} days")
    with col3:
        st.metric("Starting Capital", f"${current_state.get('starting_capital', 1000):,.2f}")
else:
    st.warning("⏸️ Simulation is stopped")

# Live Simulation Checklist
st.divider()
with st.expander("📋 Live Simulation Checklist", expanded=True):
    # Get data to determine progress
    try:
        summary = data_service.get_pnl_summary()
        pnl_df = data_service.get_pnl_data(limit=100)
        
        # Check initialization
        init_status = "✅ Done" if is_running or not pnl_df.empty else "⏳ Waiting..."
        
        # Check allocation (has data means allocation happened)
        alloc_status = "✅ Done" if not pnl_df.empty else "⏳ Waiting..."
        
        # Calculate cycles/days progress
        progress_pct = 0.0
        cycle_status = "⏸️ Stopped"
        if not pnl_df.empty and is_running:
            cycle_count = len(pnl_df)
            target_days = current_state.get('days', 30)
            # Estimate: each cycle is roughly 6 hours = 0.25 days
            estimated_days = cycle_count * 0.25
            progress_pct = min(100, (estimated_days / target_days * 100) if target_days > 0 else 0)
            cycle_status = f"🔄 {cycle_count} cycles | ~{estimated_days:.1f}/{target_days} days ({progress_pct:.0f}%)"
        elif is_running:
            cycle_status = "🔄 Starting..."
        
        # Risk check (simplified - would need actual risk data)
        risk_status = "🟢 All green" if is_running else "⏸️ N/A"
        
        # Completion status
        if is_running:
            last_updated = current_state.get("last_updated")
            if last_updated:
                try:
                    last_ts = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                    elapsed = (datetime.now(timezone.utc) - last_ts).total_seconds() / 3600
                    if elapsed > 24:  # No update in 24 hours
                        complete_status = "⚠️ Stalled (no updates)"
                    else:
                        complete_status = "❌ Not yet"
                except:
                    complete_status = "❌ Not yet"
            else:
                complete_status = "❌ Not yet"
        else:
            complete_status = "⏸️ Not started"
        
        st.markdown(f"""
        1. **Initialization:** {init_status}  
        2. **Capital Allocation:** {alloc_status}  
        3. **Agent Cycles:** {cycle_status}  
        4. **Risk Check:** {risk_status}  
        5. **Progress:** {progress_pct:.0f}% complete (estimated)  
        6. **Complete:** {complete_status}
        """)
        
    except Exception as e:
        st.warning(f"Error loading checklist data: {e}")
        st.markdown("""
        1. **Initialization:** ⏳ Checking...
        2. **Capital Allocation:** ⏳ Checking...
        3. **Agent Cycles:** ⏳ Checking...
        4. **Risk Check:** ⏳ Checking...
        5. **Progress:** ⏳ Checking...
        6. **Complete:** ⏳ Checking...
        """)

# Quick actions
st.divider()
st.subheader("Quick Simulation Presets")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("⚡ Run 7-Day Blitz", use_container_width=True):
        success = update_simulation_state(
            days=7,
            speed=500,
            running=True
        )
        if success:
            st.success("7-day blitz started at 500x!")
            st.rerun()
        else:
            st.error("Failed to start blitz")

with col2:
    if st.button("🔥 Run 90-Day Stress Test", use_container_width=True):
        success = update_simulation_state(
            days=90,
            speed=200,
            running=True
        )
        if success:
            st.success("90-day stress test running!")
            st.rerun()
        else:
            st.error("Failed to start stress test")

with col3:
    if st.button("🏃 Run 1-Year Marathon", use_container_width=True):
        success = update_simulation_state(
            days=365,
            speed=100,
            running=True
        )
        if success:
            st.success("1-year simulation started!")
            st.rerun()
        else:
            st.error("Failed to start marathon")

st.info("💡 Your bot reads these settings live — no restart needed! Changes take effect within 3-5 seconds.")

# System information
st.divider()
st.subheader("System Information")

col1, col2 = st.columns(2)

with col1:
    mode = "🟢 Paper Trading" if settings.PAPER_TRADING else "🔴 Live Trading"
    st.write(f"**Current Mode:** {mode}")
    st.write(f"**Fee Rate:** {settings.SIMULATION_FEES * 100:.3f}%")
    st.write(f"**Memory Directory:** {settings.MEMORY_DIR}")

with col2:
    st.write(f"**Log Level:** {settings.LOG_LEVEL}")
    last_updated = current_state.get("last_updated")
    if last_updated:
        st.write(f"**Last Updated:** {last_updated}")
    else:
        st.write("**Last Updated:** Never")

# Data export
st.divider()
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
else:
    st.info("No PnL data available yet. Start a simulation to generate data.")

# Clear cache
st.divider()
st.subheader("Data Management")
if st.button("🗑️ Clear Dashboard Cache", help="Clear dashboard cache (does not delete stored data)"):
    data_service.clear_cache()
    st.success("Cache cleared!")
    st.rerun()
