# Streamlit Trading Dashboard

Real-time monitoring dashboard for the Crypto Swarm Trading Bot.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install Streamlit and Plotly if not already present.

### 2. Generate Sample Data (Optional)

If you want to see the dashboard with sample data before running the bot:

```bash
python scripts/generate_sample_data.py --days 7 --trades 10
```

This generates 7 days of sample trading data (10 trades per day).

### 3. Run the Dashboard

```bash
streamlit run dashboard/Home.py
```

Or use the launcher script:
```bash
python run_dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Dashboard Features

### 📊 Overview
- Total P&L curve
- Portfolio balance history
- Key metrics (Sharpe ratio, win rate, max drawdown)
- System status
- Performance summary

### 🤖 Agent Performance
- PnL contribution by agent (pie chart)
- Agent performance table
- Agent activity timeline
- Individual agent details

### ⚠️ Risk Metrics
- Risk limits status
- Current and maximum drawdown
- Daily P&L tracking
- Drawdown chart

### 📈 Order Flow & Trades
- Order activity heatmap (by symbol and time)
- Recent trades table
- Trade statistics

### 💰 Balance & Positions
- Balance history chart
- Balance breakdown
- Position tracking (when available)

### 🎮 Simulation Controls
- Simulation status
- Data export (download CSV)
- Cache management

### 📡 Real-Time Events
- Event statistics
- System health monitoring

## Usage Tips

### Auto-Refresh
- Enable "Auto Refresh" in the sidebar
- Select update interval (Fast: 1s, Normal: 5s, Slow: 10s)
- Or use "Manual" mode and click "Refresh Now"

### Data Points
- Adjust "Data Points" slider to control how much historical data is displayed
- More points = more detail but slower rendering
- Recommended: 1000-2000 points for smooth performance

### Integration with Running Bot

The dashboard reads from the same data sources as your bot:
- `ChronologicalMemory` for PnL and trade history
- `MetricsCollector` for aggregated metrics
- Settings for configuration

**To use with a running bot:**
1. Start your bot in paper trading mode: `PAPER_TRADING=true python main.py`
2. Run the dashboard in another terminal: `streamlit run dashboard/Home.py` (or `python run_dashboard.py`)
3. The dashboard will automatically pick up data as the bot runs

### Standalone Mode

You can also use the dashboard to visualize historical data:
1. Generate or load historical data
2. Run dashboard (it reads from memory files)
3. View charts and metrics

## Data Sources

The dashboard reads from:
- **Memory Directory**: `data/memory/crypto_pnl.json` (configurable via `MEMORY_DIR` in settings)
- **ChronologicalMemory**: Stores PnL entries, trades, agent activity
- **MetricsCollector**: Aggregated metrics and statistics

## Customization

### Update Intervals
Edit `dashboard/config.py` to change default update intervals.

### Chart Colors
Modify `COLORS` and `AGENT_COLORS` in `dashboard/config.py`.

### Data Limits
Adjust `MAX_DATA_POINTS` in `dashboard/config.py` for default data limit.

## Troubleshooting

### "No data available"
- Run the bot first to generate data, or
- Generate sample data: `python scripts/generate_sample_data.py`

### Dashboard not updating
- Check if "Auto Refresh" is enabled
- Click "Refresh Now" manually
- Clear cache: Click "Clear Cache" button

### Performance issues
- Reduce "Data Points" slider value
- Disable auto-refresh
- Close other browser tabs

## Advanced Usage

### Export Data
Click "Download PnL Data (CSV)" in Simulation Controls to export all data.

### Multiple Dashboards
You can run multiple dashboard instances on different ports:
```bash
streamlit run dashboard/Home.py --server.port 8502
```

### Custom Memory Namespace
Modify `dashboard/data_service.py` to use a different memory namespace if needed.

## Next Steps

1. **Run your bot** in paper trading mode to generate real data
2. **Monitor performance** using the dashboard
3. **Analyze patterns** in agent behavior
4. **Optimize strategies** based on dashboard insights

---

**Happy Trading! 📈**

