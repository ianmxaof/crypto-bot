#!/bin/bash

# Phase 0: Validation and Testing Script
# Run this to systematically test your crypto bot implementation

echo "================================"
echo "Crypto Bot Phase 0 Validation"
echo "================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

EXIT_CODE=0

# Step 1: Check Python version
echo "Step 1: Checking Python version..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

if [[ $(echo "$python_version 3.9" | tr " " "\n" | sort -V | head -n 1) != "3.9" ]] && [[ $(echo "$python_version" | cut -d. -f1) -lt 3 ]] || [[ $(echo "$python_version" | cut -d. -f1) -eq 3 ]] && [[ $(echo "$python_version" | cut -d. -f2) -lt 9 ]]; then
    echo -e "${RED}❌ Python 3.9+ required${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Python version OK${NC}"
fi
echo ""

# Step 2: Install dependencies
echo "Step 2: Installing dependencies..."
pip install -r requirements.txt --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${RED}❌ Dependency installation failed${NC}"
    exit 1
fi
echo ""

# Step 3: Check for .env file
echo "Step 3: Checking environment configuration..."
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from template...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env with your API keys before running live${NC}"
    else
        echo -e "${RED}❌ .env.example not found. Cannot create .env file.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi

# Verify PAPER_TRADING is enabled by default
if grep -q "PAPER_TRADING=true" .env 2>/dev/null; then
    echo -e "${GREEN}✅ Paper trading enabled (safe mode)${NC}"
else
    echo -e "${YELLOW}⚠️  Adding PAPER_TRADING=true to .env for safety${NC}"
    if ! grep -q "PAPER_TRADING" .env 2>/dev/null; then
        echo "PAPER_TRADING=true" >> .env
    else
        sed -i.bak 's/^PAPER_TRADING=.*/PAPER_TRADING=true/' .env
    fi
fi
echo ""

# Step 4: Run unit tests
echo "Step 4: Running unit tests..."
pytest tests/unit/ -v --tb=short
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Unit tests passed${NC}"
else
    echo -e "${RED}❌ Unit tests failed - fix these before continuing${NC}"
    EXIT_CODE=1
fi
echo ""

# Step 5: Test basic imports
echo "Step 5: Testing basic imports..."
python -c "
from core.event_bus import EventBus
from core.agent_base import Agent
from core.rate_limiter import RateLimiter
from exchanges.mock_exchange import MockExchange
from simulation.position_tracker import PositionTracker
print('✅ All core imports successful')
" 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Import tests passed${NC}"
else
    echo -e "${RED}❌ Import errors detected${NC}"
    EXIT_CODE=1
fi
echo ""

# Step 6: Test mock exchange
echo "Step 6: Testing mock exchange initialization..."
python scripts/test_connection.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Mock exchange test passed${NC}"
else
    echo -e "${RED}❌ Mock exchange test failed${NC}"
    EXIT_CODE=1
fi
echo ""

# Step 7: Run integration tests
echo "Step 7: Running integration tests..."
pytest tests/integration/ -v --tb=short
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Integration tests passed${NC}"
else
    echo -e "${YELLOW}⚠️  Integration tests failed (may need real data)${NC}"
fi
echo ""

# Step 8: Quick paper trading smoke test
echo "Step 8: Running paper trading smoke test (10 seconds)..."
timeout 10s python main.py > /tmp/bot_test.log 2>&1 &
PID=$!

sleep 10

kill $PID 2>/dev/null
wait $PID 2>/dev/null

if grep -q "ERROR\|Exception\|Traceback" /tmp/bot_test.log 2>/dev/null; then
    echo -e "${RED}❌ Paper trading test encountered errors:${NC}"
    tail -20 /tmp/bot_test.log
    EXIT_CODE=1
else
    echo -e "${GREEN}✅ Paper trading smoke test passed${NC}"
fi
rm -f /tmp/bot_test.log
echo ""

# Summary
echo "================================"
echo "Validation Summary"
echo "================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Phase 0 validation complete!${NC}"
else
    echo -e "${RED}❌ Validation completed with errors${NC}"
fi
echo ""
echo "Next steps:"
echo "1. Review test output above for any warnings"
echo "2. Run full paper trading: PAPER_TRADING=true python main.py"
echo "3. Monitor logs for 5-10 minutes"
echo "4. Run backtest: python scripts/run_backtest.py"
echo ""
echo -e "${YELLOW}⚠️  Remember: Keep PAPER_TRADING=true until backtests validate profitability${NC}"

exit $EXIT_CODE

