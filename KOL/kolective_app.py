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
    """Normalize name for comparison by handling mixed-language names carefully."""
    if pd.isna(name):
        return ""
    
    # Convert to lowercase and remove extra spaces
    name = str(name).strip()
    
    # Create two versions: one with spaces and one without
    spaced_version = ' '.join(name.split())  # Normalize spaces
    no_space_version = ''.join(name.split())  # Remove all spaces
    
    return (spaced_version, no_space_version)

def find_matching_photo(kol_name, photo_files, original_files, used_photos):
    """Find the best matching photo for a KOL name."""
    kol_spaced, kol_no_space = normalize_name(kol_name)
    logger.info(f"\nMatching process for KOL: '{kol_name}'")
    logger.info(f"Normalized versions - Spaced: '{kol_spaced}', No space: '{kol_no_space}'")
    
    # First try: Exact match with original filename (case-sensitive)
    for filename in original_files.values():
        if filename not in used_photos:
            base_name = os.path.splitext(filename)[0]
            if kol_name == base_name or kol_spaced == base_name or kol_no_space == base_name:
                logger.info(f"✓ Found exact case-sensitive match: '{filename}'")
                return filename
    
    # Second try: Case-insensitive exact match
    for filename in original_files.values():
        if filename not in used_photos:
            base_name = os.path.splitext(filename)[0]
            if kol_name.lower() == base_name.lower() or \
               kol_spaced.lower() == base_name.lower() or \
               kol_no_space.lower() == base_name.lower():
                logger.info(f"✓ Found case-insensitive match: '{filename}'")
                return filename
    
    # Third try: Partial match for mixed-language names
    best_match = None
    best_match_score = 0
    
    for filename in original_files.values():
        if filename in used_photos:
            continue
            
        base_name = os.path.splitext(filename)[0]
        file_spaced, file_no_space = normalize_name(base_name)
        
        # Check if both names contain Chinese characters
        kol_has_chinese = any('\u4e00' <= char <= '\u9fff' for char in kol_name)
        file_has_chinese = any('\u4e00' <= char <= '\u9fff' for char in base_name)
        
        # If one has Chinese and the other doesn't, skip
        if kol_has_chinese != file_has_chinese:
            continue
        
        # Calculate match score
        score = 0
        if kol_has_chinese:
            # For Chinese names, require exact match of Chinese characters
            kol_chinese = ''.join(char for char in kol_name if '\u4e00' <= char <= '\u9fff')
            file_chinese = ''.join(char for char in base_name if '\u4e00' <= char <= '\u9fff')
            if kol_chinese == file_chinese:
                score = 1.0
        else:
            # For non-Chinese names, use string similarity
            score = max(
                len(set(kol_no_space.lower()) & set(file_no_space.lower())) / max(len(kol_no_space), len(file_no_space)),
                len(set(kol_spaced.lower()) & set(file_spaced.lower())) / max(len(kol_spaced), len(file_spaced))
            )
        
        if score > best_match_score and score >= 0.8:  # Require 80% match
            best_match = filename
            best_match_score = score
            logger.debug(f"New best match: '{filename}' with score {score:.2f}")

    if best_match:
        logger.info(f"✓ Found best match: '{best_match}' (score: {best_match_score:.2f})")
        return best_match

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
    except FileNotFoundError:
        logger.error("List.xlsx not found")
        return jsonify({"error": "List.xlsx not found"}), 404
    except Exception as e:
        logger.error(f"Failed to read Excel file: {str(e)}")
        return jsonify({"error": f"Failed to read Excel file: {str(e)}"}), 500

    logger.info(f"Excel Columns: {df.columns.tolist()}")
    df.columns = df.columns.str.strip()

    required_cols = ['KOL Nickname', 'Followers', 'Engagement Rate']
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            return jsonify({"error": f"Missing required column: {col}"}), 400

    if df.empty:
        return jsonify([])

    # Clean the data
    df['KOL Nickname'] = df['KOL Nickname'].apply(clean_text)
    df['Followers'] = df['Followers'].apply(parse_followers)
    df['Engagement Rate'] = df['Engagement Rate'].fillna("N/A")
    
    # Clean other columns if they exist
    optional_cols = ['Platform', 'Category', 'Location', 'Bio']
    for col in optional_cols:
        if col in df.columns:
            df[col] = df[col].apply(clean_text)

    photo_dir = os.path.join(base_dir, 'static', 'KOL_Picture')
    photo_files = {}  # Normalized names to normalized filenames
    original_files = {}  # Normalized names to original filenames
    valid_extensions = {'.png'}  # Only allow PNG files
    
    try:
        logger.info(f"\nScanning directory: {photo_dir}")
        files_list = os.listdir(photo_dir)
        logger.info(f"Found {len(files_list)} total files")
        
        # First, log all files found
        logger.info("All files in directory:")
        for f in files_list:
            logger.info(f"  {f}")
        
        for filename in files_list:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in valid_extensions:
                base_name = os.path.splitext(filename)[0]
                spaced_name, no_space_name = normalize_name(base_name)
                if spaced_name:  # Only add if name is not empty after normalization
                    photo_files[no_space_name] = filename
                    original_files[spaced_name] = filename
                    logger.info(f"Indexed image: '{filename}' -> '{spaced_name}' / '{no_space_name}'")
        
        logger.info(f"Successfully indexed {len(photo_files)} valid PNG images")
    except Exception as e:
        logger.error(f"Error reading photo directory: {str(e)}")
        return jsonify({"error": f"Failed to read photo directory: {str(e)}"}), 500

    # Track used photos to prevent duplicates
    used_photos = set()
    
    kols = []
    for _, row in df.iterrows():
        kol_nickname = row['KOL Nickname']
        photo_file = find_matching_photo(kol_nickname, photo_files, original_files, used_photos)
        
        if photo_file and photo_file not in used_photos:
            photo_url = f'/static/KOL_Picture/{urllib.parse.quote(photo_file)}'
            used_photos.add(photo_file)
            logger.info(f"✓ Successfully matched '{kol_nickname}' -> '{photo_file}'")
        else:
            if photo_file:
                logger.warning(f"⚠ Photo '{photo_file}' already used - skipping for '{kol_nickname}'")
            photo_url = 'https://via.placeholder.com/300x400?text=No+Photo'
            logger.warning(f"✗ No photo found for: '{kol_nickname}'")
            
        kol = row.to_dict()
        kol['Photo'] = photo_url
        kols.append(kol)

    return jsonify(kols)

if __name__ == '__main__':
    app.run(debug=True)     