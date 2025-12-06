"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from decimal import Decimal
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_balance():
    """Sample balance for testing."""
    from exchanges.base import Balance
    return Balance("USDT", Decimal('10000'), Decimal('9500'), Decimal('500'))


@pytest.fixture
def sample_position():
    """Sample position for testing."""
    from exchanges.base import Position
    return Position(
        symbol="BTC/USDT",
        size=Decimal('0.1'),
        entry_price=Decimal('50000'),
        side="long",
        unrealized_pnl=Decimal('100'),
        leverage=Decimal('1')
    )


@pytest.fixture
def sample_order():
    """Sample order for testing."""
    from exchanges.base import Order
    from datetime import datetime, timezone
    return Order(
        id="test_order_123",
        symbol="BTC/USDT",
        side="buy",
        type="market",
        amount=Decimal('0.1'),
        price=None,
        status="filled",
        filled=Decimal('0.1'),
        remaining=Decimal('0'),
        timestamp=datetime.now(timezone.utc)
    )

