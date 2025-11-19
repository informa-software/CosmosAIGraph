# Setup HTTPS Certificate for Word Add-in Development
# This script generates a self-signed certificate for localhost

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Word Add-in HTTPS Certificate Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Set paths
$certName = "localhost"
$outputDir = "$PSScriptRoot\query-builder"
$pfxPassword = "WordAddin2025!"

Write-Host "Certificate will be created for: $certName" -ForegroundColor Green
Write-Host "Output directory: $outputDir" -ForegroundColor Green
Write-Host ""

# Create output directory if it doesn't exist
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
    Write-Host "Created directory: $outputDir" -ForegroundColor Green
}

try {
    # Generate self-signed certificate
    Write-Host "Generating self-signed certificate..." -ForegroundColor Yellow

    $cert = New-SelfSignedCertificate `
        -DnsName $certName `
        -CertStoreLocation "Cert:\LocalMachine\My" `
        -NotAfter (Get-Date).AddYears(5) `
        -FriendlyName "Word Add-in Development Certificate" `
        -KeyUsage DigitalSignature,KeyEncipherment `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.1") `
        -Provider "Microsoft Software Key Storage Provider"

    Write-Host "Certificate created successfully" -ForegroundColor Green
    Write-Host "  Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
    Write-Host ""

    # Export to PFX
    Write-Host "Exporting certificate to PFX..." -ForegroundColor Yellow
    $pfxPath = Join-Path $outputDir "localhost.pfx"
    $securePwd = ConvertTo-SecureString -String $pfxPassword -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $securePwd | Out-Null
    Write-Host "Exported to: $pfxPath" -ForegroundColor Green
    Write-Host ""

    # Check if OpenSSL is available
    $opensslPath = where.exe openssl 2>$null

    if ($opensslPath) {
        Write-Host "Converting to PEM format using OpenSSL..." -ForegroundColor Yellow

        # Export to CRT (certificate)
        $crtPath = Join-Path $outputDir "localhost.crt"
        & openssl pkcs12 -in $pfxPath -out $crtPath -clcerts -nokeys -password "pass:$pfxPassword" 2>$null
        Write-Host "Certificate file: $crtPath" -ForegroundColor Green

        # Export to KEY (private key)
        $keyPath = Join-Path $outputDir "localhost.key"
        & openssl pkcs12 -in $pfxPath -out $keyPath -nocerts -nodes -password "pass:$pfxPassword" 2>$null
        Write-Host "Private key file: $keyPath" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "OpenSSL not found. Installing via Chocolatey..." -ForegroundColor Yellow

        # Check if Chocolatey is installed
        $chocoPath = where.exe choco 2>$null

        if ($chocoPath) {
            choco install openssl -y

            # Retry conversion
            $opensslPath = where.exe openssl 2>$null
            if ($opensslPath) {
                Write-Host "Converting to PEM format..." -ForegroundColor Yellow

                $crtPath = Join-Path $outputDir "localhost.crt"
                & openssl pkcs12 -in $pfxPath -out $crtPath -clcerts -nokeys -password "pass:$pfxPassword" 2>$null
                Write-Host "Certificate file: $crtPath" -ForegroundColor Green

                $keyPath = Join-Path $outputDir "localhost.key"
                & openssl pkcs12 -in $pfxPath -out $keyPath -nocerts -nodes -password "pass:$pfxPassword" 2>$null
                Write-Host "Private key file: $keyPath" -ForegroundColor Green
                Write-Host ""
            }
        } else {
            Write-Host "OpenSSL is not installed and Chocolatey is not available." -ForegroundColor Yellow
            Write-Host "  Manual conversion required:" -ForegroundColor Yellow
            Write-Host "  1. Install OpenSSL from https://slproweb.com/products/Win32OpenSSL.html" -ForegroundColor Gray
            Write-Host "  2. Run the following commands:" -ForegroundColor Gray
            Write-Host "     openssl pkcs12 -in $pfxPath -out localhost.crt -clcerts -nokeys -password pass:$pfxPassword" -ForegroundColor Gray
            Write-Host "     openssl pkcs12 -in $pfxPath -out localhost.key -nocerts -nodes -password pass:$pfxPassword" -ForegroundColor Gray
            Write-Host ""
        }
    }

    # Trust the certificate
    Write-Host "Installing certificate to Trusted Root..." -ForegroundColor Yellow
    $store = New-Object System.Security.Cryptography.X509Certificates.X509Store("Root", "LocalMachine")
    $store.Open("ReadWrite")
    $store.Add($cert)
    $store.Close()
    Write-Host "Certificate installed to Trusted Root Certification Authorities" -ForegroundColor Green
    Write-Host ""

    # Summary
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "Certificate Setup Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Certificate files created in: $outputDir" -ForegroundColor White
    Write-Host "  - localhost.pfx (PFX format)" -ForegroundColor Gray

    if (Test-Path (Join-Path $outputDir "localhost.crt")) {
        Write-Host "  - localhost.crt (Certificate)" -ForegroundColor Gray
        Write-Host "  - localhost.key (Private Key)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "PFX Password: $pfxPassword" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Update package.json with SSL configuration" -ForegroundColor White
    Write-Host "2. Update angular.json for HTTPS serving" -ForegroundColor White
    Write-Host "3. Configure FastAPI backend with SSL" -ForegroundColor White
    Write-Host ""

} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create certificate" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
