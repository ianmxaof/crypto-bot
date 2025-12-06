# Comprehensive Code Review Prompt for Crypto Trading Bot System

## Context

You are reviewing a cryptocurrency trading bot system built in Python that implements:
- Multi-exchange support (Bybit, Binance, OKX, Hyperliquid)
- Funding rate arbitrage strategies
- MEV liquidation hunting on Solana
- Paper trading/simulation mode with mock exchange
- Event-driven agent architecture
- Risk management (circuit breakers, position limits)
- Backtesting framework

The system is currently in Phase 0 validation and needs a comprehensive security, robustness, and architecture review before live trading.

## System Architecture Overview

**Core Components:**
- `main.py` - Entry point, initializes overseer and agents
- `core/event_bus.py` - Event-driven pub/sub system for agent coordination
- `core/agent_base.py` - Base agent class with lifecycle management
- `exchanges/mock_exchange.py` - Paper trading simulation
- `exchanges/base.py` - Unified exchange interface
- `agents/crypto/funding_rate_agent.py` - Funding rate arbitrage strategy
- `risk/circuit_breaker.py` - Loss protection mechanism
- `config/settings.py` - Environment-based configuration
- `simulation/` - P&L tracking, position management, state management

**Key Design Patterns:**
- Event-driven architecture (EventBus)
- Agent-based system (multiple trading strategies)
- Strategy pattern (exchange abstraction)
- Observer pattern (event subscriptions)

## Critical Review Areas

### 1. SECURITY ANALYSIS

**API Key Management:**
- Review `config/settings.py` - Are API keys properly secured?
- Check for any hardcoded credentials or secrets
- Verify .env file handling and gitignore patterns
- Assess risk of key leakage in logs or error messages

**Input Validation:**
- Are all user inputs and configuration values validated?
- Decimal precision handling for financial calculations
- Symbol/currency validation before API calls
- Rate limiting to prevent API abuse

**Network Security:**
- HTTPS/WSS usage for all exchange connections
- Certificate validation
- Request signing and authentication
- Protection against replay attacks

**Code Injection Risks:**
- SQL injection (if any database usage)
- Command injection in subprocess calls
- Path traversal in file operations

### 2. ERROR HANDLING & ROBUSTNESS

**Exception Handling:**
- Review error handling in `main.py`, `core/event_bus.py`, `core/agent_base.py`
- Are all critical paths wrapped in try/except?
- Are exceptions logged appropriately?
- Is there proper cleanup on exceptions (resource leaks)?

**Network Failures:**
- How does the system handle exchange API timeouts?
- Retry logic and exponential backoff
- Connection drops and reconnection strategies
- Partial order fills and order state reconciliation

**Data Integrity:**
- What happens if price data is stale or missing?
- Handling of exchange API inconsistencies
- Position tracking accuracy (internal vs exchange state)
- Balance reconciliation

**Edge Cases:**
- Zero or negative balances
- Extremely large or small order sizes
- Market halts or exchange maintenance
- Funding rate calculation errors
- Slippage exceeding expected bounds
- Concurrent order placement conflicts

### 3. FINANCIAL CALCULATION ACCURACY

**Decimal Precision:**
- Review all financial calculations in `simulation/pnl_calculator.py`
- Are Decimal types used consistently (not float)?
- Rounding errors and precision loss
- Fee calculations accuracy
- P&L calculation correctness (long/short, entry/exit)

**Slippage & Fees:**
- Realistic slippage modeling in `exchanges/mock_exchange.py`
- Fee application (maker vs taker, tiered fees)
- Funding rate payments timing and calculation
- Position sizing with fees included

**Risk Calculations:**
- Position size limits enforcement
- Leverage calculations
- Margin requirements
- Drawdown calculations in `risk/circuit_breaker.py`

### 4. CONCURRENCY & RACE CONDITIONS

**Async/Await Safety:**
- Review async patterns in `core/event_bus.py` and agent loops
- Event bus queue overflow handling
- Task cancellation and cleanup
- Deadlock potential in async operations

**Shared State:**
- Thread safety of position tracking
- Event bus subscriber concurrency
- Exchange client connection pooling
- Agent state synchronization

**Race Conditions:**
- Multiple agents trading same symbol simultaneously
- Order placement while position closing
- Balance updates during concurrent trades
- Event processing order guarantees

### 5. MEMORY & RESOURCE MANAGEMENT

**Memory Leaks:**
- Event bus event history accumulation
- Agent task cleanup on stop
- Exchange connection lifecycle
- Log file rotation and cleanup

**Resource Limits:**
- Maximum open positions tracking
- WebSocket connection limits
- File handle management
- Database connection pooling (if applicable)

**Performance:**
- Event processing bottlenecks
- Agent loop efficiency
- Exchange API call frequency
- Data structure choices (dicts, lists, etc.)

### 6. RISK MANAGEMENT EFFECTIVENESS

**Circuit Breaker:**
- Review `risk/circuit_breaker.py` implementation
- Does it actually prevent trades when triggered?
- State transition logic correctness
- Recovery mechanism safety

**Position Limits:**
- Enforcement in `risk/limits.py`
- Per-symbol vs total portfolio limits
- Dynamic position sizing
- Emergency position closure

**Capital Protection:**
- Maximum drawdown enforcement
- Daily loss limits
- Position size relative to capital
- Correlation risk (multiple positions in correlated assets)

### 7. PAPER TRADING ACCURACY

**Mock Exchange Realism:**
- Review `exchanges/mock_exchange.py` simulation accuracy
- Does it properly simulate real exchange behavior?
- Slippage modeling realism
- Order execution timing
- Price update mechanisms

**State Persistence:**
- Does paper trading state persist across restarts?
- Position tracking accuracy
- Balance reconciliation
- Trade history completeness

**Gap Between Paper and Live:**
- What behaviors differ between mock and real exchanges?
- Missing edge cases in simulation
- Latency differences
- API rate limit differences

### 8. TESTING & VALIDATION

**Test Coverage:**
- Unit test completeness (`tests/unit/`)
- Integration test coverage (`tests/integration/`)
- Edge case testing
- Error condition testing

**Test Quality:**
- Are tests actually validating correctness?
- Mock data realism
- Test isolation and cleanup
- Performance testing

**Validation Scripts:**
- Review `phase0_validation.ps1` and `phase0_validation.sh`
- Are all critical paths validated?
- Missing validation checks?

### 9. CONFIGURATION & DEPLOYMENT

**Settings Management:**
- Review `config/settings.py` for missing validations
- Environment variable handling
- Default value safety
- Type coercion and validation

**Deployment Safety:**
- PAPER_TRADING default enforcement
- Configuration validation on startup
- Missing required settings detection
- Environment-specific configurations

### 10. CODE QUALITY & MAINTAINABILITY

**Code Organization:**
- Module structure and separation of concerns
- Circular import risks
- Code duplication
- Documentation completeness

**Best Practices:**
- Type hints usage
- Docstring completeness
- Error message clarity
- Logging levels appropriateness

**Technical Debt:**
- TODO comments and incomplete features
- Deprecated patterns
- Performance optimizations needed
- Refactoring opportunities

## Specific Code Sections to Review

### Critical Paths (Must Review):

1. **Order Execution Flow:**
   ```
   Agent → Exchange.create_market_order() → Position Update → P&L Calculation
   ```
   - Review: `agents/crypto/funding_rate_agent.py` lines 98-150
   - Review: `exchanges/mock_exchange.py` lines 64-141
   - Review: `simulation/pnl_calculator.py`

2. **Risk Check Before Trade:**
   ```
   Trade Request → Circuit Breaker Check → Position Limit Check → Execute
   ```
   - Review: `risk/circuit_breaker.py` lines 47-87
   - Review: `risk/limits.py`
   - Verify these are actually called before trades

3. **Event Bus Processing:**
   ```
   Event Published → Queue → Subscriber Callback → Error Handling
   ```
   - Review: `core/event_bus.py` lines 83-130
   - Check for event loss, queue overflow, callback errors

4. **Agent Lifecycle:**
   ```
   Start → Run Loop → Error → Retry/Stop → Cleanup
   ```
   - Review: `core/agent_base.py` lines 56-175
   - Verify proper cleanup on errors

5. **Main Application Flow:**
   ```
   Startup → Validation → Exchange Init → Agent Start → Run → Shutdown
   ```
   - Review: `main.py` lines 22-119
   - Check error handling and cleanup

### High-Risk Areas (Detailed Review):

1. **Mock Exchange Order Execution** (`exchanges/mock_exchange.py:64-141`)
   - Verify balance checks before trades
   - Position size validation
   - Fee calculation accuracy
   - Slippage application

2. **Circuit Breaker Logic** (`risk/circuit_breaker.py:47-87`)
   - State transition correctness
   - Threshold calculation accuracy
   - Recovery mechanism safety

3. **Funding Rate Agent** (`agents/crypto/funding_rate_agent.py:38-150`)
   - Position opening/closing logic
   - Rebalancing safety
   - Error recovery

4. **Event Bus** (`core/event_bus.py:83-130`)
   - Queue overflow handling
   - Subscriber error isolation
   - Task cleanup

5. **P&L Calculation** (`simulation/pnl_calculator.py`)
   - Long/short P&L correctness
   - Fee inclusion
   - Funding payment tracking

## Review Output Format

Please provide your review in the following structure:

### Executive Summary
- Overall risk assessment (Low/Medium/High/Critical)
- Top 3 critical issues
- Top 3 recommendations

### Detailed Findings

For each finding, provide:
1. **Severity:** Critical/High/Medium/Low
2. **Category:** Security/Correctness/Robustness/Performance/Maintainability
3. **Location:** File path and line numbers
4. **Issue Description:** Clear explanation of the problem
5. **Impact:** What could go wrong in production
6. **Recommendation:** Specific fix or improvement
7. **Code Example:** If applicable, show problematic code and suggested fix

### Priority Action Items

List in priority order:
1. **Must Fix Before Live Trading** (Critical issues)
2. **Should Fix Soon** (High priority)
3. **Nice to Have** (Medium/Low priority)

### Architecture Recommendations

- Design pattern improvements
- Missing components
- Scalability concerns
- Monitoring and observability gaps

### Testing Recommendations

- Missing test cases
- Test improvements needed
- Edge cases to test
- Integration test gaps

### Security Hardening

- Security vulnerabilities
- Best practices not followed
- Additional security measures needed

## Questions to Answer

1. **Is this system safe to run with real money?** If not, what must be fixed first?

2. **What is the worst-case scenario failure mode?** (e.g., losing all capital, making unintended trades, API key compromise)

3. **Are there any obvious bugs that would cause immediate losses?**

4. **Is the paper trading mode accurate enough to trust for strategy validation?**

5. **What monitoring/alerting is missing that would be critical for live trading?**

6. **Are there any compliance or regulatory concerns?**

7. **What would you change if you were deploying this to production with $100K capital?**

## Additional Context

**Current State:**
- System has validation scripts (`phase0_validation.ps1`, `phase0_validation.sh`)
- Basic unit and integration tests exist
- Paper trading mode is functional
- Backtesting framework is in place but may need historical data

**Known Limitations:**
- Some exchange clients may be incomplete
- Historical data download may not be implemented
- Alerting system may be basic
- Some agents may be placeholders

**Deployment Target:**
- Initially: Small capital ($1K-$10K) paper trading
- Eventually: Live trading with real capital
- Expected strategies: Funding rate arbitrage, MEV hunting, market making

---

**Please conduct a thorough, critical review focusing on production-readiness, financial correctness, and system robustness. Be specific with code references and actionable recommendations.**

