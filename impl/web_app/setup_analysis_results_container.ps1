# Setup Analysis Results Container (PowerShell Wrapper)
# Creates the CosmosDB container needed for analysis results storage

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Analysis Results Container Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Virtual environment not detected" -ForegroundColor Yellow
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow

    if (Test-Path "venv\Scripts\Activate.ps1") {
        . .\venv\Scripts\Activate.ps1
    } else {
        Write-Host "❌ Virtual environment not found. Please run venv.ps1 first" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✅ Virtual environment active" -ForegroundColor Green
Write-Host ""

# Check if environment variables are set
if (-not $env:CAIG_COSMOSDB_NOSQL_URI) {
    Write-Host "❌ CAIG_COSMOSDB_NOSQL_URI not set" -ForegroundColor Red
    Write-Host "Please run set-caig-env-vars.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Environment variables configured" -ForegroundColor Green
Write-Host ""

# Run the Python setup script
Write-Host "Running container setup..." -ForegroundColor Cyan
Write-Host ""

python setup_analysis_results_container.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ Setup completed successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "❌ Setup failed" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
}
