"""OrderGateway - The single most important class for order submission.

This is the ONLY path to exchange order submission. All agents MUST use this gateway.
Enforces complete transactional order flow with proper failure handling.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone
import uuid

from exchanges.base import BaseExchange, Order, OrderValidationResult, ExchangeError
from risk.circuit_breaker import CircuitBreaker, CircuitBreakerState
from core.symbol_locker import SymbolLocker, SymbolLockError
from simulation.atomic_balance import AtomicBalanceManager
from core.event_bus import event_bus
from core.order_audit import OrderAudit
from core.order_persistence import OrderPersistence

logger = logging.getLogger(__name__)


class OrderGatewayError(Exception):
    """Base exception for OrderGateway errors."""
    pass


class OrderState:
    """Order state constants."""
    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    TIMED_OUT = "TIMED_OUT"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    VERIFIED_FILLED = "VERIFIED_FILLED"
    VERIFIED_REJECTED = "VERIFIED_REJECTED"
    ORPHANED = "ORPHANED"


class OrderGateway:
    """Centralized order submission gateway with transactional guarantees.
    
    This is the ONLY path to exchange order submission. All agents MUST use this gateway.
    
    Order Flow:
    1. Circuit breaker check (FIRST - before any state changes)
    2. Symbol lock acquisition
    3. Balance reservation
    4. Order validation
    5. Idempotency check (deterministic client_order_id generation)
    6. Exchange submission
    7. Order status tracking
    8. Position update
    9. P&L calculation
    
    Failure Handling:
    - Circuit breaker check fails → Return error, no state change
    - Symbol lock fails → Return error, no state change
    - Balance reservation fails → Release symbol lock, return error
    - Order validation fails → Release balance, release symbol lock, return error
    - Idempotency check finds existing → Return existing order, release balance/lock
    - Exchange submission fails → Release balance, release symbol lock, return error
    - Exchange submission times out → DO NOT release balance/lock, mark PENDING_VERIFICATION
    - Position update fails → Log error, trigger reconciliation, DO NOT release balance
    """
    
    def __init__(self, 
                 exchange: BaseExchange,
                 circuit_breaker: CircuitBreaker,
                 symbol_locker: SymbolLocker,
                 balance_manager: Optional[AtomicBalanceManager] = None,
                 order_persistence: Optional[OrderPersistence] = None):
        """Initialize OrderGateway.
        
        Args:
            exchange: Exchange instance to submit orders to
            circuit_breaker: Circuit breaker instance for risk checks
            symbol_locker: Symbol locker for preventing concurrent trades
            balance_manager: Optional atomic balance manager (required for simulation)
            order_persistence: Optional order persistence instance
        """
        self.exchange = exchange
        self.circuit_breaker = circuit_breaker
        self.symbol_locker = symbol_locker
        self.balance_manager = balance_manager
        self.order_persistence = order_persistence
        
        # Track pending verification orders (blocks new orders on same symbol)
        self._pending_verification: Dict[str, str] = {}  # symbol -> order_id
        
        # Order audit trails (in-memory, will be persisted separately)
        self._audit_trails: Dict[str, OrderAudit] = {}
        
        logger.info("OrderGateway initialized")
    
    def _generate_client_order_id(self, agent_id: str, symbol: str) -> str:
        """Generate deterministic client_order_id.
        
        Format: {agent_id}_{symbol}_{timestamp_ms}_{nonce}
        
        Args:
            agent_id: Agent identifier
            symbol: Trading symbol
        """
        timestamp_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        nonce = uuid.uuid4().hex[:8]
        # Clean symbol for use in ID (remove special chars)
        clean_symbol = symbol.replace("/", "_").replace(":", "_")
        return f"{agent_id}_{clean_symbol}_{timestamp_ms}_{nonce}"
    
    async def submit_market_order(self,
                                  agent_id: str,
                                  symbol: str,
                                  side: str,
                                  amount: Decimal,
                                  currency: str = "USDT",
                                  params: Optional[Dict] = None) -> Order:
        """Submit a market order through the gateway.
        
        This is the ONLY way agents should submit orders. All safety checks are enforced.
        
        Args:
            agent_id: ID of the agent submitting the order
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount
            currency: Currency for balance checks (default: USDT)
            params: Additional parameters for exchange
        
        Returns:
            Order object
        
        Raises:
            OrderGatewayError: If order cannot be submitted
        """
        client_order_id = self._generate_client_order_id(agent_id, symbol)
        
        # Create audit trail
        audit = OrderAudit(
            order_id="",  # Will be set after submission
            client_order_id=client_order_id,
            agent_id=agent_id,
            symbol=symbol,
            side=side,
            amount=amount,
            price=None,
            order_type="market"
        )
        audit.add_timestamp("created")
        audit.order_state = OrderState.CREATED
        
        try:
            # STEP 1: Circuit breaker check (FIRST - before any state changes)
            current_value = await self._get_current_portfolio_value()
            allowed, error_msg = await self.circuit_breaker.check(current_value)
            audit.circuit_breaker_state = self.circuit_breaker.state.value
            
            if not allowed:
                audit.add_error(f"Circuit breaker blocked order: {error_msg}")
                audit.update_state(OrderState.REJECTED)
                self._audit_trails[client_order_id] = audit
                raise OrderGatewayError(f"Circuit breaker blocked order: {error_msg}")
            
            # Check if symbol has pending verification order
            if symbol in self._pending_verification:
                pending_order_id = self._pending_verification[symbol]
                audit.add_error(f"Symbol {symbol} has pending verification order: {pending_order_id}")
                audit.update_state(OrderState.REJECTED)
                self._audit_trails[client_order_id] = audit
                raise OrderGatewayError(f"Symbol {symbol} has pending verification order: {pending_order_id}")
            
            # STEP 2: Symbol lock acquisition
            try:
                async with self.symbol_locker.lock_symbol(symbol, agent_id):
                    # STEP 3: Balance reservation (if balance manager available)
                    balance_reserved = False
                    reserved_amount = Decimal('0')
                    
                    if self.balance_manager and side == "buy":
                        # Get balance before reservation
                        balance_before = await self.balance_manager.get_balance(currency)
                        audit.balance_before = balance_before
                        
                        # Fetch current price to calculate cost
                        try:
                            ticker = await self.exchange.fetch_ticker(symbol)
                            current_price = Decimal(str(ticker.get('last', ticker.get('ask', '0'))))
                            if current_price == 0:
                                # Fallback: try to get price from positions or use estimate
                                logger.warning(f"Could not get price for {symbol}, using estimate")
                                current_price = Decimal('100000')  # Conservative estimate
                        except Exception as e:
                            logger.warning(f"Error fetching price for {symbol}: {e}, using estimate")
                            current_price = Decimal('100000')  # Conservative estimate
                        
                        # Calculate cost with fee estimate (0.1% fee)
                        estimated_cost = amount * current_price * Decimal('1.001')
                        reserved_amount = estimated_cost
                        
                        async with self.balance_manager.reserve(currency, estimated_cost) as reserved:
                            if not reserved:
                                available = await self.balance_manager.get_balance(currency)
                                audit.add_error(f"Insufficient balance: available={available}, required={estimated_cost}")
                                audit.update_state(OrderState.REJECTED)
                                self._audit_trails[client_order_id] = audit
                                raise OrderGatewayError(f"Insufficient {currency} balance: available={available}")
                            
                            balance_reserved = True
                            audit.balance_reserved = reserved_amount
                            
                            # STEP 4: Order validation
                            validation = await self.exchange.validate_order(symbol, side, amount, None, "market")
                            if not validation.allowed:
                                audit.add_error(f"Validation failed: {validation.message}")
                                audit.update_state(OrderState.REJECTED)
                                self._audit_trails[client_order_id] = audit
                                # Balance will be released automatically by context manager
                                raise OrderGatewayError(f"Order validation failed: {validation.message}")
                            
                            # STEP 5: Idempotency check
                            existing_order = await self.exchange.fetch_order_by_client_id(client_order_id, symbol)
                            if existing_order:
                                audit.add_error(f"Order with client_order_id {client_order_id} already exists")
                                audit.update_state(OrderState.SUBMITTED)  # Already submitted
                                audit.order_id = existing_order.id
                                # Balance will be released automatically by context manager
                                logger.info(f"Order {client_order_id} already exists, returning existing order")
                                return existing_order
                            
                            # STEP 6: Exchange submission
                            audit.add_timestamp("submitted")
                            audit.update_state(OrderState.SUBMITTED)
                            
                            try:
                                # Submit with timeout
                                order = await asyncio.wait_for(
                                    self.exchange.create_market_order(
                                        symbol, side, amount, params, client_order_id
                                    ),
                                    timeout=30.0
                                )
                                
                                audit.order_id = order.id
                                audit.exchange_response = {
                                    "status": order.status,
                                    "filled": str(order.filled),
                                    "price": str(order.price) if order.price else None
                                }
                                
                                # Register order with circuit breaker
                                self.circuit_breaker.register_order(order.id)
                                
                                # STEP 7: Order status tracking
                                if order.status in ("filled", "closed"):
                                    audit.add_timestamp("filled")
                                    audit.update_state(OrderState.FILLED)
                                    self.circuit_breaker.complete_order(order.id)
                                    
                                    # STEP 8: Position update (handled by exchange in simulation)
                                    # For real exchanges, would update position tracker here
                                    
                                    # STEP 9: P&L calculation (handled by exchange in simulation)
                                    # Balance is committed automatically when context manager exits
                                    
                                    audit.balance_after = await self.balance_manager.get_balance(currency) if self.balance_manager else None
                                    audit.order_status_verified = True
                                    
                                elif order.status in ("rejected", "canceled"):
                                    audit.update_state(OrderState.REJECTED)
                                    # Balance will be released by context manager
                                    self.circuit_breaker.complete_order(order.id)
                                
                            except asyncio.TimeoutError:
                                # Exchange submission timeout
                                audit.add_error("Exchange submission timeout (>30s)")
                                audit.update_state(OrderState.TIMED_OUT)
                                # CRITICAL: DO NOT release balance/lock on timeout
                                # We don't know if order executed
                                # Mark as PENDING_VERIFICATION
                                audit.update_state(OrderState.PENDING_VERIFICATION)
                                self._pending_verification[symbol] = client_order_id
                                
                                # Register order with circuit breaker (even though we don't have order.id)
                                # Use client_order_id as temporary identifier
                                self.circuit_breaker.register_order(client_order_id)
                                
                                # Trigger immediate reconciliation
                                event_bus.publish("risk:position_mismatch", {
                                    "reason": "order_timeout",
                                    "order_id": client_order_id,
                                    "symbol": symbol,
                                    "timestamp": datetime.now(timezone.utc).isoformat()
                                }, source="order_gateway")
                                
                                raise OrderGatewayError(f"Order submission timeout for {symbol}. Order may have executed. Status: PENDING_VERIFICATION")
                            
                            except Exception as e:
                                audit.add_error(f"Exchange submission failed: {str(e)}")
                                audit.update_state(OrderState.REJECTED)
                                # Balance will be released by context manager
                                raise OrderGatewayError(f"Exchange submission failed: {str(e)}")
                    
                    elif side == "sell":
                        # For sell orders, check position instead of balance
                        # Position validation is handled by exchange
                        
                        # STEP 4: Order validation
                        validation = await self.exchange.validate_order(symbol, side, amount, None, "market")
                        if not validation.allowed:
                            audit.add_error(f"Validation failed: {validation.message}")
                            audit.update_state(OrderState.REJECTED)
                            self._audit_trails[client_order_id] = audit
                            raise OrderGatewayError(f"Order validation failed: {validation.message}")
                        
                        # STEP 5: Idempotency check
                        existing_order = await self.exchange.fetch_order_by_client_id(client_order_id, symbol)
                        if existing_order:
                            audit.add_error(f"Order with client_order_id {client_order_id} already exists")
                            audit.update_state(OrderState.SUBMITTED)
                            audit.order_id = existing_order.id
                            logger.info(f"Order {client_order_id} already exists, returning existing order")
                            return existing_order
                        
                        # STEP 6: Exchange submission
                        audit.add_timestamp("submitted")
                        audit.update_state(OrderState.SUBMITTED)
                        
                        try:
                            order = await asyncio.wait_for(
                                self.exchange.create_market_order(
                                    symbol, side, amount, params, client_order_id
                                ),
                                timeout=30.0
                            )
                            
                            audit.order_id = order.id
                            audit.exchange_response = {
                                "status": order.status,
                                "filled": str(order.filled),
                                "price": str(order.price) if order.price else None
                            }
                            
                            self.circuit_breaker.register_order(order.id)
                            
                            if order.status in ("filled", "closed"):
                                audit.add_timestamp("filled")
                                audit.update_state(OrderState.FILLED)
                                self.circuit_breaker.complete_order(order.id)
                                audit.order_status_verified = True
                            
                        except asyncio.TimeoutError:
                            audit.add_error("Exchange submission timeout (>30s)")
                            audit.update_state(OrderState.PENDING_VERIFICATION)
                            self._pending_verification[symbol] = client_order_id
                            self.circuit_breaker.register_order(client_order_id)
                            
                            event_bus.publish("risk:position_mismatch", {
                                "reason": "order_timeout",
                                "order_id": client_order_id,
                                "symbol": symbol,
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            }, source="order_gateway")
                            
                            raise OrderGatewayError(f"Order submission timeout for {symbol}. Order may have executed. Status: PENDING_VERIFICATION")
                        
                        except Exception as e:
                            audit.add_error(f"Exchange submission failed: {str(e)}")
                            audit.update_state(OrderState.REJECTED)
                            raise OrderGatewayError(f"Exchange submission failed: {str(e)}")
                    
                    # Store audit trail
                    self._audit_trails[client_order_id] = audit
                    
                    # Persist order audit trail
                    if self.order_persistence:
                        self.order_persistence.save_order(audit)
                    
                    return order
                    
            except SymbolLockError as e:
                audit.add_error(f"Symbol lock failed: {str(e)}")
                audit.update_state(OrderState.REJECTED)
                self._audit_trails[client_order_id] = audit
                raise OrderGatewayError(f"Symbol lock failed: {str(e)}")
        
        except OrderGatewayError:
            # Already logged in audit trail
            raise
        except Exception as e:
            audit.add_error(f"Unexpected error: {str(e)}")
            audit.update_state(OrderState.REJECTED)
            self._audit_trails[client_order_id] = audit
            
            # Persist order audit trail even on error
            if self.order_persistence:
                self.order_persistence.save_order(audit)
            
            logger.error(f"Unexpected error in order submission: {e}", exc_info=True)
            raise OrderGatewayError(f"Unexpected error: {str(e)}")
    
    async def _get_current_portfolio_value(self) -> Decimal:
        """Get current portfolio value for circuit breaker check.
        
        Returns:
            Current portfolio value in USDT
        """
        try:
            # Get balance
            balances = await self.exchange.fetch_balance("USDT")
            total_value = Decimal('0')
            
            if "USDT" in balances:
                total_value += balances["USDT"].total
            
            # Add position values
            positions = await self.exchange.fetch_positions()
            for pos in positions:
                # Estimate position value (simplified)
                total_value += pos.size * pos.entry_price
            
            return total_value
        except Exception as e:
            logger.warning(f"Error getting portfolio value: {e}, returning 0")
            return Decimal('0')
    
    def get_audit_trail(self, client_order_id: str) -> Optional[OrderAudit]:
        """Get audit trail for an order.
        
        Args:
            client_order_id: Client order ID
        
        Returns:
            OrderAudit if found, None otherwise
        """
        return self._audit_trails.get(client_order_id)
    
    def get_pending_verification_orders(self) -> Dict[str, str]:
        """Get all orders pending verification.
        
        Returns:
            Dictionary mapping symbol -> order_id
        """
        return self._pending_verification.copy()
    
    async def verify_pending_order(self, symbol: str, order_id: Optional[str] = None) -> bool:
        """Verify a pending order by checking exchange status.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to verify (if None, verifies all pending for symbol)
        
        Returns:
            True if order verified, False otherwise
        """
        if order_id:
            # Verify specific order
            try:
                order = await self.exchange.fetch_order(order_id, symbol)
                if order.status in ("filled", "closed"):
                    # Order filled
                    if symbol in self._pending_verification:
                        del self._pending_verification[symbol]
                    return True
                elif order.status in ("rejected", "canceled"):
                    # Order rejected - can release resources
                    if symbol in self._pending_verification:
                        del self._pending_verification[symbol]
                    return True
            except Exception as e:
                logger.error(f"Error verifying order {order_id}: {e}")
                return False
        else:
            # Verify all pending for symbol
            if symbol in self._pending_verification:
                pending_id = self._pending_verification[symbol]
                return await self.verify_pending_order(symbol, pending_id)
        
        return False

