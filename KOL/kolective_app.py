import pandas as pd
from flask import Flask, render_template, request, jsonify
import os
import re
import urllib.parse
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_followers(value):
    """Convert followers like '1.3M', '536k' to numeric."""
    try:
        value = str(value).lower().strip()
        if 'm' in value:
            return int(float(value.replace('m', '')) * 1_000_000)
        elif 'k' in value:
            return int(float(value.replace('k', '')) * 1_000)
        else:
            return int(value) if value.isdigit() else 0
    except:
        return 0

def clean_text(text):
    """Clean text by removing extra whitespace and newlines."""
    if pd.isna(text):
        return ""
    return str(text).strip().replace('\n', ' ')

def normalize_name(name):
    """Normalize name for comparison."""
    if pd.isna(name):
        return ""
    
    # Remove extra spaces and convert to lowercase
    name = ' '.join(str(name).strip().split())
    
    # Log the original and normalized name
    logger.info(f"Normalizing name: '{name}'")
    return name

def clean_name_for_matching(name):
    """Clean name for matching by removing special characters and parentheses content."""
    # Remove content within parentheses
    name = re.sub(r'\([^)]*\)', '', name)
    # Remove special characters but keep Chinese characters
    name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name)
    # Remove extra spaces and convert to lowercase
    return ' '.join(name.lower().split())

def find_matching_photo(kol_name, photo_files):
    """Find the matching photo using flexible matching strategies."""
    logger.info(f"\n=== Matching process for KOL: '{kol_name}' ===")
    
    # Create a case-insensitive mapping of filenames
    filename_map = {clean_name_for_matching(f.replace('.png', '')): f for f in photo_files}
    
    # Try different variations of the name
    cleaned_name = clean_name_for_matching(kol_name)
    logger.info(f"Cleaned name for matching: '{cleaned_name}'")
    
    # Try exact match first
    if cleaned_name in filename_map:
        actual_filename = filename_map[cleaned_name]
        logger.info(f"✓ Found exact match: '{actual_filename}'")
        return actual_filename
    
    # Try matching parts of the name
    name_parts = cleaned_name.split()
    if len(name_parts) > 1:
        logger.info("Trying partial name matches...")
        for stored_name, filename in filename_map.items():
            # Check if all parts of the cleaned name are in the stored name
            if all(part in stored_name for part in name_parts):
                logger.info(f"✓ Found partial match: '{filename}'")
                return filename
            # Check if all parts of the stored name are in the cleaned name
            stored_parts = stored_name.split()
            if all(part in cleaned_name for part in stored_parts):
                logger.info(f"✓ Found reverse partial match: '{filename}'")
                return filename
    
    # If no match found, log similar names for debugging
    logger.info("No match found. Similar files:")
    for stored_name, filename in filename_map.items():
        # Show files that share at least one word with the search term
        if any(part in stored_name for part in name_parts):
            logger.info(f"  '{filename}' (cleaned: '{stored_name}')")
    
    logger.warning(f"✗ No match found for '{kol_name}'")
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/kols')
def api_kols():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'List.xlsx')
    logger.info(f"Reading from: {excel_path}")

    try:
        df = pd.read_excel(excel_path, engine='openpyxl')
        logger.info(f"Successfully read Excel file with {len(df)} rows")
        
        # Log first few KOL names for debugging
        logger.info("First few KOL names from Excel:")
        for idx, name in enumerate(df['KOL Nickname'].head()):
            logger.info(f"  {idx + 1}. '{name}' -> cleaned: '{clean_name_for_matching(name)}'")
    except Exception as e:
        logger.error(f"Error reading Excel: {str(e)}")
        return jsonify({"error": str(e)}), 500

    df.columns = df.columns.str.strip()
    
    # Clean the data - only remove leading/trailing whitespace
    df['KOL Nickname'] = df['KOL Nickname'].str.strip()
    df['Followers'] = df['Followers'].apply(parse_followers)
    df['Engagement Rate'] = df['Engagement Rate'].fillna("N/A")

    photo_dir = os.path.join(base_dir, 'static', 'KOL_Picture')
    
    try:
        # Get all PNG files in the directory
        photo_files = [f for f in os.listdir(photo_dir) if f.lower().endswith('.png')]
        logger.info(f"\nFound {len(photo_files)} PNG files in {photo_dir}")
        
        # Log all image files for debugging
        logger.info("All available image files:")
        for f in sorted(photo_files):
            logger.info(f"  '{f}' -> cleaned: '{clean_name_for_matching(f)}'")
            
    except Exception as e:
        logger.error(f"Error reading photo directory: {str(e)}")
        return jsonify({"error": str(e)}), 500

    # Track used photos to prevent duplicates
    used_photos = set()
    
    kols = []
    for _, row in df.iterrows():
        kol_nickname = row['KOL Nickname']
        available_photos = [f for f in photo_files if f not in used_photos]
        photo_file = find_matching_photo(kol_nickname, available_photos)
        
        if photo_file:
            photo_url = f'/static/KOL_Picture/{urllib.parse.quote(photo_file)}'
            used_photos.add(photo_file)
            logger.info(f"✓ Successfully matched '{kol_nickname}' -> '{photo_file}'")
        else:
            photo_url = 'https://via.placeholder.com/300x400?text=No+Photo'
            logger.warning(f"✗ No photo found for: '{kol_nickname}'")
            
        kol = row.to_dict()
        kol['Photo'] = photo_url
        kols.append(kol)

    return jsonify(kols)

if __name__ == '__main__':
    app.run(debug=True)     