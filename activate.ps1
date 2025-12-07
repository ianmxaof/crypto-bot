# Quick activation script for Windows PowerShell
# Usage: .\activate.ps1

if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & .\.venv\Scripts\Activate.ps1
} else {
    Write-Host "❌ Virtual environment not found. Run setup_venv.ps1 first." -ForegroundColor Red
    exit 1
}

