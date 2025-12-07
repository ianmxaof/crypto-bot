# Crypto Swarm Trading Bot System

A complete, production-ready crypto trading bot ecosystem with funding rate arbitrage, MEV liquidation hunting, Hyperliquid market making, and an autonomous strategy council system.

## Features

- **Multi-Exchange Support**: Bybit, Binance, OKX, Hyperliquid
- **Funding Rate Arbitrage**: Delta-neutral perpetual funding collection with hot-coin rotation
- **MEV Liquidation Hunter**: Real-time Solana liquidation detection via Helius + Jito
- **Hyperliquid LP**: Delta-neutral market making with dynamic spread adjustment
- **Kelly-Optimal Capital Allocation**: Automated capital allocation with correlation hedging
- **Strategy Council v3**: Autonomous strategy invention, voting, and deployment
- **Real-Time Dashboard**: Streamlit-based monitoring dashboard with 7 comprehensive pages
- **Backtesting Framework**: Historical strategy testing with detailed metrics
- **Market Data Provider**: Real-time and historical market data via CoinGecko API
- **Enhanced Risk Management**: Atomic balance operations, circuit breakers, position reconciliation
- **Secure Logging**: Automatic redaction of sensitive data from logs

## Architecture

The system uses an event-driven, agent-based architecture:

- **Core Framework**: Event bus with backpressure, agent base classes, rate limiting, chronological memory, symbol locking
- **Exchange Layer**: Unified interface for multiple exchanges with idempotent order submission
- **Strategy Agents**: Modular trading strategies
- **Overseer/Allocator**: Capital coordination and optimization
- **Strategy Council**: Self-evolving strategy ecosystem
- **Risk Management**: Atomic balance operations, circuit breakers with draining state, position reconciliation
- **Monitoring**: Real-time dashboard, metrics collection, alerting system
- **Data Layer**: Market data providers, trade history storage, simulation state management

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository>
cd crypto_bot
cp .env.example .env
```

### 2. Set Up Virtual Environment (Recommended)

**Windows (PowerShell):**
```powershell
.\setup_venv.ps1
.\activate.ps1
```

**Linux/Mac:**
```bash
chmod +x setup_venv.sh activate.sh
./setup_venv.sh
source activate.sh
```

**Manual Setup:**
```bash
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1
# Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```

See [VENV_SETUP.md](VENV_SETUP.md) for detailed instructions.

### 3. Configure Environment

Edit `.env` and set at least one exchange API key:

```env
BYBIT_API_KEY=your_key
BYBIT_API_SECRET=your_secret
HELIUS_API_KEY=your_helius_key  # For MEV hunting
STARTING_CAPITAL=1000
PAPER_TRADING=true  # Keep this true for safety!
```

### 4. Verify Installation

```bash
python scripts/verify_env.py
```

### 5. Run the Trading Bot

**Option A: Using main.py (Recommended)**
```bash
python main.py
```

**Option B: Direct overseer**
```bash
python -m agents.crypto.crypto_swarm_overseer
```

### 6. Launch the Dashboard

In a separate terminal, start the real-time monitoring dashboard:

```bash
# Option 1: Using launcher script
python run_dashboard.py

# Option 2: Direct Streamlit
streamlit run dashboard/Home.py
```

The dashboard will open at `http://localhost:8501`

### 7. Run with Docker (Optional)

```bash
cd docker
docker-compose up -d
```

## Project Structure

```
crypto_bot/
├── core/                    # Core framework
│   ├── event_bus.py        # Event-driven communication with backpressure
│   ├── agent_base.py       # Base agent class
│   ├── rate_limiter.py     # API rate limiting
│   ├── symbol_locker.py    # Symbol-level locking for concurrent trades
│   └── memory/             # Chronological memory
│       └── chrono.py       # Memory persistence
├── exchanges/              # Exchange clients
│   ├── base.py            # Base exchange interface
│   ├── bybit_client.py    # Bybit implementation
│   ├── binance_client.py  # Binance implementation
│   ├── okx_client.py      # OKX implementation
│   ├── hyperliquid_client.py  # Hyperliquid implementation
│   └── mock_exchange.py   # Paper trading mock exchange
├── agents/                 # Trading agents
│   └── crypto/
│       ├── funding_rate_agent.py      # Funding rate arbitrage
│       ├── mev_watcher_agent.py       # MEV hunter
│       ├── mev_helius_jito.py         # Helius integration
│       ├── mev_full_analyzer.py       # Transaction analyzer
│       ├── hyperliquid_lp_agent.py    # Hyperliquid LP
│       ├── crypto_swarm_overseer.py   # Basic overseer
│       ├── swarm_capital_allocator_v2.py  # Kelly allocator
│       └── swarm_council_v3.py        # Strategy council
├── strategies/             # Strategy logic
│   └── funding_rate.py    # Funding rate calculations
├── config/                 # Configuration
│   ├── settings.py        # Settings management
│   └── simulation_state.py  # Simulation state management
├── dashboard/              # Streamlit dashboard
│   ├── Home.py            # Dashboard entry point
│   ├── components.py      # Reusable dashboard components
│   ├── data_service.py    # Data aggregation service
│   ├── utils.py           # Dashboard utilities
│   └── pages/             # Dashboard pages
│       ├── 1_Overview.py
│       ├── 2_Agent_Performance.py
│       ├── 3_Risk_Metrics.py
│       ├── 4_Order_Flow_&_Trades.py
│       ├── 5_Balance_&_Positions.py
│       ├── 6_Simulation_Controls.py
│       └── 7_Real-Time_Events.py
├── data_providers/         # Market data providers
│   └── market_data.py     # CoinGecko API integration
├── simulation/             # Simulation engine
│   ├── atomic_balance.py  # Atomic balance operations
│   ├── pnl_calculator.py  # P&L calculations
│   ├── position_tracker.py  # Position tracking
│   └── state_manager.py   # State management
├── risk/                   # Risk management
│   ├── circuit_breaker.py # Circuit breaker with draining state
│   ├── limits.py          # Risk limits
│   ├── monitor.py         # Risk monitoring
│   └── position_reconciler.py  # Position reconciliation
├── monitoring/             # Monitoring and alerting
│   ├── metrics_collector.py  # Metrics aggregation
│   └── alerting.py        # Alert system
├── storage/                # Data storage
│   └── trade_history.py   # Trade history persistence
├── backtesting/            # Backtesting framework
│   ├── backtester.py      # Backtesting engine
│   ├── data_loader.py     # Historical data loading
│   ├── metrics.py         # Performance metrics
│   └── reporter.py        # Report generation
├── utils/                  # Utilities
│   ├── logger.py          # Logging setup
│   ├── money.py           # Decimal-safe money type
│   └── secure_logging.py  # Secure logging with redaction
├── scripts/                # Utility scripts
│   ├── verify_env.py      # Environment verification
│   ├── generate_sample_data.py  # Sample data generation
│   ├── quick_test.py      # Quick system test
│   └── run_backtest.py    # Backtest runner
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   └── integration/       # Integration tests
├── docker/                 # Docker setup
│   ├── Dockerfile
│   └── docker-compose.yml
├── run_dashboard.py        # Dashboard launcher
├── main.py                 # Main entry point
└── requirements.txt       # Python dependencies
```

## Configuration

### Environment Variables

See `.env.example` for all available options. Key settings:

- **Exchange API Keys**: Configure at least one exchange
- **STARTING_CAPITAL**: Initial capital in USDT
- **RISK_APPETITE**: Maximum deployment percentage (0.95 = 95%)
- **HELIUS_API_KEY**: Required for MEV liquidation hunting
- **LOG_LEVEL**: Logging verbosity (DEBUG, INFO, WARNING, ERROR)

### Exchange Setup

1. Create API keys on your chosen exchange(s)
2. Enable futures/perpetual trading permissions
3. For MEV hunting: Get free Helius API key at https://helius.xyz
4. Add keys to `.env` file

## Usage

### Starting the System

**Main Entry Point (Recommended):**
```bash
python main.py
```

**Direct Overseer:**
```bash
python -m agents.crypto.crypto_swarm_overseer
```

### Real-Time Dashboard

Launch the Streamlit dashboard for real-time monitoring:

```bash
# Using launcher script
python run_dashboard.py

# Or directly
streamlit run dashboard/Home.py
```

**Dashboard Features:**
- 📊 **Overview**: Total P&L, portfolio balance, key metrics, system status
- 🤖 **Agent Performance**: P&L by agent, performance tables, activity timeline
- ⚠️ **Risk Metrics**: Risk limits, drawdown tracking, daily P&L
- 📈 **Order Flow & Trades**: Order heatmap, recent trades, statistics
- 💰 **Balance & Positions**: Balance history, breakdown, position tracking
- 🎮 **Simulation Controls**: Status, data export, cache management
- 📡 **Real-Time Events**: Event statistics, system health

See [DASHBOARD_README.md](DASHBOARD_README.md) for detailed dashboard documentation.

### Individual Agents

Run agents individually for testing:

```bash
# Funding rate agent
python -m agents.crypto.funding_rate_agent

# MEV watcher
python -m agents.crypto.mev_watcher_agent

# Hyperliquid LP
python -m agents.crypto.hyperliquid_lp_agent
```

### Strategy Council

The council v3 autonomously invents and votes on strategies:

```bash
python -m agents.crypto.swarm_council_v3
```

### Backtesting

Run backtests on historical data:

```bash
python scripts/run_backtest.py --strategy funding_rate --days 30
```

### Generate Sample Data

Generate sample data for testing the dashboard:

```bash
python scripts/generate_sample_data.py --days 7 --trades 10
```

## Strategies

### Funding Rate Arbitrage

- Delta-neutral hedging (spot long + perpetual short)
- Daily rotation to top 3 highest funding rate coins
- Expected: 80-250% APR with very low risk

### MEV Liquidation Hunter

- Real-time Solana liquidation detection
- Executes buy orders on large liquidations
- Expected: 300-1500%+ APR (bursty, higher risk)

### Hyperliquid LP

- Delta-neutral market making
- Dynamic spread based on volatility
- Expected: 120-420% APR with <9% max drawdown

## Performance Tracking

All agents log performance metrics to chronological memory. View summaries:

```python
from core.memory.chrono import ChronologicalMemory

memory = ChronologicalMemory("crypto_pnl")
summary = memory.get_pnl_summary()
print(summary)
```

## Security & Reliability

### Security Features

- **API Key Protection**: API keys stored in environment variables (never in code)
- **Secure Logging**: Automatic redaction of sensitive data from logs (API keys, secrets, passwords)
- **Rate Limiting**: Prevents API bans and ensures compliance with exchange limits
- **Symbol Locking**: Prevents concurrent trades on the same symbol

### Reliability Features

- **Atomic Balance Operations**: Thread-safe balance management prevents race conditions
- **Idempotent Order Submission**: Client order IDs prevent duplicate orders on retry
- **Circuit Breaker with Draining**: Graceful handling of in-flight orders when circuit breaker trips
- **Position Reconciliation**: Automatic periodic reconciliation detects and alerts on position mismatches
- **Event Bus Backpressure**: Queue size limits prevent memory exhaustion, critical events prioritized
- **Pre-Trade Validation**: Order validation before submission prevents invalid trades

### Risk Management

- **Position Size Limits**: Configurable maximum position sizes
- **Circuit Breakers**: Automatic trading halt on excessive drawdowns
- **Risk Limits**: Daily loss limits, maximum drawdown thresholds
- **Position Tracking**: Real-time position monitoring and reconciliation

## Testing

Use testnet mode for safe testing:

```env
BYBIT_TESTNET=true
BINANCE_TESTNET=true
```

## Monitoring

### Real-Time Dashboard

The Streamlit dashboard provides comprehensive real-time monitoring:
- Live P&L tracking and portfolio balance
- Agent performance metrics and activity
- Risk metrics and drawdown monitoring
- Order flow visualization and trade history
- System health and event statistics

### Logging

- **Logs**: `logs/crypto_bot.log` (if configured)
- **Secure Logging**: Automatic redaction of sensitive data
- **Log Levels**: Configurable via `LOG_LEVEL` environment variable

### Data Storage

- **Memory**: `data/memory/` directory (ChronologicalMemory JSON files)
- **Trade History**: Persistent trade history storage
- **Simulation State**: `data/simulation_state.json`

### Metrics Collection

- **MetricsCollector**: Aggregated performance metrics
- **ChronologicalMemory**: Historical P&L and trade data
- **Event Bus**: Real-time event tracking with statistics

## Troubleshooting

### Exchange Connection Issues

- Verify API keys are correct
- Check API permissions (futures/perpetual trading enabled)
- Ensure rate limits aren't exceeded

### MEV Hunter Not Working

- Verify Helius API key is valid
- Check WebSocket connection to Helius
- Ensure Solana RPC endpoints are accessible

### Capital Not Allocating

- Check starting capital is > $0
- Verify risk appetite allows deployment
- Review agent logs for errors

## Development

### Adding a New Strategy

1. Create agent class inheriting from `StrategyAgent`
2. Implement `evaluate_opportunity()` and `execute()`
3. Use `client_order_id` for idempotent order submission
4. Register orders with circuit breaker
5. Use `SymbolLocker` to prevent concurrent trades
6. Register with overseer

### Customizing Allocation

Modify `swarm_capital_allocator_v2.py`:
- Adjust Kelly criterion parameters
- Change correlation matrix
- Modify allocation caps

### Code Review

Comprehensive code review prompts are available for quality assurance:
- **REVIEW_PROMPT_FOR_OPUS.md**: Detailed comprehensive review (recommended)
- **REVIEW_PROMPT_CONCISE.md**: Focused quick review

See [HOW_TO_USE_REVIEW_PROMPTS.md](HOW_TO_USE_REVIEW_PROMPTS.md) for usage instructions.

### Recent Improvements (Opus 4.5 Fixes)

The system has been enhanced with critical fixes and improvements:
- ✅ Atomic balance operations for thread-safe balance management
- ✅ Circuit breaker with DRAINING state for graceful order completion
- ✅ Position reconciliation system with periodic checks
- ✅ Idempotent order submission with client order IDs
- ✅ Event bus backpressure to prevent memory exhaustion
- ✅ Symbol-level locking to prevent concurrent trades
- ✅ Secure logging with automatic sensitive data redaction
- ✅ Pre-trade validation for order safety
- ✅ Money type for Decimal-safe financial calculations

See [OPUS_4_5_FIXES_SUMMARY.md](OPUS_4_5_FIXES_SUMMARY.md) for detailed documentation.

## License

MIT License - See LICENSE file for details

## Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies carries significant risk. Past performance does not guarantee future results. Use at your own risk.

## Documentation

Additional documentation is available:

- **[DASHBOARD_README.md](DASHBOARD_README.md)**: Complete dashboard documentation
- **[VENV_SETUP.md](VENV_SETUP.md)**: Detailed virtual environment setup guide
- **[OPUS_4_5_FIXES_SUMMARY.md](OPUS_4_5_FIXES_SUMMARY.md)**: Critical fixes and improvements
- **[HOW_TO_USE_REVIEW_PROMPTS.md](HOW_TO_USE_REVIEW_PROMPTS.md)**: Code review guide
- **[REVIEW_PROMPT_FOR_OPUS.md](REVIEW_PROMPT_FOR_OPUS.md)**: Comprehensive review prompt
- **[REVIEW_PROMPT_CONCISE.md](REVIEW_PROMPT_CONCISE.md)**: Concise review prompt

## Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Built with ❤️ for the crypto trading community**

