"""Order audit trail for complete order lifecycle tracking."""

import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class OrderAudit:
    """Complete audit trail for an order."""
    
    order_id: str
    client_order_id: str
    agent_id: str
    symbol: str
    side: str
    amount: Decimal
    price: Optional[Decimal]
    order_type: str  # 'market' or 'limit'
    
    # Timestamps
    timestamps: Dict[str, str] = field(default_factory=dict)  # created, submitted, filled, verified
    
    # Circuit breaker state
    circuit_breaker_state: str = "UNKNOWN"
    
    # Balance tracking
    balance_before: Optional[Decimal] = None
    balance_reserved: Optional[Decimal] = None
    balance_after: Optional[Decimal] = None
    
    # Position tracking
    position_before: Optional[Decimal] = None
    position_after: Optional[Decimal] = None
    
    # Exchange response
    exchange_response: Optional[Dict] = None
    
    # Verification
    reconciliation_verified: bool = False
    order_status_verified: bool = False
    
    # Errors
    errors: List[str] = field(default_factory=list)
    
    # Order state
    order_state: str = "CREATED"  # CREATED, SUBMITTED, FILLED, REJECTED, TIMED_OUT, PENDING_VERIFICATION, etc.
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert Decimal to string for JSON serialization
        for key in ['amount', 'price', 'balance_before', 'balance_reserved', 'balance_after',
                    'position_before', 'position_after']:
            if data.get(key) is not None:
                data[key] = str(data[key])
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> "OrderAudit":
        """Create from dictionary."""
        # Convert string back to Decimal
        for key in ['amount', 'price', 'balance_before', 'balance_reserved', 'balance_after',
                    'position_before', 'position_after']:
            if key in data and data[key] is not None:
                data[key] = Decimal(str(data[key]))
        return cls(**data)
    
    def add_timestamp(self, event: str):
        """Add a timestamp for an event."""
        self.timestamps[event] = datetime.now(timezone.utc).isoformat()
    
    def add_error(self, error: str):
        """Add an error to the audit trail."""
        self.errors.append(f"{datetime.now(timezone.utc).isoformat()}: {error}")
        logger.error(f"Order {self.order_id} error: {error}")
    
    def update_state(self, new_state: str):
        """Update order state."""
        old_state = self.order_state
        self.order_state = new_state
        logger.debug(f"Order {self.order_id} state transition: {old_state} -> {new_state}")

