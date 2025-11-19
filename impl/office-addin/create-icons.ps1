# Create PNG icon files for Office Add-in
Add-Type -AssemblyName System.Drawing

$iconSizes = @(16, 32, 64, 80)
$assetsPath = "public\assets"

# Create assets directory if it doesn't exist
if (-not (Test-Path $assetsPath)) {
    New-Item -ItemType Directory -Path $assetsPath | Out-Null
}

foreach ($size in $iconSizes) {
    # Create bitmap
    $bitmap = New-Object System.Drawing.Bitmap($size, $size)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)

    # Set high quality rendering
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAlias

    # Background color (Microsoft blue)
    $backgroundColor = [System.Drawing.Color]::FromArgb(0, 120, 212)
    $graphics.Clear($backgroundColor)

    # Draw "C" text
    $font = New-Object System.Drawing.Font("Arial", ($size * 0.6), [System.Drawing.FontStyle]::Bold)
    $brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::White)

    # Center the text
    $format = New-Object System.Drawing.StringFormat
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center

    $rect = New-Object System.Drawing.RectangleF(0, 0, $size, $size)
    $graphics.DrawString("C", $font, $brush, $rect, $format)

    # Save PNG
    $outputPath = Join-Path $assetsPath "icon-$size.png"
    $bitmap.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)

    Write-Host "Created $outputPath"

    # Cleanup
    $graphics.Dispose()
    $bitmap.Dispose()
    $font.Dispose()
    $brush.Dispose()
}

Write-Host "`nAll icon files created successfully!"
