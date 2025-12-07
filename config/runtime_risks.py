"""Runtime risk configuration for dashboard updates.

This module provides utilities for reading and writing runtime risk settings
to data/runtime_risks.json. This allows the dashboard to update risk limits
without modifying .env or settings.py.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import os

logger = logging.getLogger(__name__)

# Risk file location (git-ignored, runtime state only)
RISK_FILE = Path(__file__).parent.parent / "data" / "runtime_risks.json"

# Default risk structure
DEFAULT_RISKS = {
    "max_position_size_usd": 5000.0,
    "max_daily_loss_percent": 5.0,
    "max_drawdown_percent": 15.0,
    "last_updated": None
}


def ensure_risk_directory() -> Path:
    """Ensure the risk file directory exists."""
    RISK_FILE.parent.mkdir(parents=True, exist_ok=True)
    return RISK_FILE.parent


def read_runtime_risks() -> Dict[str, Any]:
    """Read current runtime risk settings from file.
    
    Returns:
        Dictionary with risk settings. Returns default risks if file doesn't exist.
    """
    try:
        if not RISK_FILE.exists():
            # Return default risks if file doesn't exist yet
            return DEFAULT_RISKS.copy()
        
        with open(RISK_FILE, 'r', encoding='utf-8') as f:
            risks = json.load(f)
        
        # Ensure all required keys exist
        for key, default_value in DEFAULT_RISKS.items():
            if key not in risks:
                risks[key] = default_value
        
        return risks
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse runtime risks file: {e}. Using defaults.")
        return DEFAULT_RISKS.copy()
    except Exception as e:
        logger.error(f"Error reading runtime risks: {e}. Using defaults.")
        return DEFAULT_RISKS.copy()


def write_runtime_risks(risks: Dict[str, Any]) -> bool:
    """Write runtime risk settings to file atomically.
    
    Uses atomic write pattern: write to temp file, then rename.
    This prevents file corruption on concurrent writes.
    
    Args:
        risks: Risk dictionary to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        ensure_risk_directory()
        
        # Validate risk structure
        validated_risks = {}
        for key, default_value in DEFAULT_RISKS.items():
            if key in risks and key != "last_updated":
                validated_risks[key] = risks[key]
            else:
                validated_risks[key] = default_value
        
        # Add timestamp
        validated_risks["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Atomic write: write to temp file, then rename
        temp_file = RISK_FILE.with_suffix('.tmp')
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(validated_risks, f, indent=2, ensure_ascii=False)
        
        # Atomic rename (works on both Unix and Windows)
        if os.name == 'nt':  # Windows
            # On Windows, need to remove target first if it exists
            if RISK_FILE.exists():
                os.remove(RISK_FILE)
        temp_file.replace(RISK_FILE)
        
        logger.debug(f"Runtime risks updated: max_position=${validated_risks['max_position_size_usd']}, "
                    f"max_daily_loss={validated_risks['max_daily_loss_percent']}%")
        return True
        
    except Exception as e:
        logger.error(f"Error writing runtime risks: {e}", exc_info=True)
        return False


def update_runtime_risks(**kwargs) -> bool:
    """Update multiple risk values at once.
    
    Args:
        **kwargs: Key-value pairs to update (max_position_size_usd, max_daily_loss_percent, max_drawdown_percent)
        
    Returns:
        True if successful
    """
    risks = read_runtime_risks()
    
    # Validate and update allowed keys only
    allowed_keys = {"max_position_size_usd", "max_daily_loss_percent", "max_drawdown_percent"}
    for key, value in kwargs.items():
        if key in allowed_keys:
            if key.endswith("_usd") or key.endswith("_percent"):
                # Validate numeric values
                try:
                    float_value = float(value)
                    if float_value < 0:
                        logger.error(f"Invalid {key}: {value}. Must be >= 0.")
                        return False
                    risks[key] = float_value
                except (ValueError, TypeError):
                    logger.error(f"Invalid {key}: {value}. Must be a number.")
                    return False
            else:
                risks[key] = value
        else:
            logger.warning(f"Ignoring unknown risk key: {key}")
    
    return write_runtime_risks(risks)


def get_max_position_size() -> float:
    """Get maximum position size in USD.
    
    Returns:
        Maximum position size
    """
    risks = read_runtime_risks()
    return float(risks.get("max_position_size_usd", 5000.0))


def get_max_daily_loss_percent() -> float:
    """Get maximum daily loss percentage.
    
    Returns:
        Maximum daily loss percentage
    """
    risks = read_runtime_risks()
    return float(risks.get("max_daily_loss_percent", 5.0))


def get_max_drawdown_percent() -> float:
    """Get maximum drawdown percentage.
    
    Returns:
        Maximum drawdown percentage
    """
    risks = read_runtime_risks()
    return float(risks.get("max_drawdown_percent", 15.0))

