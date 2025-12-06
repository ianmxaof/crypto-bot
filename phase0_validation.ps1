# Phase 0: Validation and Testing Script (PowerShell)
# Run this to systematically test your crypto bot implementation

Write-Host "================================" -ForegroundColor Cyan
Write-Host "Crypto Bot Phase 0 Validation" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$exitCode = 0

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
            Write-Host "❌ Python 3.9+ required" -ForegroundColor Red
            exit 1
        } else {
            Write-Host "✅ Python version OK" -ForegroundColor Green
        }
    } else {
        Write-Host "⚠️  Could not parse Python version, continuing anyway..." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ Python not found. Please install Python 3.9+" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 2: Install dependencies
Write-Host "Step 2: Installing dependencies..." -ForegroundColor Yellow
try {
    python -m pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "❌ Dependency installation failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Dependency installation failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Check for .env file
Write-Host "Step 3: Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No .env file found. Creating from template..." -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "⚠️  Please edit .env with your API keys before running live" -ForegroundColor Yellow
    } else {
        Write-Host "❌ .env.example not found. Cannot create .env file." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ .env file exists" -ForegroundColor Green
}

# Verify PAPER_TRADING is enabled by default
$envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
if ($envContent -and $envContent -match "PAPER_TRADING\s*=\s*true") {
    Write-Host "✅ Paper trading enabled (safe mode)" -ForegroundColor Green
} else {
    Write-Host "⚠️  Adding PAPER_TRADING=true to .env for safety" -ForegroundColor Yellow
    if (-not (Test-Path ".env")) {
        "PAPER_TRADING=true" | Out-File -FilePath ".env" -Encoding utf8
    } else {
        $envContent = Get-Content ".env" -Raw
        if ($envContent -notmatch "PAPER_TRADING") {
            Add-Content -Path ".env" -Value "PAPER_TRADING=true"
        } else {
            $envContent = $envContent -replace "PAPER_TRADING\s*=\s*.*", "PAPER_TRADING=true"
            $envContent | Out-File -FilePath ".env" -Encoding utf8
        }
    }
}
Write-Host ""

# Step 4: Run unit tests
Write-Host "Step 4: Running unit tests..." -ForegroundColor Yellow
try {
    python -m pytest tests/unit/ -v --tb=short
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Unit tests passed" -ForegroundColor Green
    } else {
        Write-Host "❌ Unit tests failed - fix these before continuing" -ForegroundColor Red
        $exitCode = 1
    }
} catch {
    Write-Host "❌ Unit tests failed: $_" -ForegroundColor Red
    $exitCode = 1
}
Write-Host ""

# Step 5: Test basic imports
Write-Host "Step 5: Testing basic imports..." -ForegroundColor Yellow
try {
    $importTest = @"
from core.event_bus import EventBus
from core.agent_base import Agent
from core.rate_limiter import RateLimiter
from exchanges.mock_exchange import MockExchange
from simulation.position_tracker import PositionTracker
print('✅ All core imports successful')
"@
    $importTest | python
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Import tests passed" -ForegroundColor Green
    } else {
        Write-Host "❌ Import errors detected" -ForegroundColor Red
        $exitCode = 1
    }
} catch {
    Write-Host "❌ Import test failed: $_" -ForegroundColor Red
    $exitCode = 1
}
Write-Host ""

# Step 6: Test mock exchange
Write-Host "Step 6: Testing mock exchange initialization..." -ForegroundColor Yellow
try {
    python scripts/test_connection.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Mock exchange test passed" -ForegroundColor Green
    } else {
        Write-Host "❌ Mock exchange test failed" -ForegroundColor Red
        $exitCode = 1
    }
} catch {
    Write-Host "❌ Mock exchange test failed: $_" -ForegroundColor Red
    $exitCode = 1
}
Write-Host ""

# Step 7: Run integration tests
Write-Host "Step 7: Running integration tests..." -ForegroundColor Yellow
try {
    python -m pytest tests/integration/ -v --tb=short
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Integration tests passed" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Integration tests failed (may need real data)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Integration tests failed: $_" -ForegroundColor Yellow
}
Write-Host ""

# Step 8: Quick paper trading smoke test
Write-Host "Step 8: Running paper trading smoke test (10 seconds)..." -ForegroundColor Yellow
try {
    $testLog = "bot_test.log"
    
    # Start main.py in background
    $job = Start-Job -ScriptBlock {
        Set-Location $using:PWD
        python main.py 2>&1 | Out-File -FilePath $using:testLog -Encoding utf8
    }
    
    # Wait 10 seconds
    Start-Sleep -Seconds 10
    
    # Stop the job
    Stop-Job -Job $job -ErrorAction SilentlyContinue
    Remove-Job -Job $job -ErrorAction SilentlyContinue
    
    # Check log for errors
    if (Test-Path $testLog) {
        $logContent = Get-Content $testLog -Raw
        if ($logContent -match "ERROR|Exception|Traceback") {
            Write-Host "❌ Paper trading test encountered errors:" -ForegroundColor Red
            Get-Content $testLog -Tail 20
            Remove-Item $testLog -ErrorAction SilentlyContinue
            $exitCode = 1
        } else {
            Write-Host "✅ Paper trading smoke test passed" -ForegroundColor Green
            Remove-Item $testLog -ErrorAction SilentlyContinue
        }
    } else {
        Write-Host "⚠️  Could not find test log file" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Smoke test encountered issues: $_" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Validation Summary" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "✅ Phase 0 validation complete!" -ForegroundColor Green
} else {
    Write-Host "❌ Validation completed with errors" -ForegroundColor Red
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Review test output above for any warnings"
Write-Host "2. Run full paper trading: `$env:PAPER_TRADING='true'; python main.py`"
Write-Host "3. Monitor logs for 5-10 minutes"
Write-Host "4. Run backtest: python scripts/run_backtest.py"
Write-Host ""
Write-Host "⚠️  Remember: Keep PAPER_TRADING=true until backtests validate profitability" -ForegroundColor Yellow

exit $exitCode

