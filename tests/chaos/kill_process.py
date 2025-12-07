"""Kill process at specific points for chaos testing."""

import os
import signal
import logging

logger = logging.getLogger(__name__)


def kill_current_process(signal_num=signal.SIGKILL):
    """Kill the current process (for chaos testing).
    
    Args:
        signal_num: Signal to send (default SIGKILL for kill -9)
    """
    logger.critical(f"KILLING PROCESS FOR CHAOS TEST (signal: {signal_num})")
    os.kill(os.getpid(), signal_num)


def kill_at_point(point_name: str):
    """Kill process at a specific point in execution.
    
    Args:
        point_name: Name of the point to kill at
    """
    logger.warning(f"Kill point reached: {point_name}")
    kill_current_process()

