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
    # Remove all special characters and extra spaces, keep only letters and numbers
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def find_matching_photo(kol_name, photo_files, original_files):
    """Find the best matching photo for a KOL name."""
    normalized_kol_name = normalize_name(kol_name)
    logger.info(f"Looking for match for KOL: {kol_name} (normalized: {normalized_kol_name})")

    # Direct match first
    if normalized_kol_name in photo_files:
        logger.info(f"Found direct match for {kol_name}")
        return original_files[normalized_kol_name]

    # Try partial matching
    for photo_name, original_name in original_files.items():
        # If the normalized names contain each other
        if normalized_kol_name in photo_name or photo_name in normalized_kol_name:
            logger.info(f"Found partial match: {kol_name} -> {original_name}")
            return original_name

    logger.warning(f"No match found for {kol_name}")
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
        logger.info(f"Scanning directory: {photo_dir}")
        files_list = os.listdir(photo_dir)
        logger.info(f"Found {len(files_list)} total files")
        
        for filename in files_list:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext in valid_extensions:
                base_name = os.path.splitext(filename)[0]
                normalized_name = normalize_name(base_name)
                if normalized_name:  # Only add if name is not empty after normalization
                    photo_files[normalized_name] = normalized_name
                    original_files[normalized_name] = filename
                    logger.info(f"Indexed image: {filename} -> {normalized_name}")
        
        logger.info(f"Indexed {len(photo_files)} valid images")
    except Exception as e:
        logger.error(f"Error reading photo directory: {str(e)}")
        return jsonify({"error": f"Failed to read photo directory: {str(e)}"}), 500

    kols = []
    for _, row in df.iterrows():
        kol_nickname = row['KOL Nickname']
        photo_file = find_matching_photo(kol_nickname, photo_files, original_files)
        
        if photo_file:
            photo_url = f'/static/KOL_Picture/{urllib.parse.quote(photo_file)}'
            logger.info(f"Successfully matched {kol_nickname} -> {photo_file}")
        else:
            photo_url = 'https://via.placeholder.com/300x400?text=No+Photo'
            logger.warning(f"No photo found for: {kol_nickname}")
        
        kol = row.to_dict()
        kol['Photo'] = photo_url
        kols.append(kol)

    return jsonify(kols)

if __name__ == '__main__':
    app.run(debug=True)     