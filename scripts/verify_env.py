"""Verify virtual environment setup and package installation."""

import sys
import os
from pathlib import Path

def check_venv_active():
    """Check if virtual environment is active."""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    return in_venv

def check_python_version():
    """Check Python version."""
    version = sys.version_info
    return version.major >= 3 and version.minor >= 9

def check_package(package_name):
    """Check if a package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False

def get_python_path():
    """Get Python executable path."""
    return sys.executable

def main():
    """Run verification checks."""
    print("=" * 60)
    print("Virtual Environment Verification")
    print("=" * 60)
    print()
    
    all_checks_passed = True
    
    # Check 1: Virtual environment active
    print("Check 1: Virtual Environment Status")
    if check_venv_active():
        print("  ✅ Virtual environment is ACTIVE")
        venv_path = os.environ.get('VIRTUAL_ENV', 'Unknown')
        print(f"  Location: {venv_path}")
    else:
        print("  ❌ Virtual environment is NOT active")
        print("  Activate it with:")
        if sys.platform == "win32":
            print("    .\\.venv\\Scripts\\Activate.ps1")
        else:
            print("    source .venv/bin/activate")
        all_checks_passed = False
    print()
    
    # Check 2: Python version
    print("Check 2: Python Version")
    if check_python_version():
        print(f"  ✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    else:
        print(f"  ❌ Python 3.9+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        all_checks_passed = False
    print()
    
    # Check 3: Python path
    print("Check 3: Python Executable Path")
    python_path = get_python_path()
    print(f"  Python: {python_path}")
    if '.venv' in python_path or 'venv' in python_path:
        print("  ✅ Python is from virtual environment")
    else:
        print("  ⚠️  Python may not be from virtual environment")
    print()
    
    # Check 4: Required packages
    print("Check 4: Required Packages")
    required_packages = {
        'pandas': 'Data processing',
        'streamlit': 'Dashboard',
        'plotly': 'Visualizations',
        'ccxt': 'Exchange integration',
        'pydantic': 'Data validation',
        'dotenv': 'Environment variables',  # python-dotenv imports as 'dotenv'
        'pytest': 'Testing',
    }
    
    missing_packages = []
    for package, description in required_packages.items():
        if check_package(package):
            print(f"  ✅ {package:20} - {description}")
        else:
            print(f"  ❌ {package:20} - {description} (MISSING)")
            missing_packages.append(package)
            all_checks_passed = False
    print()
    
    # Summary
    print("=" * 60)
    if all_checks_passed:
        print("✅ All checks passed! Environment is ready.")
        return 0
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        if missing_packages:
            print()
            print("To install missing packages:")
            print(f"  pip install {' '.join(missing_packages)}")
            print("Or install all dependencies:")
            print("  pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

