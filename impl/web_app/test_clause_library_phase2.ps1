# Test Clause Library Phase 2 functionality
#
# This script runs comprehensive tests for Phase 2 enhancements:
# - Sample data loading
# - AI comparison accuracy
# - Vector search quality
# - Caching performance
# - Embedding optimization

Write-Host "Clause Library - Phase 2 Testing" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan

# Check if virtual environment exists
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Error: Virtual environment not found. Run venv.ps1 first." -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "`nActivating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Check if environment variables are set
if (-not $env:CAIG_COSMOSDB_NOSQL_URI) {
    Write-Host "Error: Environment variables not set. Run set-caig-env-vars.ps1 first." -ForegroundColor Red
    exit 1
}

# Run the test script
Write-Host "`nRunning Phase 2 tests..." -ForegroundColor Yellow
python test_clause_library_phase2.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nTests completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nTests failed with errors." -ForegroundColor Red
    exit $LASTEXITCODE
}
