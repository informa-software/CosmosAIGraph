# Fix rule set synchronization
# This script syncs existing rules with their rule sets to populate the rule_ids arrays

$baseUrl = "https://localhost:8000"

Write-Host "Fetching all rules..." -ForegroundColor Cyan

# Get all rules (including inactive ones)
try {
    $rules = Invoke-RestMethod -Uri "$baseUrl/api/compliance/rules?active=false" -Method GET -SkipCertificateCheck
}
catch {
    Write-Host "Failed to fetch rules: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Found $($rules.Count) rules to process" -ForegroundColor Green
Write-Host ""

$processedCount = 0
$successCount = 0
$errorCount = 0

foreach ($rule in $rules) {
    if ($rule.rule_set_ids -and $rule.rule_set_ids.Count -gt 0) {
        Write-Host "Processing: $($rule.name)" -ForegroundColor Yellow
        Write-Host "  Rule ID: $($rule.id)"
        Write-Host "  Rule Sets: $($rule.rule_set_ids -join ', ')"

        foreach ($ruleSetId in $rule.rule_set_ids) {
            try {
                $body = @{ rule_ids = @($rule.id) } | ConvertTo-Json
                
                $response = Invoke-RestMethod -Uri "$baseUrl/api/rule_sets/$ruleSetId/rules" -Method POST -Body $body -ContentType "application/json" -SkipCertificateCheck
                
                Write-Host "  Success: Added to rule set $ruleSetId" -ForegroundColor Green
                $successCount++
            }
            catch {
                Write-Host "  Error: Failed to add to rule set $ruleSetId" -ForegroundColor Red
                $errorCount++
            }
        }

        $processedCount++
        Write-Host ""
    }
}

Write-Host "========================================"
Write-Host "Sync Complete!"
Write-Host "  Rules processed: $processedCount"
Write-Host "  Successful syncs: $successCount"
Write-Host "  Errors: $errorCount"
