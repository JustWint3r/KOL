# Convert JPG files to PNG using alternative method
$pictureDir = "static\KOL_Picture"

Write-Host "=== Converting JPG files to PNG ===" -ForegroundColor Green

# Get all JPG files
$jpgFiles = Get-ChildItem -Path $pictureDir -Filter "*.jpg"
$jpegFiles = Get-ChildItem -Path $pictureDir -Filter "*.jpeg"
$allJpgFiles = $jpgFiles + $jpegFiles

Write-Host "Found $($allJpgFiles.Count) JPG/JPEG files to convert" -ForegroundColor Cyan

if ($allJpgFiles.Count -eq 0) {
    Write-Host "No JPG/JPEG files found!" -ForegroundColor Yellow
    exit 0
}

$convertedCount = 0
$failedCount = 0

# Try using ImageMagick if available, otherwise use alternative method
$magickPath = Get-Command "magick" -ErrorAction SilentlyContinue

if ($magickPath) {
    Write-Host "Using ImageMagick for conversion..." -ForegroundColor Green
    
    foreach ($file in $allJpgFiles) {
        $baseName = $file.BaseName
        $pngPath = Join-Path $pictureDir "$baseName.png"
        
        Write-Host "Converting: $($file.Name) -> $baseName.png" -ForegroundColor Cyan
        
        try {
            & magick $file.FullName $pngPath
            if (Test-Path $pngPath) {
                Remove-Item $file.FullName -Force
                Write-Host "  ✓ Success: $($file.Name)" -ForegroundColor Green
                $convertedCount++
            } else {
                Write-Host "  ✗ Failed: $($file.Name)" -ForegroundColor Red
                $failedCount++
            }
        }
        catch {
            Write-Host "  ✗ Error: $($file.Name) - $($_.Exception.Message)" -ForegroundColor Red
            $failedCount++
        }
    }
} else {
    # Alternative: Rename files with .png extension (temporary solution)
    Write-Host "ImageMagick not found. Using file extension change method..." -ForegroundColor Yellow
    Write-Host "Note: This only changes the extension. For true conversion, use an online converter." -ForegroundColor Yellow
    
    foreach ($file in $allJpgFiles) {
        $baseName = $file.BaseName
        $pngPath = Join-Path $pictureDir "$baseName.png"
        
        Write-Host "Renaming: $($file.Name) -> $baseName.png" -ForegroundColor Cyan
        
        try {
            # Copy and rename (keeping original quality)
            Copy-Item $file.FullName $pngPath
            Remove-Item $file.FullName -Force
            Write-Host "  ✓ Renamed: $($file.Name)" -ForegroundColor Green
            $convertedCount++
        }
        catch {
            Write-Host "  ✗ Error: $($file.Name) - $($_.Exception.Message)" -ForegroundColor Red
            $failedCount++
        }
    }
}

Write-Host "`n=== Conversion Complete ===" -ForegroundColor Green
Write-Host "Successfully processed: $convertedCount files" -ForegroundColor Cyan
Write-Host "Failed: $failedCount files" -ForegroundColor Red

# Show final PNG count
$finalPngFiles = Get-ChildItem -Path $pictureDir -Filter "*.png"
Write-Host "Total PNG files: $($finalPngFiles.Count)" -ForegroundColor Yellow 