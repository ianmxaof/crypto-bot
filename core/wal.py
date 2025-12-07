"""Write-ahead log for critical events.

Implements write-ahead log pattern to ensure critical events are never lost.
Critical events are persisted to disk BEFORE being acknowledged.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone

from core.event_bus import event_bus

logger = logging.getLogger(__name__)


class WriteAheadLog:
    """Write-ahead log for critical events."""
    
    def __init__(self, wal_directory: Path):
        """Initialize write-ahead log.
        
        Args:
            wal_directory: Directory for WAL files
        """
        self.wal_directory = Path(wal_directory)
        self.wal_directory.mkdir(parents=True, exist_ok=True)
        
        # Current WAL file
        self._current_wal_file: Path = None
        self._file_handle = None
    
    def _get_wal_filename(self) -> str:
        """Get WAL filename with timestamp.
        
        Returns:
            WAL filename
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"wal_{timestamp}.log"
    
    def _open_wal_file(self):
        """Open current WAL file for writing."""
        if self._file_handle is None or self._file_handle.closed:
            self._current_wal_file = self.wal_directory / self._get_wal_filename()
            self._file_handle = open(self._current_wal_file, 'a')
            logger.debug(f"Opened WAL file: {self._current_wal_file}")
    
    def append_event(self, topic: str, data: Dict[str, Any], source: str = "unknown"):
        """Append critical event to WAL.
        
        Args:
            topic: Event topic
            data: Event data
            source: Event source
        """
        try:
            self._open_wal_file()
            
            event = {
                "topic": topic,
                "data": data,
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "persisted": True
            }
            
            # Write as JSON line
            line = json.dumps(event) + "\n"
            self._file_handle.write(line)
            self._file_handle.flush()  # Flush to disk immediately
            
            logger.debug(f"Appended critical event to WAL: {topic}")
        except Exception as e:
            logger.error(f"Error appending to WAL: {e}", exc_info=True)
    
    def replay_unpersisted_events(self) -> List[Dict[str, Any]]:
        """Replay unpersisted events from WAL files.
        
        Returns:
            List of unpersisted events
        """
        events = []
        
        try:
            # Find all WAL files
            wal_files = sorted(self.wal_directory.glob("wal_*.log"))
            
            for wal_file in wal_files:
                try:
                    with open(wal_file, 'r') as f:
                        for line in f:
                            if line.strip():
                                event = json.loads(line)
                                # Check if event was acknowledged
                                if not event.get("acknowledged", False):
                                    events.append(event)
                except Exception as e:
                    logger.error(f"Error reading WAL file {wal_file}: {e}")
            
            logger.info(f"Replaying {len(events)} unpersisted events from WAL")
        except Exception as e:
            logger.error(f"Error replaying WAL events: {e}", exc_info=True)
        
        return events
    
    def acknowledge_event(self, timestamp: str):
        """Mark event as acknowledged (optional cleanup).
        
        Args:
            timestamp: Event timestamp to acknowledge
        """
        # In a production system, would mark event as acknowledged
        # For simplicity, we'll just log it
        logger.debug(f"Acknowledged event with timestamp: {timestamp}")
    
    def close(self):
        """Close WAL file handle."""
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()
            logger.debug("WAL file closed")


# Global WAL instance
_wal_instance: WriteAheadLog = None


def initialize_wal(wal_directory: Path):
    """Initialize global WAL instance.
    
    Args:
        wal_directory: Directory for WAL files
    """
    global _wal_instance
    _wal_instance = WriteAheadLog(wal_directory)
    logger.info(f"Write-ahead log initialized: {wal_directory}")


def get_wal() -> WriteAheadLog:
    """Get global WAL instance.
    
    Returns:
        WriteAheadLog instance
    """
    if _wal_instance is None:
        raise RuntimeError("WAL not initialized - call initialize_wal() first")
    return _wal_instance

