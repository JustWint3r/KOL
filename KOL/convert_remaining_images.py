#!/usr/bin/env python3
"""
Convert remaining JPG/JPEG files to PNG format in the KOL_Picture directory
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
    print("✓ PIL/Pillow is available")
except ImportError:
    print("✗ PIL/Pillow not found. Installing...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        from PIL import Image
        print("✓ PIL/Pillow installed successfully")
    except Exception as e:
        print(f"✗ Failed to install PIL/Pillow: {e}")
        sys.exit(1)

def convert_image_to_png(input_path, output_path):
    """Convert an image file to PNG format"""
    try:
        with Image.open(input_path) as img:
            # Convert to RGB if necessary (for JPEG compatibility)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Keep transparency for images that have it
                img = img.convert('RGBA')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Save as PNG
            img.save(output_path, 'PNG', optimize=True)
        return True
    except Exception as e:
        print(f"  ✗ Error converting {input_path}: {e}")
        return False

def main():
    picture_dir = Path("static/KOL_Picture")
    
    if not picture_dir.exists():
        print(f"✗ Directory not found: {picture_dir}")
        return
    
    print("=== Converting remaining JPG/JPEG files to PNG ===")
    print(f"Working directory: {picture_dir}")
    
    # Find all JPG/JPEG files
    jpg_files = list(picture_dir.glob("*.jpg")) + list(picture_dir.glob("*.jpeg"))
    
    if not jpg_files:
        print("✓ No JPG/JPEG files found. All images are already in PNG format.")
        return
    
    print(f"Found {len(jpg_files)} JPG/JPEG files to convert")
    
    converted_count = 0
    failed_count = 0
    
    for jpg_file in jpg_files:
        # Create PNG filename
        png_file = jpg_file.with_suffix('.png')
        
        print(f"Converting: {jpg_file.name} -> {png_file.name}")
        
        if convert_image_to_png(jpg_file, png_file):
            # Remove original JPG file after successful conversion
            try:
                jpg_file.unlink()
                print(f"  ✓ Successfully converted and removed: {jpg_file.name}")
                converted_count += 1
            except Exception as e:
                print(f"  ⚠ Converted but failed to remove original: {e}")
                converted_count += 1
        else:
            failed_count += 1
    
    print(f"\n=== Conversion Complete ===")
    print(f"Successfully converted: {converted_count} files")
    print(f"Failed conversions: {failed_count} files")
    
    # Show final PNG count
    png_files = list(picture_dir.glob("*.png"))
    print(f"Total PNG files: {len(png_files)}")

if __name__ == "__main__":
    main() 