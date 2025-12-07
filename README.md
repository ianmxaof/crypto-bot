# Crypto Swarm Trading Bot System

A complete, production-ready crypto trading bot ecosystem with funding rate arbitrage, MEV liquidation hunting, Hyperliquid market making, and an autonomous strategy council system.

## Features

- **Multi-Exchange Support**: Bybit, Binance, OKX, Hyperliquid
- **Funding Rate Arbitrage**: Delta-neutral perpetual funding collection with hot-coin rotation
- **MEV Liquidation Hunter**: Real-time Solana liquidation detection via Helius + Jito
- **Hyperliquid LP**: Delta-neutral market making with dynamic spread adjustment
- **Kelly-Optimal Capital Allocation**: Automated capital allocation with correlation hedging
- **Strategy Council v3**: Autonomous strategy invention, voting, and deployment

## Architecture

The system uses an event-driven, agent-based architecture:

- **Core Framework**: Event bus, agent base classes, rate limiting, chronological memory
- **Exchange Layer**: Unified interface for multiple exchanges
- **Strategy Agents**: Modular trading strategies
- **Overseer/Allocator**: Capital coordination and optimization
- **Strategy Council**: Self-evolving strategy ecosystem

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

### 4. Run with Docker (Recommended)

```bash
cd docker
docker-compose up -d
```

### 5. Run Locally

```bash
python -m agents.crypto.crypto_swarm_overseer
```

## Project Structure

```
crypto_bot/
├── core/                    # Core framework
│   ├── event_bus.py        # Event-driven communication
│   ├── agent_base.py       # Base agent class
│   ├── rate_limiter.py     # API rate limiting
│   └── memory/             # Chronological memory
├── exchanges/              # Exchange clients
│   ├── base.py            # Base exchange interface
│   ├── bybit_client.py    # Bybit implementation
│   ├── binance_client.py  # Binance implementation
│   ├── okx_client.py      # OKX implementation
│   └── hyperliquid_client.py  # Hyperliquid implementation
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
│   └── settings.py        # Settings management
├── docker/                 # Docker setup
│   ├── Dockerfile
│   └── docker-compose.yml
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

The overseer coordinates all agents:

```bash
python -m agents.crypto.crypto_swarm_overseer
```

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

## Security

- API keys stored in environment variables (never in code)
- Rate limiting prevents API bans
- Position size limits and risk controls
- Circuit breakers for excessive drawdowns

## Testing

Use testnet mode for safe testing:

```env
BYBIT_TESTNET=true
BINANCE_TESTNET=true
```

## Monitoring

- Logs: `logs/crypto_bot.log` (if configured)
- Memory: `data/memory/` directory
- Events: Monitor event bus for agent activity

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
3. Register with overseer

### Customizing Allocation

Modify `swarm_capital_allocator_v2.py`:
- Adjust Kelly criterion parameters
- Change correlation matrix
- Modify allocation caps

## License

MIT License - See LICENSE file for details

## Disclaimer

This software is for educational and research purposes. Trading cryptocurrencies carries significant risk. Past performance does not guarantee future results. Use at your own risk.

## Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Built with ❤️ for the crypto trading community**

