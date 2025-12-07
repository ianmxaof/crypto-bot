"""Simulation state management for runtime control via dashboard.

This module provides utilities for reading and writing simulation state
to data/simulation_state.json. This follows the industry-standard pattern
used by Hummingbot, Freqtrade, and 3Commas.

The state file is separate from .env to allow runtime updates without
modifying boot-time configuration files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import tempfile
import os

logger = logging.getLogger(__name__)

# State file location (git-ignored, runtime state only)
STATE_FILE = Path(__file__).parent.parent / "data" / "simulation_state.json"

# Default state structure
DEFAULT_STATE = {
    "running": False,
    "speed": 100,
    "days": 30,
    "starting_capital": 1000,
    "last_updated": None,
    "start_time": None,  # When simulation started
    "elapsed_real_seconds": 0.0,  # Real-time elapsed
    "elapsed_sim_days": 0.0,  # Simulated days elapsed
    "cycle_count": 0,  # Number of cycles completed
    "current_phase": "idle",  # idle, initializing, allocating, running, complete
    "selected_market": "BTCUSDT",  # Selected market for live price data
    "allocation_pct": 0.0  # Current allocation percentage
}


def ensure_state_directory() -> Path:
    """Ensure the state file directory exists."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return STATE_FILE.parent


def read_simulation_state() -> Dict[str, Any]:
    """Read current simulation state from file.
    
    Returns:
        Dictionary with simulation state. Returns default state if file doesn't exist.
    """
    try:
        if not STATE_FILE.exists():
            # Return default state if file doesn't exist yet
            return DEFAULT_STATE.copy()
        
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        # Ensure all required keys exist
        for key, default_value in DEFAULT_STATE.items():
            if key not in state:
                state[key] = default_value
        
        return state
        
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse simulation state file: {e}. Using defaults.")
        return DEFAULT_STATE.copy()
    except Exception as e:
        logger.error(f"Error reading simulation state: {e}. Using defaults.")
        return DEFAULT_STATE.copy()


def write_simulation_state(state: Dict[str, Any]) -> bool:
    """Write simulation state to file atomically.
    
    Uses atomic write pattern: write to temp file, then rename.
    This prevents file corruption on concurrent writes.
    
    Args:
        state: State dictionary to write
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        ensure_state_directory()
        
        # Validate state structure
        validated_state = {}
        for key, default_value in DEFAULT_STATE.items():
            if key in state:
                validated_state[key] = state[key]
            else:
                validated_state[key] = default_value
        
        # Add timestamp
        validated_state["last_updated"] = datetime.now(timezone.utc).isoformat()
        
        # Atomic write: write to temp file, then rename
        temp_file = STATE_FILE.with_suffix('.tmp')
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(validated_state, f, indent=2, ensure_ascii=False)
        
        # Atomic rename (works on both Unix and Windows)
        if os.name == 'nt':  # Windows
            # On Windows, need to remove target first if it exists
            if STATE_FILE.exists():
                os.remove(STATE_FILE)
        temp_file.replace(STATE_FILE)
        
        logger.debug(f"Simulation state updated: running={validated_state['running']}, "
                    f"speed={validated_state['speed']}x, days={validated_state['days']}")
        return True
        
    except Exception as e:
        logger.error(f"Error writing simulation state: {e}", exc_info=True)
        return False


def get_simulation_running() -> bool:
    """Get current simulation running status.
    
    Returns:
        True if simulation is running, False otherwise
    """
    state = read_simulation_state()
    return state.get("running", False)


def get_simulation_speed() -> float:
    """Get current simulation speed multiplier.
    
    Returns:
        Speed multiplier (e.g., 100.0 for 100x speed)
    """
    state = read_simulation_state()
    return float(state.get("speed", 100))


def get_simulation_days() -> int:
    """Get target simulation duration in days.
    
    Returns:
        Number of days to simulate
    """
    state = read_simulation_state()
    return int(state.get("days", 30))


def get_starting_capital() -> float:
    """Get starting capital for simulation.
    
    Returns:
        Starting capital amount
    """
    state = read_simulation_state()
    return float(state.get("starting_capital", 1000))


def set_simulation_running(running: bool) -> bool:
    """Set simulation running status.
    
    Args:
        running: True to start, False to stop
        
    Returns:
        True if successful
    """
    state = read_simulation_state()
    state["running"] = running
    return write_simulation_state(state)


def set_simulation_speed(speed: float) -> bool:
    """Set simulation speed multiplier.
    
    Args:
        speed: Speed multiplier (must be > 0)
        
    Returns:
        True if successful
    """
    if speed <= 0:
        logger.error(f"Invalid speed multiplier: {speed}. Must be > 0.")
        return False
    
    state = read_simulation_state()
    state["speed"] = float(speed)
    return write_simulation_state(state)


def set_simulation_days(days: int) -> bool:
    """Set target simulation duration.
    
    Args:
        days: Number of days to simulate (must be > 0)
        
    Returns:
        True if successful
    """
    if days <= 0:
        logger.error(f"Invalid days: {days}. Must be > 0.")
        return False
    
    state = read_simulation_state()
    state["days"] = int(days)
    return write_simulation_state(state)


def set_starting_capital(capital: float) -> bool:
    """Set starting capital.
    
    Args:
        capital: Starting capital amount (must be > 0)
        
    Returns:
        True if successful
    """
    if capital <= 0:
        logger.error(f"Invalid capital: {capital}. Must be > 0.")
        return False
    
    state = read_simulation_state()
    state["starting_capital"] = float(capital)
    return write_simulation_state(state)


def update_simulation_state(**kwargs) -> bool:
    """Update multiple simulation state values at once.
    
    Args:
        **kwargs: Key-value pairs to update (running, speed, days, starting_capital, etc.)
        
    Returns:
        True if successful
    """
    state = read_simulation_state()
    
    # Validate and update allowed keys only
    allowed_keys = {"running", "speed", "days", "starting_capital", "start_time", 
                   "elapsed_real_seconds", "elapsed_sim_days", "cycle_count", "current_phase",
                   "selected_market", "allocation_pct"}
    for key, value in kwargs.items():
        if key in allowed_keys:
            if key == "speed" and value <= 0:
                logger.error(f"Invalid speed: {value}. Must be > 0.")
                return False
            if key == "days" and value <= 0:
                logger.error(f"Invalid days: {value}. Must be > 0.")
                return False
            if key == "starting_capital" and value <= 0:
                logger.error(f"Invalid capital: {value}. Must be > 0.")
                return False
            state[key] = value
        else:
            logger.warning(f"Ignoring unknown state key: {key}")
    
    return write_simulation_state(state)


def get_progress_percentage() -> float:
    """Get simulation progress as percentage.
    
    Returns:
        Progress percentage (0-100)
    """
    state = read_simulation_state()
    target_days = state.get("days", 30)
    elapsed_sim_days = state.get("elapsed_sim_days", 0.0)
    
    if target_days <= 0:
        return 0.0
    
    progress = (elapsed_sim_days / target_days) * 100
    return min(100.0, max(0.0, progress))


def get_elapsed_sim_days() -> float:
    """Get elapsed simulation days.
    
    Returns:
        Elapsed simulated days
    """
    state = read_simulation_state()
    return float(state.get("elapsed_sim_days", 0.0))


def get_cycle_count() -> int:
    """Get number of completed cycles.
    
    Returns:
        Cycle count
    """
    state = read_simulation_state()
    return int(state.get("cycle_count", 0))


def get_current_phase() -> str:
    """Get current simulation phase.
    
    Returns:
        Current phase string
    """
    state = read_simulation_state()
    return state.get("current_phase", "idle")


def set_current_phase(phase: str) -> bool:
    """Set current simulation phase.
    
    Args:
        phase: Phase string (idle, initializing, allocating, running, complete)
        
    Returns:
        True if successful
    """
    return update_simulation_state(current_phase=phase)


def increment_cycle_count() -> bool:
    """Increment cycle count by 1.
    
    Returns:
        True if successful
    """
    state = read_simulation_state()
    current_count = state.get("cycle_count", 0)
    return update_simulation_state(cycle_count=current_count + 1)


def get_selected_market() -> str:
    """Get selected market for live price data.
    
    Returns:
        Selected market symbol (e.g., "BTCUSDT")
    """
    state = read_simulation_state()
    return state.get("selected_market", "BTCUSDT")


def set_selected_market(market: str) -> bool:
    """Set selected market for live price data.
    
    Args:
        market: Market symbol (e.g., "BTCUSDT", "ETHUSDT")
        
    Returns:
        True if successful
    """
    if not market or not isinstance(market, str):
        logger.error(f"Invalid market: {market}. Must be a non-empty string.")
        return False
    
    return update_simulation_state(selected_market=market)

