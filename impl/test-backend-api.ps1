# Test Backend API for Contract Query Builder

Write-Host "`nTesting Backend API Endpoints" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan
Write-Host ""

$baseUrl = "http://localhost:8000/api"

# Test 1: Get Contractor Parties
Write-Host "Test 1: Getting Contractor Parties..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/entities/contractor_parties" -Method Get
    Write-Host "✓ Success! Found $($response.total) contractor parties" -ForegroundColor Green
    if ($response.entities -and $response.entities.Count -gt 0) {
        Write-Host "  Sample: $($response.entities[0].displayName) (normalized: $($response.entities[0].normalizedName))" -ForegroundColor Gray
        Write-Host "  Contracts: $($response.entities[0].contractCount), Value: `$$($response.entities[0].totalValue)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 2: Get Contracting Parties
Write-Host "Test 2: Getting Contracting Parties..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/entities/contracting_parties" -Method Get
    Write-Host "✓ Success! Found $($response.total) contracting parties" -ForegroundColor Green
    if ($response.entities -and $response.entities.Count -gt 0) {
        Write-Host "  Sample: $($response.entities[0].displayName)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 3: Search Entities
Write-Host "Test 3: Searching for 'west'..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/entities/search?q=west" -Method Get
    Write-Host "✓ Success! Found $($response.total) results" -ForegroundColor Green
    foreach ($group in $response.results) {
        Write-Host "  $($group.displayName): $($group.entities.Count) entities" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""

# Test 4: Get Query Templates
Write-Host "Test 4: Getting Query Templates..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/query-templates" -Method Get
    Write-Host "✓ Success! Found $($response.templates.Count) templates" -ForegroundColor Green
    foreach ($template in $response.templates) {
        Write-Host "  - $($template.name): $($template.description)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "API Testing Complete!" -ForegroundColor Cyan
Write-Host ""

# Instructions
Write-Host "Next Steps:" -ForegroundColor Magenta
Write-Host "1. Ensure web_app.py is running with CAIG_GRAPH_MODE=contracts"
Write-Host "2. Load contract data using: python main_contracts.py load_contracts"
Write-Host "3. Angular app should now connect to real backend data"
Write-Host ""