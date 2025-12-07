#!/usr/bin/env python
"""Quick launcher for Streamlit dashboard."""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch the Streamlit dashboard."""
    dashboard_path = Path(__file__).parent / "dashboard" / "Home.py"
    
    if not dashboard_path.exists():
        print(f"❌ Dashboard not found at {dashboard_path}")
        sys.exit(1)
    
    print("🚀 Starting Streamlit Dashboard...")
    print("📊 Dashboard will open in your browser at http://localhost:8501")
    print("💡 Press Ctrl+C to stop")
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", str(dashboard_path)
        ])
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except FileNotFoundError:
        print("❌ Streamlit not found. Install with: pip install streamlit")
        sys.exit(1)

if __name__ == "__main__":
    main()

