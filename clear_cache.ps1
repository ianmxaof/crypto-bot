# Clear Python cache files to fix import issues

Write-Host "🧹 Clearing Python cache files..." -ForegroundColor Yellow

# Remove all __pycache__ directories
Get-ChildItem -Path . -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue | 
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Remove .pyc files
Get-ChildItem -Path . -Filter "*.pyc" -Recurse -ErrorAction SilentlyContinue | 
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "✅ Cache cleared!" -ForegroundColor Green
Write-Host ""
Write-Host "Now restart your Streamlit app:" -ForegroundColor Cyan
Write-Host "  1. Stop Streamlit (Ctrl+C if running)" -ForegroundColor White
Write-Host "  2. Run: python run_dashboard.py" -ForegroundColor White

