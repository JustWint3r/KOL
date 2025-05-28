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
    """Normalize name for comparison by keeping only alphanumeric characters."""
    if pd.isna(name):
        return ""
    # Convert to lowercase
    name = str(name).lower()
    # Special handling for Chinese characters
    if any('\u4e00' <= char <= '\u9fff' for char in name):
        # For Chinese names, keep the characters as is
        return name
    # For non-Chinese names, only keep alphanumeric
    name = re.sub(r'[^a-z0-9]', '', name)
    logger.debug(f"Normalized name: '{name}'")
    return name

def find_matching_photo(kol_name, photo_files, original_files, used_photos):
    """Find the best matching photo for a KOL name."""
    normalized_kol_name = normalize_name(kol_name)
    logger.info(f"\nMatching process for KOL: '{kol_name}'")
    logger.info(f"Normalized KOL name: '{normalized_kol_name}'")
    
    # Check if name contains Chinese characters
    has_chinese = any('\u4e00' <= char <= '\u9fff' for char in kol_name)
    
    # For Chinese names, require exact matches
    if has_chinese:
        # Look for exact matches only
        for photo_name, original_name in original_files.items():
            if original_name in used_photos:
                continue
            if normalized_kol_name == normalize_name(photo_name):
                logger.info(f"✓ Found exact Chinese name match: '{original_name}'")
                return original_name
        logger.warning(f"✗ No exact match found for Chinese name: '{kol_name}'")
        return None
    
    # For non-Chinese names, try exact match first
    if normalized_kol_name in photo_files:
        matched_file = original_files[normalized_kol_name]
        if matched_file not in used_photos:
            logger.info(f"✓ Found exact match: '{matched_file}'")
            return matched_file
    
    # Try to find the best partial match for non-Chinese names
    best_match = None
    best_match_score = 0
    
    for photo_name, original_name in original_files.items():
        # Skip if photo already used
        if original_name in used_photos:
            continue
            
        # Skip if the photo name contains Chinese characters but KOL name doesn't
        if any('\u4e00' <= char <= '\u9fff' for char in photo_name):
            continue
        
        normalized_photo = normalize_name(photo_name)
        
        # Skip if names are too different in length
        len_diff = abs(len(normalized_kol_name) - len(normalized_photo))
        if len_diff > 2:  # More strict length difference
            continue
            
        # Calculate match score
        common_chars = sum(1 for c in normalized_kol_name if c in normalized_photo)
        match_score = common_chars / max(len(normalized_kol_name), len(normalized_photo))
        
        # Update best match if this score is higher
        if match_score > best_match_score and match_score > 0.8:  # Increased threshold to 80%
            best_match = original_name
            best_match_score = match_score

    if best_match:
        logger.info(f"✓ Found partial match: '{best_match}' (score: {best_match_score:.2f})")
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
    valid_extensions = {'.jpg', '.jpeg', '.png'}
    
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
                normalized_name = normalize_name(base_name)
                if normalized_name:  # Only add if name is not empty after normalization
                    photo_files[normalized_name] = normalized_name
                    original_files[normalized_name] = filename
                    logger.info(f"Indexed image: '{filename}' -> '{normalized_name}'")
        
        logger.info(f"Successfully indexed {len(photo_files)} valid images")
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
            
        kol = row.to_dict()
        kol['Photo'] = photo_url
        kols.append(kol)

    return jsonify(kols)

if __name__ == '__main__':
    app.run(debug=True)     