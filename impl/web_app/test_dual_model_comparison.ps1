# PowerShell script to run the dual-model comparison tests
# This script compares GPT-4.1 vs GPT-4.1-mini side-by-side

Write-Host "`n================================================================================"
Write-Host "DUAL-MODEL COMPARISON TEST SUITE"
Write-Host "================================================================================"
Write-Host "Comparing: GPT-4.1 (primary) vs GPT-4.1-mini (secondary)"
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

# Check if secondary model is configured
$envFile = ".env"
if (Test-Path $envFile) {
    $envContent = Get-Content $envFile -Raw
    if ($envContent -match 'CAIG_AZURE_OPENAI_URL_SECONDARY="https://your-secondary-resource\.openai\.azure\.com/"') {
        Write-Host ""
        Write-Host "WARNING: Secondary Azure OpenAI URL is not configured!"
        Write-Host ""
        Write-Host "Please update the following in .env file:"
        Write-Host "  CAIG_AZURE_OPENAI_URL_SECONDARY=`"https://your-actual-resource.openai.azure.com/`""
        Write-Host ""
        Write-Host "The test will detect this and exit gracefully."
        Write-Host ""
    }
}

# Run the test
Write-Host "Running dual-model comparison tests..."
Write-Host ""

python test_dual_model_comparison.py

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "================================================================================"
if ($exitCode -eq 0) {
    Write-Host "Tests completed successfully!"
    Write-Host ""
    Write-Host "RESULTS AVAILABLE IN:"
    Write-Host "  1. Console output above (summary metrics)"
    Write-Host "  2. dual_model_comparison_results.json (aggregate statistics)"
    Write-Host "  3. dual_model_comparison_details/ (full LLM responses for each test)"
    Write-Host ""
    Write-Host "NEXT STEPS:"
    Write-Host "  - Review DUAL_MODEL_OUTPUT_GUIDE.md for guidance on interpreting results"
    Write-Host "  - Compare individual test responses in dual_model_comparison_details/"
    Write-Host "  - Make model selection decision based on quality vs cost analysis"
} else {
    Write-Host "Tests failed with exit code: $exitCode"
}
Write-Host "================================================================================"
Write-Host ""

exit $exitCode
