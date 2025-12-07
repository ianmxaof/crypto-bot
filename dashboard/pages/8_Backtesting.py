"""Backtesting page for historical strategy testing."""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_service import DashboardDataService
from backtesting.backtester import Backtester
from strategies.funding_rate import FundingRateStrategy
from config.settings import settings

# Page configuration
st.set_page_config(
    page_title="Backtesting - Crypto Swarm Trading Bot",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Historical Backtesting")

st.markdown("""
Test your strategies against real historical market data. Select a date range and symbol to see how 
your strategy would have performed during past market events.
""")

data_service = DashboardDataService()

# Strategy selection
st.subheader("Strategy Selection")
strategy_options = {
    "Funding Rate Arbitrage": FundingRateStrategy()
}
selected_strategy_name = st.selectbox(
    "Select Strategy",
    options=list(strategy_options.keys()),
    help="Choose which strategy to backtest"
)
selected_strategy = strategy_options[selected_strategy_name]

# Date range selection
st.subheader("Date Range")
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "Start Date",
        value=datetime.now(timezone.utc).date() - timedelta(days=30),
        max_value=datetime.now(timezone.utc).date(),
        help="Backtest start date"
    )

with col2:
    end_date = st.date_input(
        "End Date",
        value=datetime.now(timezone.utc).date(),
        max_value=datetime.now(timezone.utc).date(),
        min_value=start_date,
        help="Backtest end date"
    )

# Symbol selection
st.subheader("Trading Symbol")
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'PEPE/USDT', 'WIF/USDT', 'BONK/USDT']
selected_symbol = st.selectbox(
    "Symbol",
    options=symbols,
    index=0,
    help="Trading pair to backtest"
)

# Capital
initial_capital = st.number_input(
    "Initial Capital ($)",
    value=10000,
    min_value=100,
    step=1000,
    help="Starting capital for backtest"
)

# Real data toggle
use_real_data = st.checkbox(
    "Use Real Historical Data (CoinGecko)",
    value=True,
    help="Fetch real historical prices from CoinGecko API"
)

# Run backtest button
if st.button("🚀 Run Backtest", type="primary", use_container_width=True):
    if start_date >= end_date:
        st.error("Start date must be before end date")
    else:
        with st.spinner("Running backtest... This may take a minute while fetching historical data."):
            try:
                # Convert dates to datetime with timezone
                start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
                end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
                
                # Create backtester
                data_dir = Path("data")
                backtester = Backtester(
                    strategy=selected_strategy,
                    initial_capital=Decimal(str(initial_capital)),
                    data_dir=data_dir,
                    start_date=start_dt,
                    end_date=end_dt,
                    use_real_data=use_real_data,
                    symbol=selected_symbol
                )
                
                # Run backtest
                results = backtester.run()
                
                # Store results in session state
                st.session_state['backtest_results'] = results
                st.session_state['backtest_config'] = {
                    'strategy': selected_strategy_name,
                    'symbol': selected_symbol,
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': initial_capital,
                    'used_real_data': results.get('used_real_data', False)
                }
                
                st.success("Backtest completed successfully!")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error running backtest: {e}")
                st.exception(e)

# Display results if available
if 'backtest_results' in st.session_state:
    results = st.session_state['backtest_results']
    config = st.session_state['backtest_config']
    
    st.divider()
    st.subheader("📈 Backtest Results")
    
    # Display configuration
    with st.expander("Backtest Configuration", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Strategy", config['strategy'])
        with col2:
            st.metric("Symbol", config['symbol'])
        with col3:
            st.metric("Date Range", f"{config['start_date']} to {config['end_date']}")
        with col4:
            st.metric("Initial Capital", f"${config['initial_capital']:,.2f}")
        
        if config.get('used_real_data'):
            st.success("✅ Used real historical data from CoinGecko")
        else:
            st.info("ℹ️ Used synthetic/simulated data")
    
    # Metrics
    metrics = results.get('metrics', {})
    st.subheader("Performance Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        final_value = results.get('equity_curve', [initial_capital])[-1] if results.get('equity_curve') else initial_capital
        total_return = ((final_value - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0
        st.metric("Total Return", f"{total_return:.2f}%", delta=f"${final_value - initial_capital:,.2f}")
    
    with col2:
        sharpe = metrics.get('sharpe_ratio', 0)
        st.metric("Sharpe Ratio", f"{sharpe:.2f}")
    
    with col3:
        max_dd = metrics.get('max_drawdown', 0) * 100
        st.metric("Max Drawdown", f"{max_dd:.2f}%")
    
    with col4:
        win_rate = metrics.get('win_rate', 0) * 100
        st.metric("Win Rate", f"{win_rate:.2f}%")
    
    # Equity curve chart
    st.subheader("Equity Curve")
    equity_curve = results.get('equity_curve', [])
    
    if equity_curve:
        # Create date range for x-axis
        start_dt = datetime.combine(config['start_date'], datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(config['end_date'], datetime.max.time()).replace(tzinfo=timezone.utc)
        num_points = len(equity_curve)
        if num_points > 1:
            date_range = pd.date_range(start=start_dt, end=end_dt, periods=num_points)
        else:
            date_range = [start_dt]
        
        # Create chart
        fig = go.Figure()
        
        # Equity curve
        fig.add_trace(go.Scatter(
            x=date_range,
            y=equity_curve,
            mode='lines',
            name='Portfolio Value',
            line=dict(color='#00d4ff', width=2)
        ))
        
        # Initial capital line
        fig.add_hline(
            y=initial_capital,
            line_dash="dash",
            line_color="gray",
            annotation_text="Initial Capital",
            annotation_position="right"
        )
        
        fig.update_layout(
            title="Portfolio Value Over Time",
            xaxis_title="Date",
            yaxis_title="Portfolio Value ($)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Comparison with buy-and-hold (if we have price data)
        if config.get('used_real_data') and equity_curve:
            st.subheader("Comparison: Strategy vs Buy-and-Hold")
            st.info("Buy-and-hold comparison requires historical price data. This feature will be enhanced in future updates.")
    
    # Additional metrics table
    if metrics:
        st.subheader("Detailed Metrics")
        metrics_df = pd.DataFrame([
            {"Metric": "Total Return", "Value": f"{total_return:.2f}%"},
            {"Metric": "Final Value", "Value": f"${final_value:,.2f}"},
            {"Metric": "Sharpe Ratio", "Value": f"{sharpe:.2f}"},
            {"Metric": "Max Drawdown", "Value": f"{max_dd:.2f}%"},
            {"Metric": "Win Rate", "Value": f"{win_rate:.2f}%"},
            {"Metric": "Total Trades", "Value": len(results.get('trades', []))},
        ])
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    # Export results
    st.subheader("Export Results")
    if st.button("📥 Download Results as JSON"):
        import json
        results_json = json.dumps(results, indent=2, default=str)
        st.download_button(
            label="Download",
            data=results_json,
            file_name=f"backtest_{config['symbol'].replace('/', '_')}_{config['start_date']}_{config['end_date']}.json",
            mime="application/json"
        )

else:
    st.info("👆 Configure your backtest above and click 'Run Backtest' to see results here.")

