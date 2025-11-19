#!/usr/bin/env pwsh
# Setup model_usage container in CosmosDB

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Setting up model_usage container in CosmosDB" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    if (Test-Path "venv\Scripts\Activate.ps1") {
        . .\venv\Scripts\Activate.ps1
    } else {
        Write-Host "ERROR: Virtual environment not found. Please run venv.ps1 first." -ForegroundColor Red
        exit 1
    }
}

# Check if environment variables are set
if (-not $env:CAIG_COSMOSDB_NOSQL_URI) {
    Write-Host "ERROR: CAIG_COSMOSDB_NOSQL_URI environment variable not set" -ForegroundColor Red
    Write-Host "Please run set-caig-env-vars.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host "Running setup script..." -ForegroundColor Green
python setup_user_preferences_container.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "✓ Setup completed successfully!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "The following containers have been created:" -ForegroundColor Cyan
    Write-Host "  - user_preferences (for model preferences)" -ForegroundColor White
    Write-Host "  - model_usage (for usage analytics)" -ForegroundColor White
    Write-Host ""
    Write-Host "You can now use the Usage Analytics dashboard." -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "================================================" -ForegroundColor Red
    Write-Host "❌ Setup failed!" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please check the error messages above." -ForegroundColor Yellow
    exit 1
}
