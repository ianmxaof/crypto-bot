# Virtual Environment Setup Script for Windows (PowerShell)
# Run this script to create and configure the virtual environment

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Virtual Environment Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check Python version
Write-Host "Step 1: Checking Python version..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python version: $pythonVersion" -ForegroundColor White
    
    # Extract version number
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
            Write-Host "❌ Python 3.9+ required. Current: $pythonVersion" -ForegroundColor Red
            Write-Host "Please install Python 3.9 or higher from https://www.python.org/" -ForegroundColor Yellow
            exit 1
        } else {
            Write-Host "✅ Python version OK" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠️  Could not parse Python version, continuing anyway..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Python not found. Please install Python 3.9+ from https://www.python.org/" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Check if venv module is available
Write-Host "Step 2: Checking venv module..." -ForegroundColor Yellow
try {
    python -m venv --help | Out-Null
    Write-Host "✅ venv module available" -ForegroundColor Green
} catch {
    Write-Host "❌ venv module not available" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Create virtual environment
Write-Host "Step 3: Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "⚠️  Virtual environment already exists at .venv" -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to recreate it? (y/N)"
    if ($overwrite -eq "y" -or $overwrite -eq "Y") {
        Remove-Item -Recurse -Force .venv
        Write-Host "Removed existing virtual environment" -ForegroundColor Yellow
    } else {
        Write-Host "Using existing virtual environment" -ForegroundColor Green
        $skipCreation = $true
    }
}

if (-not $skipCreation) {
    try {
        python -m venv .venv
        Write-Host "✅ Virtual environment created in .venv" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to create virtual environment: $_" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# Step 4: Activate and upgrade pip
Write-Host "Step 4: Upgrading pip..." -ForegroundColor Yellow
try {
    & .\.venv\Scripts\python.exe -m pip install --upgrade pip --quiet
    Write-Host "✅ pip upgraded" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Failed to upgrade pip: $_" -ForegroundColor Yellow
}
Write-Host ""

# Step 5: Install dependencies
Write-Host "Step 5: Installing dependencies from requirements.txt..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    try {
        & .\.venv\Scripts\pip.exe install -r requirements.txt
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Some dependencies failed to install" -ForegroundColor Red
            exit 1
        }
    } catch {
        Write-Host "❌ Failed to install dependencies: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "⚠️  requirements.txt not found, skipping dependency installation" -ForegroundColor Yellow
}
Write-Host ""

# Step 6: Verify installation
Write-Host "Step 6: Verifying installation..." -ForegroundColor Yellow
try {
    & .\.venv\Scripts\python.exe -c "import pandas, streamlit, plotly; print('✅ Key packages imported successfully')"
    Write-Host "✅ Verification passed" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Verification warning: Some packages may not be installed correctly" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To activate the virtual environment, run:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "Or use the helper script:" -ForegroundColor White
Write-Host "  .\activate.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "To deactivate, simply run:" -ForegroundColor White
Write-Host "  deactivate" -ForegroundColor Green
Write-Host ""
Write-Host "Note: If you get an execution policy error, run:" -ForegroundColor Yellow
Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
Write-Host ""

