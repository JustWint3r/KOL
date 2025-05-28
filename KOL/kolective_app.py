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
    """Normalize name by removing extension, converting to lowercase, and trimming spaces."""
    # Remove file extension if present
    name = name.lower().replace('.png', '')
    # Remove extra spaces and trim
    return ' '.join(name.split())

def clean_name_for_matching(name):
    """Clean name for matching by removing special characters and parentheses content."""
    # Remove content within parentheses
    name = re.sub(r'\([^)]*\)', '', name)
    # Remove special characters but keep Chinese characters
    name = re.sub(r'[^\w\s\u4e00-\u9fff]', '', name)
    # Remove extra spaces and convert to lowercase
    return ' '.join(name.lower().split())

def find_matching_photo(kol_name, photo_dict):
    """Find matching photo using exact or partial matching."""
    normalized_kol_name = normalize_name(kol_name)
    logger.info(f"\n=== Matching process for KOL: '{kol_name}' ===")
    logger.info(f"Normalized name: '{normalized_kol_name}'")
    
    # Try exact match first
    if normalized_kol_name in photo_dict:
        matched_file = photo_dict[normalized_kol_name]
        logger.info(f"✓ Found exact match: '{matched_file}'")
        return matched_file
        
    # Try partial match
    for norm_filename, original_filename in photo_dict.items():
        if normalized_kol_name in norm_filename or norm_filename in normalized_kol_name:
            logger.info(f"✓ Found partial match: '{original_filename}'")
            return original_filename
            
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
        # Read Excel file
        df = pd.read_excel(excel_path, engine='openpyxl')
        logger.info(f"Successfully read Excel file with {len(df)} rows")
        
        # Clean column names and data
        df.columns = df.columns.str.strip()
        df['KOL Nickname'] = df['KOL Nickname'].str.strip()
        df['Followers'] = df['Followers'].apply(parse_followers)
        df['Engagement Rate'] = df['Engagement Rate'].fillna("N/A")

        # Read all files from KOL_Picture directory
        photo_dir = os.path.join(base_dir, 'static', 'KOL_Picture')
        photo_files = [f for f in os.listdir(photo_dir) if f.lower().endswith('.png')]
        logger.info(f"\nFound {len(photo_files)} PNG files in {photo_dir}")
        
        # Build dictionary mapping normalized names to original filenames
        photo_dict = {normalize_name(f): f for f in photo_files}
        
        # Log the mapping for debugging
        logger.info("\nPhoto name mapping:")
        for norm_name, orig_name in photo_dict.items():
            logger.info(f"  '{norm_name}' -> '{orig_name}'")

        # Track used photos to prevent duplicates
        used_photos = set()
        
        # Process each KOL
        kols = []
        for _, row in df.iterrows():
            kol_nickname = row['KOL Nickname']
            available_photos = {k: v for k, v in photo_dict.items() if v not in used_photos}
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
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)     