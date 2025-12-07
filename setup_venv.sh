#!/bin/bash

# Virtual Environment Setup Script for Linux/Mac
# Run this script to create and configure the virtual environment

echo "================================"
echo "Virtual Environment Setup"
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Python version
echo "Step 1: Checking Python version..."
python_version=$(python3 --version 2>&1 || python --version 2>&1)
echo "Python version: $python_version"

# Try python3 first, fallback to python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo -e "${RED}❌ Python not found. Please install Python 3.9+${NC}"
    exit 1
fi

# Check version
version_str=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
major=$(echo $version_str | cut -d. -f1)
minor=$(echo $version_str | cut -d. -f2)

if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 9 ]); then
    echo -e "${RED}❌ Python 3.9+ required. Current: $version_str${NC}"
    echo "Please install Python 3.9 or higher"
    exit 1
else
    echo -e "${GREEN}✅ Python version OK${NC}"
fi
echo ""

# Step 2: Check if venv module is available
echo "Step 2: Checking venv module..."
if $PYTHON_CMD -m venv --help &> /dev/null; then
    echo -e "${GREEN}✅ venv module available${NC}"
else
    echo -e "${RED}❌ venv module not available${NC}"
    exit 1
fi
echo ""

# Step 3: Create virtual environment
echo "Step 3: Creating virtual environment..."
if [ -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment already exists at .venv${NC}"
    read -p "Do you want to recreate it? (y/N): " overwrite
    if [ "$overwrite" = "y" ] || [ "$overwrite" = "Y" ]; then
        rm -rf .venv
        echo "Removed existing virtual environment"
    else
        echo -e "${GREEN}Using existing virtual environment${NC}"
        skip_creation=true
    fi
fi

if [ "$skip_creation" != "true" ]; then
    if $PYTHON_CMD -m venv .venv; then
        echo -e "${GREEN}✅ Virtual environment created in .venv${NC}"
    else
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        exit 1
    fi
fi
echo ""

# Step 4: Activate and upgrade pip
echo "Step 4: Upgrading pip..."
source .venv/bin/activate
python -m pip install --upgrade pip --quiet
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ pip upgraded${NC}"
else
    echo -e "${YELLOW}⚠️  Failed to upgrade pip${NC}"
fi
echo ""

# Step 5: Install dependencies
echo "Step 5: Installing dependencies from requirements.txt..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
    else
        echo -e "${RED}❌ Some dependencies failed to install${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠️  requirements.txt not found, skipping dependency installation${NC}"
fi
echo ""

# Step 6: Verify installation
echo "Step 6: Verifying installation..."
python -c "import pandas, streamlit, plotly; print('✅ Key packages imported successfully')" 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Verification passed${NC}"
else
    echo -e "${YELLOW}⚠️  Verification warning: Some packages may not be installed correctly${NC}"
fi
echo ""

# Summary
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "To activate the virtual environment, run:"
echo -e "${GREEN}  source .venv/bin/activate${NC}"
echo ""
echo "Or use the helper script:"
echo -e "${GREEN}  source activate.sh${NC}"
echo ""
echo "To deactivate, simply run:"
echo -e "${GREEN}  deactivate${NC}"
echo ""

