#!/bin/bash
# Quick activation script for Linux/Mac
# Usage: source activate.sh

if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
    echo "✅ Virtual environment activated"
    echo "Python: $(which python)"
    echo "To deactivate, run: deactivate"
else
    echo "❌ Virtual environment not found. Run setup_venv.sh first."
    return 1 2>/dev/null || exit 1
fi

