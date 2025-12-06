"""Manage simulation state for paper trading."""

import json
import logging
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from pathlib import Path

from exchanges.base import Balance, Position, Order
from simulation.position_tracker import PositionTracker
from simulation.pnl_calculator import PnLCalculator

logger = logging.getLogger(__name__)


class SimulationState:
    """Manages complete simulation state."""
    
    def __init__(self, starting_balance: Decimal, fee_rate: Decimal = Decimal('0.001'),
                 persist_path: Optional[Path] = None):
        """Initialize simulation state.
        
        Args:
            starting_balance: Starting USDT balance
            fee_rate: Trading fee rate (0.001 = 0.1%)
            persist_path: Optional path to persist state to disk
        """
        self.balances: Dict[str, Balance] = {
            "USDT": Balance("USDT", starting_balance, starting_balance, Decimal('0'))
        }
        self.position_tracker = PositionTracker()
        self.pnl_calculator = PnLCalculator(fee_rate)
        self.orders: List[Order] = []
        self.trade_history: List[Dict] = []
        self.current_prices: Dict[str, Decimal] = {}
        self.realized_pnl = Decimal('0')
        self.persist_path = persist_path
        self.starting_capital = starting_balance
        
    def get_balance(self, currency: str = "USDT") -> Decimal:
        """Get balance for a currency.
        
        Args:
            currency: Currency code
            
        Returns:
            Available balance
        """
        if currency in self.balances:
            return self.balances[currency].free
        return Decimal('0')
        
    def update_balance(self, currency: str, amount: Decimal, operation: str = "subtract"):
        """Update balance.
        
        Args:
            currency: Currency code
            amount: Amount to adjust
            operation: 'add' or 'subtract'
        """
        if currency not in self.balances:
            if operation == "subtract" and amount > Decimal('0'):
                raise ValueError(f"Insufficient balance: {currency}")
            self.balances[currency] = Balance(currency, Decimal('0'), Decimal('0'), Decimal('0'))
            
        bal = self.balances[currency]
        
        if operation == "add":
            bal.total += amount
            bal.free += amount
        else:  # subtract
            if bal.free < amount:
                raise ValueError(f"Insufficient {currency} balance: {bal.free} < {amount}")
            bal.total -= amount
            bal.free -= amount
            
    def add_order(self, order: Order):
        """Add an order to the order list.
        
        Args:
            order: Order to add
        """
        self.orders.append(order)
        
    def record_trade(self, symbol: str, side: str, size: Decimal, price: Decimal,
                    entry_price: Optional[Decimal] = None):
        """Record a completed trade.
        
        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            size: Trade size
            price: Execution price
            entry_price: Entry price if closing a position
        """
        trade = {
            "symbol": symbol,
            "side": side,
            "size": float(size),
            "price": float(price),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if entry_price:
            pnl = self.pnl_calculator.calculate_realized_pnl(
                entry_price, price, size, "long" if side == "sell" else "short"
            )
            trade["realized_pnl"] = float(pnl)
            self.realized_pnl += pnl
            
        self.trade_history.append(trade)
        
    def get_total_value(self) -> Decimal:
        """Get total portfolio value (cash + positions).
        
        Returns:
            Total value in USDT
        """
        cash = self.get_balance("USDT")
        unrealized_pnl = self.pnl_calculator.calculate_total_unrealized_pnl(
            self.position_tracker.get_all_positions(),
            self.current_prices
        )
        return cash + unrealized_pnl + self.realized_pnl
        
    def update_price(self, symbol: str, price: Decimal):
        """Update current price for a symbol.
        
        Args:
            symbol: Trading symbol
            price: Current price
        """
        self.current_prices[symbol] = price
        
    def save_state(self):
        """Save state to disk if persist_path is set."""
        if not self.persist_path:
            return
            
        try:
            state_data = {
                "balances": {
                    curr: {
                        "total": float(bal.total),
                        "free": float(bal.free),
                        "used": float(bal.used)
                    }
                    for curr, bal in self.balances.items()
                },
                "positions": [
                    {
                        "symbol": pos.symbol,
                        "size": float(pos.size),
                        "entry_price": float(pos.entry_price),
                        "side": pos.side
                    }
                    for pos in self.position_tracker.get_all_positions()
                ],
                "realized_pnl": float(self.realized_pnl),
                "starting_capital": float(self.starting_capital)
            }
            
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_path, 'w') as f:
                json.dump(state_data, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Failed to save simulation state: {e}")
            
    def load_state(self):
        """Load state from disk if persist_path exists."""
        if not self.persist_path or not self.persist_path.exists():
            return
            
        try:
            with open(self.persist_path, 'r') as f:
                state_data = json.load(f)
                
            # Restore balances
            for curr, bal_data in state_data.get("balances", {}).items():
                self.balances[curr] = Balance(
                    curr,
                    Decimal(str(bal_data["total"])),
                    Decimal(str(bal_data["free"])),
                    Decimal(str(bal_data["used"]))
                )
                
            # Restore positions
            for pos_data in state_data.get("positions", []):
                position = Position(
                    symbol=pos_data["symbol"],
                    size=Decimal(str(pos_data["size"])),
                    entry_price=Decimal(str(pos_data["entry_price"])),
                    side=pos_data["side"]
                )
                self.position_tracker.add_position(position)
                
            self.realized_pnl = Decimal(str(state_data.get("realized_pnl", 0)))
            
        except Exception as e:
            logger.warning(f"Failed to load simulation state: {e}")

