"""Integration tests for paper trading."""

import pytest
import asyncio
from decimal import Decimal
from exchanges.mock_exchange import MockExchange


class TestPaperTrading:
    """Test paper trading functionality."""
    
    @pytest.mark.asyncio
    async def test_mock_exchange_creation(self):
        """Test mock exchange can be created."""
        exchange = MockExchange(starting_balance=Decimal('10000'))
        assert exchange is not None
        assert exchange.is_simulation()
        
    @pytest.mark.asyncio
    async def test_mock_exchange_balance(self):
        """Test mock exchange balance tracking."""
        exchange = MockExchange(starting_balance=Decimal('10000'))
        
        balance = await exchange.fetch_balance("USDT")
        assert "USDT" in balance
        assert balance["USDT"].total == Decimal('10000')
        assert balance["USDT"].free == Decimal('10000')
        
    @pytest.mark.asyncio
    async def test_mock_exchange_buy_order(self):
        """Test placing buy order in mock exchange."""
        exchange = MockExchange(starting_balance=Decimal('10000'))
        
        # Place buy order
        order = await exchange.create_market_order("BTC/USDT", "buy", Decimal('0.1'))
        
        assert order is not None
        assert order.status == "filled"
        assert order.side == "buy"
        
        # Check balance decreased
        balance = await exchange.fetch_balance("USDT")
        assert balance["USDT"].free < Decimal('10000')
        
        # Check position created
        positions = await exchange.fetch_positions("BTC/USDT")
        assert len(positions) > 0
        
    @pytest.mark.asyncio
    async def test_mock_exchange_pnl_tracking(self):
        """Test P&L tracking in mock exchange."""
        exchange = MockExchange(starting_balance=Decimal('10000'))
        
        # Buy
        await exchange.create_market_order("BTC/USDT", "buy", Decimal('0.1'))
        
        # Update price to simulate profit
        exchange.update_price("BTC/USDT", Decimal('61000'))  # Price went up
        
        # Check total value increased
        total_value = exchange.get_total_value()
        assert total_value > Decimal('10000')

