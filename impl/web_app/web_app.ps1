# Start the web app, running within the hypercorn server.
# Entry point is web_app.py, 'app' is the FastAPI object.
# hypercorn enables restarting the app as the Python code changes.
# Chris Joakim, Microsoft, 2025

New-Item -ItemType Directory -Force -Path .\tmp | out-null

Write-Host 'deleting tmp\ files ...'
Remove-Item tmp\*.*

Write-Host 'activating the venv ...'
.\venv\Scripts\Activate.ps1

Write-Host '.env file contents ...'
Get-Content .env

# Check if SSL certificates exist
$certPath = "..\query-builder\localhost.crt"
$keyPath = "..\query-builder\localhost.key"

if ((Test-Path $certPath) -and (Test-Path $keyPath)) {
    Write-Host 'Starting web app with HTTPS...'
    hypercorn web_app:app --bind 127.0.0.1:8000 --workers 1 --certfile $certPath --keyfile $keyPath
} else {
    Write-Host 'SSL certificates not found. Starting with HTTP...'
    Write-Host 'Warning: Office Add-in requires HTTPS. Please run setup-https-cert.ps1'
    hypercorn web_app:app --bind 127.0.0.1:8000 --workers 1
} 