from PIL import Image
import os

def convert_to_png():
    # Path to the KOL_Picture directory
    directory = os.path.join(os.path.dirname(__file__), 'static', 'KOL_Picture')
    
    # Get all files in the directory
    files = os.listdir(directory)
    
    # Counter for converted files
    converted = 0
    
    for filename in files:
        # Get the file extension
        file_ext = os.path.splitext(filename)[1].lower()
        
        # Only process image files that aren't already PNG
        if file_ext in ['.jpg', '.jpeg']:
            try:
                # Full path to the original file
                file_path = os.path.join(directory, filename)
                
                # Create the new PNG filename
                new_filename = os.path.splitext(filename)[0] + '.png'
                new_file_path = os.path.join(directory, new_filename)
                
                # Open and convert the image
                with Image.open(file_path) as img:
                    # Convert to RGB if necessary (in case of RGBA)
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    
                    # Save as PNG
                    img.save(new_file_path, 'PNG', quality=95)
                
                # Remove the original file
                os.remove(file_path)
                
                print(f"Converted: {filename} -> {new_filename}")
                converted += 1
                
            except Exception as e:
                print(f"Error converting {filename}: {str(e)}")
    
    print(f"\nConversion complete! Converted {converted} files to PNG format.")

if __name__ == '__main__':
    convert_to_png() 