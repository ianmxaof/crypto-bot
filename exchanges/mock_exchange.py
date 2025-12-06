"""Mock exchange for paper trading simulation."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from decimal import Decimal
from datetime import datetime, timezone
import uuid

from .base import BaseExchange, Balance, Position, Order, FundingRate, ExchangeError, OrderValidationResult, OrderRejectionReason
from simulation.state_manager import SimulationState
from simulation.pnl_calculator import PnLCalculator
from simulation.atomic_balance import AtomicBalanceManager

logger = logging.getLogger(__name__)


class MockExchange(BaseExchange):
    """Mock exchange for paper trading - simulates all operations without real API calls."""
    
    def __init__(self, starting_balance: Decimal = Decimal('10000'),
                 fee_rate: Decimal = Decimal('0.001'), name: str = "mock"):
        """Initialize mock exchange.
        
        Args:
            starting_balance: Starting USDT balance
            fee_rate: Trading fee rate (0.001 = 0.1%)
            name: Exchange name identifier
        """
        # Use dummy credentials for mock
        super().__init__(api_key="mock_key", api_secret="mock_secret", testnet=True)
        self._is_simulation = True
        self.state = SimulationState(starting_balance, fee_rate)
        self.pnl_calculator = PnLCalculator(fee_rate)
        self.name = name
        self._order_counter = 0
        
        # Atomic balance manager for thread-safe operations
        initial_balances = self.state.balances.copy()
        self._atomic_balance = AtomicBalanceManager(initial_balances)
        
        # Track orders by client order ID for idempotent submission
        self._client_order_map: Dict[str, Order] = {}
        
        # Default prices (can be updated with real market data)
        self.state.current_prices = {
            "BTC/USDT": Decimal('60000'),
            "ETH/USDT": Decimal('3000'),
            "SOL/USDT": Decimal('180'),
            "PEPE/USDT": Decimal('0.00001'),
            "WIF/USDT": Decimal('3.5'),
            "BONK/USDT": Decimal('0.00002'),
        }
        
        logger.info(f"MockExchange initialized with ${starting_balance} starting balance")
        
    async def fetch_balance(self, currency: Optional[str] = None) -> Dict[str, Balance]:
        """Fetch account balance."""
        # Use atomic balance manager
        all_balances = await self._atomic_balance.get_all_balances()
        if currency:
            if currency in all_balances:
                return {currency: all_balances[currency]}
            return {}
        return all_balances
        
    async def fetch_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Fetch open positions."""
        positions = self.state.position_tracker.get_all_positions()
        if symbol:
            return [p for p in positions if p.symbol == symbol]
        return positions
        
    async def create_market_order(self, symbol: str, side: str, amount: Decimal,
                                   params: Optional[Dict] = None,
                                   client_order_id: Optional[str] = None) -> Order:
        """Create a market order (simulated).
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            params: Additional parameters (ignored in simulation)
            client_order_id: Client order ID for idempotent submission
            
        Returns:
            Simulated order
        """
        # Check for existing order by client_order_id (idempotent submission)
        if client_order_id:
            existing = await self.fetch_order_by_client_id(client_order_id, symbol)
            if existing:
                logger.info(f"Order with client_order_id {client_order_id} already exists, returning existing order")
                return existing
        
        # Generate client_order_id if not provided
        if not client_order_id:
            client_order_id = f"mock_client_{uuid.uuid4().hex[:16]}"
        
        # Get current price
        if symbol not in self.state.current_prices:
            raise ExchangeError(f"Unknown symbol: {symbol}")
            
        base_price = self.state.current_prices[symbol]
        
        # Calculate slippage
        slippage = self.pnl_calculator.estimate_slippage(amount, side, base_price)
        execution_price = base_price + slippage
        
        # For market orders, execute immediately
        if side == "buy":
            # Need USDT to buy
            cost = execution_price * amount
            fee = cost * self.state.pnl_calculator.fee_rate
            total_cost = cost + fee
            
            # Use atomic balance reservation
            async with self._atomic_balance.reserve("USDT", total_cost) as reserved:
                if not reserved:
                    available = await self._atomic_balance.get_balance("USDT")
                    raise ExchangeError(
                        f"Insufficient USDT balance: available={available}, required={total_cost}"
                    )
                
                # Balance is reserved, proceed with order execution
                # Update position
                self.state.position_tracker.update_position_size(symbol, amount, execution_price)
                
                # Record trade
                self.state.record_trade(symbol, side, amount, execution_price)
                
                # Balance will be committed automatically when context exits
            
        else:  # sell
            # Check if we have position to sell
            position = self.state.position_tracker.get_position(symbol)
            if not position or position.size < amount:
                raise ExchangeError(f"Insufficient position to sell: {symbol}")
                
            proceeds = execution_price * amount
            fee = proceeds * self.state.pnl_calculator.fee_rate
            
            # Calculate realized P&L
            entry_price = position.entry_price
            pnl = self.pnl_calculator.calculate_realized_pnl(
                entry_price, execution_price, amount, position.side
            )
            
            # Add proceeds to balance (atomic)
            await self._atomic_balance.add_balance("USDT", proceeds - fee)
            
            self.state.position_tracker.update_position_size(symbol, -amount, execution_price)
            self.state.record_trade(symbol, side, amount, execution_price, entry_price)
            
        # Create order object
        order_id = f"mock_order_{self._order_counter}"
        self._order_counter += 1
        
        order = Order(
            id=order_id,
            symbol=symbol,
            side=side,
            type="market",
            amount=amount,
            price=execution_price,
            status="filled",
            filled=amount,
            remaining=Decimal('0'),
            timestamp=datetime.now(timezone.utc),
            client_order_id=client_order_id
        )
        
        # Store order by client_order_id
        self._client_order_map[client_order_id] = order
        self.state.add_order(order)
        logger.info(f"Mock order executed: {side} {amount} {symbol} @ {execution_price} (client_id: {client_order_id})")
        
        return order
        
    async def create_limit_order(self, symbol: str, side: str, amount: Decimal, price: Decimal,
                                  params: Optional[Dict] = None,
                                  client_order_id: Optional[str] = None) -> Order:
        """Create a limit order (simulated).
        
        For simplicity, limit orders execute immediately if price is favorable.
        In a more sophisticated simulation, they would wait for price to cross.
        """
        # For now, treat limit orders like market orders if price is favorable
        current_price = self.state.current_prices.get(symbol)
        if not current_price:
            raise ExchangeError(f"Unknown symbol: {symbol}")
            
        # Check if limit price would execute
        if side == "buy" and price >= current_price:
            # Limit buy at or above market - execute
            return await self.create_market_order(symbol, side, amount, params)
        elif side == "sell" and price <= current_price:
            # Limit sell at or below market - execute
            return await self.create_market_order(symbol, side, amount, params)
        else:
            # Limit order not executable yet - create pending order
            if not client_order_id:
                client_order_id = f"mock_client_{uuid.uuid4().hex[:16]}"
            
            order_id = f"mock_order_{self._order_counter}"
            self._order_counter += 1
            
            order = Order(
                id=order_id,
                symbol=symbol,
                side=side,
                type="limit",
                amount=amount,
                price=price,
                status="open",
                filled=Decimal('0'),
                remaining=amount,
                timestamp=datetime.now(timezone.utc),
                client_order_id=client_order_id
            )
            self._client_order_map[client_order_id] = order
            self.state.add_order(order)
            logger.debug(f"Mock limit order placed: {side} {amount} {symbol} @ {price} (not filled yet, client_id: {client_order_id})")
            return order
            
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        # Find and remove order
        for i, order in enumerate(self.state.orders):
            if order.id == order_id and order.symbol == symbol:
                order.status = "canceled"
                logger.debug(f"Mock order canceled: {order_id}")
                return True
        return False
        
    async def fetch_order(self, order_id: str, symbol: str) -> Order:
        """Fetch order by ID."""
        for order in self.state.orders:
            if order.id == order_id and order.symbol == symbol:
                return order
        raise ExchangeError(f"Order not found: {order_id}")
    
    async def fetch_order_by_client_id(self, client_order_id: str, symbol: str) -> Optional[Order]:
        """Fetch order by client order ID (for idempotent submission).
        
        Args:
            client_order_id: Client order ID
            symbol: Trading pair symbol
            
        Returns:
            Order if found, None otherwise
        """
        if client_order_id in self._client_order_map:
            order = self._client_order_map[client_order_id]
            if order.symbol == symbol:
                return order
        return None
        
    async def fetch_funding_rates(self, symbols: Optional[List[str]] = None) -> Dict[str, FundingRate]:
        """Fetch funding rates (simulated with default rates).
        
        Returns simulated funding rates for common symbols.
        """
        # Default funding rates (can be updated with real data)
        default_rates = {
            "BTC/USDT": Decimal('0.0001'),  # 0.01%
            "ETH/USDT": Decimal('0.0001'),
            "SOL/USDT": Decimal('0.0002'),
            "PEPE/USDT": Decimal('0.0012'),  # Higher for meme coins
            "WIF/USDT": Decimal('0.0010'),
            "BONK/USDT": Decimal('0.0009'),
        }
        
        rates = {}
        symbols_to_fetch = symbols or list(default_rates.keys())
        
        for symbol in symbols_to_fetch:
            if symbol in default_rates:
                rates[symbol] = FundingRate(
                    symbol=symbol,
                    rate=default_rates[symbol],
                    timestamp=datetime.now(timezone.utc),
                    next_funding_time=datetime.now(timezone.utc)  # Simplified
                )
                
        return rates
        
    async def set_leverage(self, leverage: int, symbol: str) -> bool:
        """Set leverage (simulated - always succeeds)."""
        logger.debug(f"Mock leverage set: {leverage}x for {symbol}")
        return True
        
    async def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """Fetch ticker/price data."""
        if symbol not in self.state.current_prices:
            raise ExchangeError(f"Unknown symbol: {symbol}")
            
        price = self.state.current_prices[symbol]
        return {
            "symbol": symbol,
            "last": float(price),
            "bid": float(price * Decimal('0.999')),
            "ask": float(price * Decimal('1.001')),
            "timestamp": datetime.now(timezone.utc).timestamp() * 1000
        }
        
    async def close_position(self, symbol: str, side: Optional[str] = None) -> bool:
        """Close an open position."""
        positions = await self.fetch_positions(symbol)
        for pos in positions:
            if side is None or pos.side == side:
                close_side = 'sell' if pos.side == 'long' else 'buy'
                await self.create_market_order(symbol, close_side, pos.size)
        return True
        
    def update_price(self, symbol: str, price: Decimal):
        """Update current price (for testing/real data integration).
        
        Args:
            symbol: Trading symbol
            price: New price
        """
        self.state.update_price(symbol, price)
        
    def get_total_value(self) -> Decimal:
        """Get total portfolio value.
        
        Returns:
            Total value in USDT
        """
        return self.state.get_total_value()
        
    def get_realized_pnl(self) -> Decimal:
        """Get realized P&L.
        
        Returns:
            Realized profit/loss
        """
        return self.state.realized_pnl
        
    async def _sync_balances(self):
        """Sync atomic balance manager with state balances."""
        # Update state balances from atomic balance manager
        atomic_balances = await self._atomic_balance.get_all_balances()
        for currency, balance in atomic_balances.items():
            if currency in self.state.balances:
                self.state.balances[currency] = balance
            else:
                self.state.balances[currency] = balance
    
    async def close(self):
        """Close exchange (save state if configured)."""
        # Sync balances before saving
        await self._sync_balances()
        self.state.save_state()

