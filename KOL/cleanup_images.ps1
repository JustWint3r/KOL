# KOL Picture Cleanup Script
# This script removes duplicate images (keeping PNG versions) and converts remaining JPG/JPEG files to PNG

$pictureDir = "static\KOL_Picture"
$convertedCount = 0
$removedCount = 0

Write-Host "=== KOL Picture Cleanup Script ===" -ForegroundColor Green
Write-Host "Working directory: $pictureDir" -ForegroundColor Yellow

# Check if directory exists
if (-not (Test-Path $pictureDir)) {
    Write-Host "Error: Directory $pictureDir not found!" -ForegroundColor Red
    exit 1
}

# Get all image files
$allFiles = Get-ChildItem -Path $pictureDir -File | Where-Object { $_.Extension -match '\.(jpg|jpeg|png)$' }

Write-Host "`nFound $($allFiles.Count) image files total" -ForegroundColor Cyan

# Group files by base name (without extension)
$fileGroups = $allFiles | Group-Object { $_.BaseName }

Write-Host "`nProcessing duplicates and conversions..." -ForegroundColor Yellow

foreach ($group in $fileGroups) {
    $baseName = $group.Name
    $files = $group.Group
    
    # Check if we have multiple files with the same base name
    if ($files.Count -gt 1) {
        Write-Host "`nProcessing duplicates for: $baseName" -ForegroundColor Cyan
        
        # Check if PNG version exists
        $pngFile = $files | Where-Object { $_.Extension -eq '.png' }
        $otherFiles = $files | Where-Object { $_.Extension -ne '.png' }
        
        if ($pngFile -and $otherFiles) {
            # PNG exists, remove other formats
            foreach ($file in $otherFiles) {
                Write-Host "  Removing duplicate: $($file.Name)" -ForegroundColor Red
                Remove-Item -Path $file.FullName -Force
                $removedCount++
            }
        }
        elseif (-not $pngFile -and $otherFiles) {
            # No PNG exists, convert the first non-PNG file and remove others
            $fileToConvert = $otherFiles[0]
            $filesToRemove = $otherFiles[1..($otherFiles.Count-1)]
            
            # Convert first file to PNG
            Write-Host "  Converting: $($fileToConvert.Name) -> $baseName.png" -ForegroundColor Green
            try {
                # Use .NET System.Drawing for conversion
                Add-Type -AssemblyName System.Drawing
                $image = [System.Drawing.Image]::FromFile($fileToConvert.FullName)
                $pngPath = Join-Path $pictureDir "$baseName.png"
                $image.Save($pngPath, [System.Drawing.Imaging.ImageFormat]::Png)
                $image.Dispose()
                
                # Remove original file
                Remove-Item -Path $fileToConvert.FullName -Force
                Write-Host "  Successfully converted: $($fileToConvert.Name)" -ForegroundColor Green
                $convertedCount++
            }
            catch {
                Write-Host "  Error converting $($fileToConvert.Name): $($_.Exception.Message)" -ForegroundColor Red
            }
            
            # Remove other duplicate files
            foreach ($file in $filesToRemove) {
                Write-Host "  Removing duplicate: $($file.Name)" -ForegroundColor Red
                Remove-Item -Path $file.FullName -Force
                $removedCount++
            }
        }
    }
    elseif ($files.Count -eq 1) {
        # Single file, convert to PNG if not already PNG
        $file = $files[0]
        if ($file.Extension -ne '.png') {
            Write-Host "`nConverting single file: $($file.Name) -> $baseName.png" -ForegroundColor Green
            try {
                # Use .NET System.Drawing for conversion
                Add-Type -AssemblyName System.Drawing
                $image = [System.Drawing.Image]::FromFile($file.FullName)
                $pngPath = Join-Path $pictureDir "$baseName.png"
                $image.Save($pngPath, [System.Drawing.Imaging.ImageFormat]::Png)
                $image.Dispose()
                
                # Remove original file
                Remove-Item -Path $file.FullName -Force
                Write-Host "  Successfully converted: $($file.Name)" -ForegroundColor Green
                $convertedCount++
            }
            catch {
                Write-Host "  Error converting $($file.Name): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    }
}

# Final summary
Write-Host "`n=== Cleanup Complete ===" -ForegroundColor Green
Write-Host "Files converted to PNG: $convertedCount" -ForegroundColor Cyan
Write-Host "Duplicate files removed: $removedCount" -ForegroundColor Red

# Show final file count
$finalFiles = Get-ChildItem -Path $pictureDir -File | Where-Object { $_.Extension -eq '.png' }
Write-Host "Total PNG files remaining: $($finalFiles.Count)" -ForegroundColor Yellow

Write-Host "`nCleanup completed successfully!" -ForegroundColor Green 