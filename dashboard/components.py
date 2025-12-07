"""Reusable dashboard components."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, Optional

from dashboard.config import COLORS, AGENT_COLORS, CHART_HEIGHT, CHART_THEME


def metric_card(label: str, value: Any, delta: Optional[str] = None, help_text: Optional[str] = None):
    """Display a metric card.
    
    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta/change indicator
        help_text: Optional help text
    """
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric(label, value, delta=delta, help=help_text)


def plot_pnl_curve(df: pd.DataFrame, title: str = "Cumulative P&L Over Time"):
    """Plot PnL curve.
    
    Args:
        df: DataFrame with timestamp and cumulative_pnl columns
        title: Chart title
    """
    if df.empty or 'cumulative_pnl' not in df.columns:
        st.warning("No PnL data available")
        return
    
    fig = px.line(
        df,
        x='timestamp',
        y='cumulative_pnl',
        title=title,
        labels={'cumulative_pnl': 'Cumulative P&L (USDT)', 'timestamp': 'Time'},
        height=CHART_HEIGHT,
        template=CHART_THEME,
    )
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    # Color based on profit/loss
    fig.update_traces(
        line=dict(color=COLORS["profit"] if df['cumulative_pnl'].iloc[-1] >= 0 else COLORS["loss"])
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_balance_history(df: pd.DataFrame, title: str = "Portfolio Balance"):
    """Plot balance history.
    
    Args:
        df: DataFrame with timestamp and balance columns
        title: Chart title
    """
    if df.empty or 'balance' not in df.columns:
        st.warning("No balance data available")
        return
    
    fig = px.area(
        df,
        x='timestamp',
        y='balance',
        title=title,
        labels={'balance': 'Balance (USDT)', 'timestamp': 'Time'},
        height=CHART_HEIGHT,
        template=CHART_THEME,
    )
    
    fig.update_traces(fill='tozeroy', fillcolor='rgba(31, 119, 180, 0.3)')
    
    st.plotly_chart(fig, use_container_width=True)


def plot_agent_performance(df: pd.DataFrame, title: str = "Agent Performance"):
    """Plot agent performance breakdown.
    
    Args:
        df: DataFrame with agent performance data
        title: Chart title
    """
    if df.empty:
        st.warning("No agent performance data available")
        return
    
    # Pie chart for PnL contribution
    fig = px.pie(
        df,
        values='total_pnl',
        names='agent',
        title=title,
        height=CHART_HEIGHT,
        template=CHART_THEME,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_drawdown(df: pd.DataFrame, title: str = "Drawdown Over Time"):
    """Plot drawdown chart.
    
    Args:
        df: DataFrame with timestamp and balance columns
        title: Chart title
    """
    if df.empty or 'balance' not in df.columns:
        st.warning("No balance data available for drawdown calculation")
        return
    
    # Calculate drawdown
    peak = df['balance'].expanding().max()
    drawdown = (df['balance'] - peak) / peak * 100
    
    drawdown_df = pd.DataFrame({
        'timestamp': df['timestamp'],
        'drawdown_pct': drawdown
    })
    
    fig = px.area(
        drawdown_df,
        x='timestamp',
        y='drawdown_pct',
        title=title,
        labels={'drawdown_pct': 'Drawdown (%)', 'timestamp': 'Time'},
        height=CHART_HEIGHT,
        template=CHART_THEME,
    )
    
    fig.update_traces(fill='tozeroy', fillcolor='rgba(255, 0, 0, 0.3)')
    fig.update_layout(yaxis=dict(range=[min(0, drawdown.min() * 1.1), 1]))
    
    st.plotly_chart(fig, use_container_width=True)


def plot_order_flow_heatmap(df: pd.DataFrame, title: str = "Order Activity Heatmap"):
    """Plot order flow heatmap.
    
    Args:
        df: DataFrame with timestamp, symbol, and amount columns
        title: Chart title
    """
    if df.empty or 'symbol' not in df.columns:
        st.warning("No order flow data available")
        return
    
    # Prepare data for heatmap
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    
    # Aggregate by date, hour, and symbol
    heatmap_data = df.groupby(['date', 'hour', 'symbol'])['amount'].sum().reset_index()
    
    if heatmap_data.empty:
        st.warning("No aggregated order data available")
        return
    
    # Create pivot table
    pivot = heatmap_data.pivot_table(
        index='symbol',
        columns=['date', 'hour'],
        values='amount',
        aggfunc='sum',
        fill_value=0
    )
    
    fig = px.imshow(
        pivot,
        title=title,
        labels=dict(x="Time", y="Symbol", color="Order Amount"),
        height=CHART_HEIGHT,
        template=CHART_THEME,
        aspect="auto",
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_agent_timeline(df: pd.DataFrame, title: str = "Agent Activity Timeline"):
    """Plot agent activity timeline.
    
    Args:
        df: DataFrame with timestamp, agent, and pnl columns
        title: Chart title
    """
    if df.empty or 'agent' not in df.columns:
        st.warning("No agent activity data available")
        return
    
    # Create scatter plot
    fig = px.scatter(
        df,
        x='timestamp',
        y='agent',
        size=abs(df['pnl']),
        color='pnl',
        title=title,
        labels={'pnl': 'P&L (USDT)', 'timestamp': 'Time'},
        height=CHART_HEIGHT,
        template=CHART_THEME,
        color_continuous_scale=['red', 'gray', 'green'],
    )
    
    st.plotly_chart(fig, use_container_width=True)


def display_metrics_table(metrics: Dict[str, Any], title: str = "Metrics"):
    """Display metrics in a table.
    
    Args:
        metrics: Dictionary of metric name -> value
        title: Table title
    """
    if not metrics:
        st.warning("No metrics available")
        return
    
    df = pd.DataFrame([
        {'Metric': k, 'Value': v}
        for k, v in metrics.items()
    ])
    
    st.dataframe(df, use_container_width=True, hide_index=True)


def display_trades_table(df: pd.DataFrame, limit: int = 50):
    """Display recent trades table.
    
    Args:
        df: DataFrame with trade data
        limit: Maximum number of trades to display
    """
    if df.empty:
        st.warning("No trades available")
        return
    
    # Format columns
    display_df = df.head(limit).copy()
    
    # Format timestamp
    if 'timestamp' in display_df.columns:
        try:
            display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            pass  # Keep original if formatting fails
    
    # Format PnL with color
    if 'pnl' in display_df.columns:
        def format_pnl(pnl):
            try:
                pnl_val = float(pnl)
                color = "🟢" if pnl_val >= 0 else "🔴"
                return f"{color} ${pnl_val:,.2f}"
            except:
                return str(pnl)
        display_df['PnL'] = display_df['pnl'].apply(format_pnl)
    
    # Select and rename columns for display
    columns_to_show = ['timestamp', 'symbol', 'agent', 'PnL', 'side', 'size', 'price']
    available_columns = [c for c in columns_to_show if c in display_df.columns]
    
    if available_columns:
        st.dataframe(display_df[available_columns], use_container_width=True, hide_index=True)
    else:
        st.dataframe(display_df, use_container_width=True, hide_index=True)

