# PowerShell script to setup user_preferences container

Write-Host "`n================================================================================"
Write-Host "USER PREFERENCES CONTAINER SETUP"
Write-Host "================================================================================"
Write-Host ""

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "ERROR: Virtual environment not found!"
    Write-Host "Please run venv.ps1 first to create the virtual environment."
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..."
& "venv\Scripts\Activate.ps1"

# Run the setup script
python setup_user_preferences_container.py

$exitCode = $LASTEXITCODE

Write-Host ""
exit $exitCode
