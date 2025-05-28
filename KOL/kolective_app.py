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
    """Normalize name for comparison by keeping only alphanumeric and Chinese characters."""
    if pd.isna(name):
        return ""
    
    # Convert to lowercase and remove extra spaces
    name = str(name).lower().strip()
    
    # Split into Chinese and non-Chinese parts
    chinese_chars = ''.join(char for char in name if '\u4e00' <= char <= '\u9fff')
    non_chinese = ''.join(char for char in name if not '\u4e00' <= char <= '\u9fff')
    
    # Clean up non-Chinese part
    non_chinese = re.sub(r'[^a-z0-9]', '', non_chinese)
    
    # Combine both parts
    normalized = non_chinese + chinese_chars
    logger.debug(f"Normalized '{name}' to '{normalized}'")
    return normalized

def find_matching_photo(kol_name, photo_files, original_files, used_photos):
    """Find the best matching photo for a KOL name."""
    normalized_kol_name = normalize_name(kol_name)
    logger.info(f"\nMatching process for KOL: '{kol_name}'")
    logger.info(f"Normalized KOL name: '{normalized_kol_name}'")
    
    # Try exact match first
    for photo_name, original_name in original_files.items():
        if original_name in used_photos:
            continue
            
        normalized_photo = normalize_name(photo_name)
        if normalized_kol_name == normalized_photo:
            logger.info(f"✓ Found exact match: '{original_name}'")
            return original_name
    
    # Try partial matches
    best_match = None
    best_match_score = 0
    
    for photo_name, original_name in original_files.items():
        if original_name in used_photos:
            continue
            
        normalized_photo = normalize_name(photo_name)
        
        # Calculate match scores for Chinese and non-Chinese parts separately
        chinese_kol = ''.join(char for char in normalized_kol_name if '\u4e00' <= char <= '\u9fff')
        non_chinese_kol = ''.join(char for char in normalized_kol_name if not '\u4e00' <= char <= '\u9fff')
        
        chinese_photo = ''.join(char for char in normalized_photo if '\u4e00' <= char <= '\u9fff')
        non_chinese_photo = ''.join(char for char in normalized_photo if not '\u4e00' <= char <= '\u9fff')
        
        # Calculate Chinese match score
        if chinese_kol and chinese_photo:
            chinese_score = 1.0 if chinese_kol == chinese_photo else 0.0
        else:
            chinese_score = 1.0  # If neither has Chinese characters, consider it a match
            
        # Calculate non-Chinese match score
        if non_chinese_kol and non_chinese_photo:
            common_chars = sum(1 for c in non_chinese_kol if c in non_chinese_photo)
            non_chinese_score = common_chars / max(len(non_chinese_kol), len(non_chinese_photo))
        else:
            non_chinese_score = 1.0 if not non_chinese_kol and not non_chinese_photo else 0.0
            
        # Combined score with higher weight for Chinese match
        match_score = (chinese_score * 0.6) + (non_chinese_score * 0.4)
        
        logger.debug(f"Match scores for '{original_name}':")
        logger.debug(f"  Chinese score: {chinese_score:.2f}")
        logger.debug(f"  Non-Chinese score: {non_chinese_score:.2f}")
        logger.debug(f"  Combined score: {match_score:.2f}")
        
        # Update best match if this score is higher
        if match_score > best_match_score and match_score > 0.7:  # Require at least 70% match
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
                normalized_name = normalize_name(base_name)
                if normalized_name:  # Only add if name is not empty after normalization
                    photo_files[normalized_name] = normalized_name
                    original_files[normalized_name] = filename
                    logger.info(f"Indexed image: '{filename}' -> '{normalized_name}'")
        
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