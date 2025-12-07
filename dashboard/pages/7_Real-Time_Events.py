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

# Get event statistics with fallback
try:
    event_stats = data_service.get_event_statistics()
except AttributeError:
    # Fallback if method doesn't exist (Streamlit cache issue)
    event_stats = {
        "queue_size": 0,
        "dropped_events": 0,
        "max_queue_size": 10000,
        "events_by_topic": {},
        "total_events": 0
    }
    st.warning("⚠️ Event statistics unavailable. Please restart Streamlit to clear cache.")

# Event statistics
st.subheader("Event Statistics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Events", event_stats.get("total_events", 0))
with col2:
    st.metric("Queue Size", event_stats.get("queue_size", 0))
with col3:
    dropped = event_stats.get("dropped_events", 0)
    st.metric("Dropped Events", dropped, delta=None, delta_color="inverse" if dropped > 0 else "normal")
with col4:
    st.metric("Max Queue Size", event_stats.get("max_queue_size", 10000))

# Events by topic
st.subheader("Events by Topic")
topic_counts = event_stats.get("events_by_topic", {})
if topic_counts:
    import pandas as pd
    topic_df = pd.DataFrame([
        {"Topic": topic, "Count": count}
        for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
    ])
    st.dataframe(topic_df, use_container_width=True, hide_index=True)
else:
    st.info("No events recorded yet. Start a simulation to see events.")

st.divider()

# Recent events
st.subheader("Recent Events")

# Filter options
col1, col2 = st.columns(2)
with col1:
    event_limit = st.slider("Number of Events", 10, 500, 100, 10)
with col2:
    topic_filter = st.selectbox(
        "Filter by Topic",
        ["All"] + list(topic_counts.keys()),
        help="Filter events by topic"
    )

# Get recent events with fallback
selected_topic = None if topic_filter == "All" else topic_filter
try:
    events = data_service.get_recent_events(limit=event_limit, topic=selected_topic)
except AttributeError:
    # Fallback if method doesn't exist (Streamlit cache issue)
    events = []
    if not st.session_state.get('_event_warning_shown', False):
        st.warning("⚠️ Event retrieval unavailable. Please restart Streamlit to clear cache.")
        st.session_state['_event_warning_shown'] = True

if events:
    import pandas as pd
    # Convert events to DataFrame
    events_df = pd.DataFrame(events)
    # Format timestamp for display
    if "timestamp" in events_df.columns:
        events_df["time"] = pd.to_datetime(events_df["timestamp"]).dt.strftime("%H:%M:%S")
        events_df = events_df[["time", "topic", "source", "data"]]
        events_df.columns = ["Time", "Topic", "Source", "Data"]
    
    st.dataframe(events_df, use_container_width=True, hide_index=True)
else:
    st.info("No events available. Events will appear here as the simulation runs.")

# System health
st.divider()
st.subheader("System Health")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Data Points", len(data_service.get_pnl_data(limit=100)))

with col2:
    st.metric("Cache Status", "✅ Active")

with col3:
    last_update = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.metric("Last Update", last_update)

