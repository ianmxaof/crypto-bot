"""Order state persistence for recovery after crashes."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from decimal import Decimal
from datetime import datetime, timezone

from core.order_audit import OrderAudit
from core.order_gateway import OrderState

logger = logging.getLogger(__name__)


class OrderPersistence:
    """Persist order state to disk for recovery."""
    
    def __init__(self, persistence_path: Path):
        """Initialize order persistence.
        
        Args:
            persistence_path: Path to JSON file for persistence
        """
        self.persistence_path = Path(persistence_path)
        self.persistence_path.parent.mkdir(parents=True, exist_ok=True)
        self._orders: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        """Load orders from disk."""
        if not self.persistence_path.exists():
            logger.info(f"Order persistence file does not exist: {self.persistence_path}")
            return
        
        try:
            with open(self.persistence_path, 'r') as f:
                self._orders = json.load(f)
            logger.info(f"Loaded {len(self._orders)} orders from persistence")
        except Exception as e:
            logger.error(f"Error loading order persistence: {e}")
            self._orders = {}
    
    def _save(self):
        """Save orders to disk."""
        try:
            with open(self.persistence_path, 'w') as f:
                json.dump(self._orders, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving order persistence: {e}")
    
    def save_order(self, audit: OrderAudit):
        """Save order audit trail.
        
        Args:
            audit: OrderAudit instance
        """
        self._orders[audit.client_order_id] = audit.to_dict()
        self._save()
        logger.debug(f"Saved order {audit.client_order_id} to persistence")
    
    def get_order(self, client_order_id: str) -> Optional[OrderAudit]:
        """Get order audit trail.
        
        Args:
            client_order_id: Client order ID
        
        Returns:
            OrderAudit if found, None otherwise
        """
        if client_order_id in self._orders:
            try:
                return OrderAudit.from_dict(self._orders[client_order_id])
            except Exception as e:
                logger.error(f"Error loading order {client_order_id}: {e}")
                return None
        return None
    
    def get_pending_orders(self) -> List[OrderAudit]:
        """Get all orders that are not in terminal state.
        
        Returns:
            List of OrderAudit for pending orders
        """
        pending = []
        terminal_states = {OrderState.FILLED, OrderState.VERIFIED_FILLED, 
                          OrderState.REJECTED, OrderState.VERIFIED_REJECTED, 
                          OrderState.ORPHANED}
        
        for client_order_id, order_dict in self._orders.items():
            try:
                audit = OrderAudit.from_dict(order_dict)
                if audit.order_state not in terminal_states:
                    pending.append(audit)
            except Exception as e:
                logger.error(f"Error loading pending order {client_order_id}: {e}")
        
        return pending
    
    def get_orders_by_state(self, state: str) -> List[OrderAudit]:
        """Get all orders with a specific state.
        
        Args:
            state: Order state
        
        Returns:
            List of OrderAudit
        """
        orders = []
        for client_order_id, order_dict in self._orders.items():
            try:
                audit = OrderAudit.from_dict(order_dict)
                if audit.order_state == state:
                    orders.append(audit)
            except Exception as e:
                logger.error(f"Error loading order {client_order_id}: {e}")
        
        return orders
    
    def update_order_state(self, client_order_id: str, new_state: str):
        """Update order state.
        
        Args:
            client_order_id: Client order ID
            new_state: New order state
        """
        if client_order_id in self._orders:
            self._orders[client_order_id]['order_state'] = new_state
            self._orders[client_order_id]['timestamps'][f"state_{new_state}"] = datetime.now(timezone.utc).isoformat()
            self._save()
            logger.debug(f"Updated order {client_order_id} state to {new_state}")
    
    def delete_order(self, client_order_id: str):
        """Delete order from persistence (for cleanup).
        
        Args:
            client_order_id: Client order ID
        """
        if client_order_id in self._orders:
            del self._orders[client_order_id]
            self._save()
            logger.debug(f"Deleted order {client_order_id} from persistence")

