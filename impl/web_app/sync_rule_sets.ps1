# Sync rule sets with rules - populate rule_ids arrays
# This script fixes the bidirectional relationship between rules and rule sets

$ErrorActionPreference = "Stop"
$baseUrl = "https://localhost:8000"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Rule Set Synchronization Script" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Disable SSL certificate validation for self-signed certificates
if (-not ([System.Management.Automation.PSTypeName]'ServerCertificateValidationCallback').Type) {
    Add-Type @"
        using System.Net;
        using System.Net.Security;
        using System.Security.Cryptography.X509Certificates;
        public class ServerCertificateValidationCallback {
            public static void Ignore() {
                ServicePointManager.ServerCertificateValidationCallback +=
                    delegate(object sender, X509Certificate certificate, X509Chain chain, SslPolicyErrors sslPolicyErrors) {
                        return true;
                    };
            }
        }
"@
}
[ServerCertificateValidationCallback]::Ignore()

# Step 1: Fetch all rules
Write-Host "Fetching all rules..." -ForegroundColor Yellow
try {
    $uri = "$baseUrl/api/compliance/rules?active=false"
    $rules = Invoke-RestMethod -Uri $uri -Method GET
    Write-Host "Found $($rules.Count) rules" -ForegroundColor Green
}
catch {
    Write-Host "ERROR: Failed to fetch rules" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Process each rule
$processedRules = 0
$processedAssignments = 0
$errorCount = 0

foreach ($rule in $rules) {
    if ($null -eq $rule.rule_set_ids -or $rule.rule_set_ids.Count -eq 0) {
        continue
    }

    Write-Host "Processing: $($rule.name)" -ForegroundColor Cyan
    Write-Host "  Rule ID: $($rule.id)" -ForegroundColor Gray
    Write-Host "  Rule Sets: $($rule.rule_set_ids -join ', ')" -ForegroundColor Gray

    $processedRules++

    foreach ($ruleSetId in $rule.rule_set_ids) {
        try {
            $uri = "$baseUrl/api/rule_sets/$ruleSetId/rules"
            $body = @{
                rule_ids = @($rule.id)
            }
            $json = $body | ConvertTo-Json -Depth 10

            $response = Invoke-RestMethod -Uri $uri -Method POST -Body $json -ContentType "application/json"

            Write-Host "    Added to rule set: $ruleSetId" -ForegroundColor Green
            $processedAssignments++
        }
        catch {
            Write-Host "    ERROR: Failed to add to rule set $ruleSetId" -ForegroundColor Red
            Write-Host "    $($_.Exception.Message)" -ForegroundColor Red
            $errorCount++
        }
    }

    Write-Host ""
}

# Step 3: Summary
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Synchronization Complete!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Rules processed: $processedRules" -ForegroundColor White
Write-Host "Assignments created: $processedAssignments" -ForegroundColor White
Write-Host "Errors: $errorCount" -ForegroundColor $(if ($errorCount -eq 0) { "Green" } else { "Yellow" })
Write-Host ""
Write-Host "Rule sets should now have populated rule_ids arrays" -ForegroundColor Cyan
