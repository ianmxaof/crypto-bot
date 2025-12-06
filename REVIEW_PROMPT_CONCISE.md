# Concise Code Review Prompt for Crypto Trading Bot

## Your Task

Review this Python cryptocurrency trading bot for **production-readiness, security, and financial correctness** before live trading deployment.

## System Overview

- **Purpose:** Multi-strategy crypto trading bot (funding rate arbitrage, MEV hunting, market making)
- **Architecture:** Event-driven agent system with paper trading simulation
- **Status:** Phase 0 validation complete, preparing for live trading
- **Risk Level:** HIGH - handles real money, must be bulletproof

## Critical Review Areas (Priority Order)

### 1. **Financial Calculation Correctness** (CRITICAL)
- Review all Decimal-based calculations in `simulation/pnl_calculator.py`
- Verify fee calculations, slippage, P&L (long/short)
- Check position sizing with fees included
- **Question:** Could rounding errors cause balance discrepancies?

### 2. **Order Execution Safety** (CRITICAL)
- Review `exchanges/mock_exchange.py` lines 64-141 (order execution)
- Verify balance checks BEFORE trades
- Check position limit enforcement
- **Question:** Can the system place orders that exceed available balance?

### 3. **Risk Management Enforcement** (CRITICAL)
- Review `risk/circuit_breaker.py` - does it actually prevent trades?
- Check if risk limits are checked BEFORE order execution
- Verify circuit breaker state transitions
- **Question:** What happens if circuit breaker triggers mid-trade?

### 4. **Error Handling & Recovery** (HIGH)
- Review exception handling in `main.py`, `core/agent_base.py`
- Check cleanup on errors (resource leaks?)
- Verify retry logic doesn't cause duplicate orders
- **Question:** Can a network error cause position tracking to desync from exchange?

### 5. **Concurrency Safety** (HIGH)
- Review `core/event_bus.py` async event processing
- Check for race conditions in position updates
- Verify agent task cleanup
- **Question:** Can two agents trade the same symbol simultaneously?

### 6. **Security** (HIGH)
- Review `config/settings.py` - API key handling
- Check for secrets in logs/errors
- Verify input validation
- **Question:** Could API keys leak in error messages or logs?

### 7. **Paper Trading Accuracy** (MEDIUM)
- Does `exchanges/mock_exchange.py` accurately simulate real exchanges?
- What behaviors differ between mock and live?
- **Question:** Could paper trading success not translate to live trading?

## Specific Code to Review

**Must Review:**
1. `exchanges/mock_exchange.py:64-141` - Order execution logic
2. `risk/circuit_breaker.py:47-87` - Circuit breaker check logic
3. `simulation/pnl_calculator.py` - All P&L calculations
4. `core/event_bus.py:83-130` - Event processing (queue overflow?)
5. `main.py:22-119` - Startup/shutdown error handling

## Output Format

For each issue found:
- **Severity:** Critical/High/Medium/Low
- **File:** Path and line numbers
- **Issue:** What's wrong
- **Impact:** What could happen in production
- **Fix:** Specific recommendation

**Top 5 Critical Issues** (must fix before live trading)
**Top 5 Recommendations** (should implement)

## Key Questions

1. **Is this safe for real money?** If not, what must be fixed?
2. **Worst-case failure scenario?** (e.g., lose all capital, unintended trades)
3. **Any obvious bugs that cause immediate losses?**
4. **What's missing for production deployment?**

---

**Focus on finding bugs that could cause financial loss, not code style issues.**

