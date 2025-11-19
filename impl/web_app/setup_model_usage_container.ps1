# PowerShell script to setup model_usage container
# Run this script from the web_app directory

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup model_usage Container" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
} else {
    Write-Host "Warning: Virtual environment not found" -ForegroundColor Red
    Write-Host "Run venv.ps1 first to create the virtual environment" -ForegroundColor Red
    exit 1
}

# Check if environment variables are set
if (-not $env:CAIG_COSMOSDB_NOSQL_URI) {
    Write-Host "Error: Environment variables not set" -ForegroundColor Red
    Write-Host "Run set-caig-env-vars.ps1 first" -ForegroundColor Red
    exit 1
}

Write-Host "Running setup script..." -ForegroundColor Yellow
python setup_model_usage_container.py

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
