Write-Host "Converting JPG files to PNG format..." -ForegroundColor Green

cd "static\KOL_Picture"

$jpgFiles = Get-ChildItem -Filter "*.jpg"
$jpegFiles = Get-ChildItem -Filter "*.jpeg"
$allFiles = $jpgFiles + $jpegFiles

Write-Host "Found $($allFiles.Count) files to convert"

foreach ($file in $allFiles) {
    $newName = $file.BaseName + ".png"
    Write-Host "Converting: $($file.Name) -> $newName"
    Rename-Item $file.Name $newName
}

$pngCount = (Get-ChildItem -Filter "*.png").Count
Write-Host "Conversion complete! Total PNG files: $pngCount" -ForegroundColor Green 