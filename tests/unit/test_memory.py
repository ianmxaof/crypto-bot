"""Unit tests for chronological memory."""

import pytest
from pathlib import Path
from core.memory.chrono import ChronologicalMemory


class TestChronologicalMemory:
    """Test chronological memory functionality."""
    
    def test_memory_creation(self):
        """Test memory can be created."""
        memory = ChronologicalMemory("test_namespace")
        assert memory.namespace == "test_namespace"
        
    def test_append_and_retrieve(self):
        """Test appending and retrieving entries."""
        memory = ChronologicalMemory("test")
        memory.append({"key": "value1"})
        memory.append({"key": "value2"})
        
        entries = memory.get_all()
        assert len(entries) == 2
        assert entries[0]["key"] == "value1"
        assert entries[1]["key"] == "value2"
        
    def test_get_recent(self):
        """Test getting recent entries."""
        memory = ChronologicalMemory("test")
        for i in range(10):
            memory.append({"index": i})
            
        recent = memory.get_recent(5)
        assert len(recent) == 5
        assert recent[-1]["index"] == 9  # Most recent
        
    def test_pnl_summary(self):
        """Test PnL summary calculation."""
        memory = ChronologicalMemory("test_pnl")
        
        memory.append({"pnl": 100.0})
        memory.append({"pnl": -50.0})
        memory.append({"pnl": 200.0})
        
        summary = memory.get_pnl_summary()
        assert summary["total_pnl"] == 250.0
        assert summary["total_trades"] == 3
        assert summary["win_rate"] == pytest.approx(0.666, abs=0.01)  # 2 wins, 1 loss

