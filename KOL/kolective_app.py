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

def find_matching_photo(kol_name, photo_files):
    """Find the matching photo using exact string matching."""
    logger.info(f"\n=== Matching process for KOL: '{kol_name}' ===")
    
    # Try exact match first
    exact_match = f"{kol_name}.png"
    logger.info(f"Looking for exact match: '{exact_match}'")
    
    if exact_match in photo_files:
        logger.info(f"✓ Found exact match: '{exact_match}'")
        return exact_match
        
    # If no exact match, log all files for debugging
    logger.info("No exact match found. Available files:")
    for f in photo_files:
        logger.info(f"  {f}")
    
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
        for idx, name in enumerate(df['KOL Nickname'].head(10)):
            logger.info(f"  {idx + 1}. '{name}'")
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
            logger.info(f"  '{f}'")
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