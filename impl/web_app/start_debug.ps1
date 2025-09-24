# PowerShell script to start web app in debug mode
Write-Host "Starting Web App in Debug Mode..." -ForegroundColor Cyan
Write-Host "The app will wait for debugger attachment on port 5678" -ForegroundColor Yellow

# Set debug environment variable
$env:CAIG_WAIT_FOR_DEBUGGER = "true"

Write-Host "`nTo attach debugger:" -ForegroundColor Green
Write-Host "1. Open VS Code" -ForegroundColor White
Write-Host "2. Go to Run and Debug (Ctrl+Shift+D)" -ForegroundColor White
Write-Host "3. Select 'Python: Attach to Running Web App'" -ForegroundColor White
Write-Host "4. Press F5" -ForegroundColor White
Write-Host "`nStarting app now..." -ForegroundColor Cyan

# Activate virtual environment if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    & "venv\Scripts\Activate.ps1"
}

# Start the app
python web_app.py