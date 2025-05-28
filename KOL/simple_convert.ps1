# Simple script to rename JPG files to PNG format
$pictureDir = "static\KOL_Picture"

Write-Host "=== Converting JPG files to PNG format ===" -ForegroundColor Green

# Get all JPG and JPEG files
$jpgFiles = Get-ChildItem -Path $pictureDir -Filter "*.jpg"
$jpegFiles = Get-ChildItem -Path $pictureDir -Filter "*.jpeg"
$allFiles = $jpgFiles + $jpegFiles

Write-Host "Found $($allFiles.Count) files to convert" -ForegroundColor Cyan

$successCount = 0
$failedCount = 0

foreach ($file in $allFiles) {
    $baseName = $file.BaseName
    $newName = "$baseName.png"
    $newPath = Join-Path $pictureDir $newName
    
    Write-Host "Converting: $($file.Name) -> $newName" -ForegroundColor Yellow
    
    try {
        # Rename the file to have .png extension
        Rename-Item -Path $file.FullName -NewName $newName
        Write-Host "  ✓ Success: $($file.Name)" -ForegroundColor Green
        $successCount++
    }
    catch {
        Write-Host "  ✗ Failed: $($file.Name) - $($_.Exception.Message)" -ForegroundColor Red
        $failedCount++
    }
}

Write-Host "`n=== Conversion Complete ===" -ForegroundColor Green
Write-Host "Successfully converted: $successCount files" -ForegroundColor Cyan
Write-Host "Failed: $failedCount files" -ForegroundColor Red

# Show final count
$pngFiles = Get-ChildItem -Path $pictureDir -Filter "*.png"
Write-Host "Total PNG files: $($pngFiles.Count)" -ForegroundColor Yellow 