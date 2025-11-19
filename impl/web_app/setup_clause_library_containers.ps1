#!/usr/bin/env pwsh

# Setup script for Clause Library CosmosDB containers

Write-Host "Clause Library Container Setup" -ForegroundColor Cyan
Write-Host "==============================`n" -ForegroundColor Cyan

# Check if environment variables are loaded
if (-not $env:CAIG_COSMOSDB_NOSQL_URI) {
    Write-Host "Loading environment variables from set-caig-env-vars.ps1..." -ForegroundColor Yellow
    $envScript = Join-Path $PSScriptRoot ".." "set-caig-env-vars.ps1"
    if (Test-Path $envScript) {
        . $envScript
    } else {
        Write-Host "Error: set-caig-env-vars.ps1 not found" -ForegroundColor Red
        Write-Host "Please create this file from set-caig-env-vars-sample.ps1" -ForegroundColor Red
        exit 1
    }
}

# Activate virtual environment
$venvPath = Join-Path $PSScriptRoot "venv" "Scripts" "Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    . $venvPath
} else {
    Write-Host "Error: Virtual environment not found at $venvPath" -ForegroundColor Red
    Write-Host "Please run venv.ps1 first to create the virtual environment" -ForegroundColor Red
    exit 1
}

# Run setup script
Write-Host "`nRunning container setup script..." -ForegroundColor Green
python setup_clause_library_containers.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Setup complete!" -ForegroundColor Green
    Write-Host "`nNext steps:" -ForegroundColor Cyan
    Write-Host "  1. Restart the web application" -ForegroundColor White
    Write-Host "  2. Access the Clause Library API at http://localhost:8000/api/clause-library" -ForegroundColor White
} else {
    Write-Host "`n❌ Setup failed. Please check the error messages above." -ForegroundColor Red
    exit $LASTEXITCODE
}
