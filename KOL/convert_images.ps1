# Get the directory path
$directory = Join-Path $PSScriptRoot "static\KOL_Picture"

# Load required assemblies
Add-Type -AssemblyName System.Drawing

# Counter for converted files
$converted = 0

# Get all JPG and JPEG files
Get-ChildItem -Path $directory -Filter "*.jp*g" | ForEach-Object {
    try {
        $sourcePath = $_.FullName
        $targetPath = Join-Path $directory ($_.BaseName + ".png")
        
        Write-Host "Converting: $($_.Name) -> $($_.BaseName).png"
        
        # Load the image
        $image = [System.Drawing.Image]::FromFile($sourcePath)
        
        # Save as PNG
        $image.Save($targetPath, [System.Drawing.Imaging.ImageFormat]::Png)
        
        # Dispose of the image object
        $image.Dispose()
        
        # Delete the original file
        Remove-Item $sourcePath
        
        $converted++
        Write-Host "Successfully converted: $($_.Name)"
    }
    catch {
        Write-Host "Error converting $($_.Name): $_"
    }
}

Write-Host "`nConversion complete! Converted $converted files to PNG format." 