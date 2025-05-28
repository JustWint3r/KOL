import pandas as pd
from flask import Flask, render_template, request, jsonify
import os
import re
import urllib.parse
import logging

app = Flask(__name__)

# Set up logging
logging.basicConfig(level=logging.INFO)
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
    # Convert to lowercase and remove extra spaces
    name = str(name).lower().strip()
    # Remove special characters but preserve Chinese characters and emojis
    name = re.sub(r'[^\w\s\u4e00-\u9fff\U0001F300-\U0001F9FF]', '', name)
    return name

def find_matching_photo(normalized_name, photo_files):
    """Find the best matching photo for a KOL name."""
    if normalized_name in photo_files:
        return photo_files[normalized_name]
    
    # Try partial matching
    for photo_name, file in photo_files.items():
        # Check if either name contains the other
        if normalized_name in photo_name or photo_name in normalized_name:
            return file
        
        # Split names into words and check for word matches
        name_words = set(normalized_name.split())
        photo_words = set(photo_name.split())
        if len(name_words.intersection(photo_words)) >= min(len(name_words), len(photo_words)) / 2:
            return file
    
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
    photo_files = {}
    valid_extensions = {'.jpg', '.jpeg', '.png'}
    
    try:
        for f in os.listdir(photo_dir):
            file_ext = os.path.splitext(f)[1].lower()
            if file_ext in valid_extensions:
                normalized_name = normalize_name(os.path.splitext(f)[0])
                photo_files[normalized_name] = f
                logger.info(f"Found image: {f} -> {normalized_name}")
    except Exception as e:
        logger.error(f"Error reading photo directory: {str(e)}")
        return jsonify({"error": f"Failed to read photo directory: {str(e)}"}), 500

    kols = []
    for _, row in df.iterrows():
        name = normalize_name(row['KOL Nickname'])
        photo_file = find_matching_photo(name, photo_files)
        
        if photo_file:
            photo_url = f'/static/KOL_Picture/{urllib.parse.quote(photo_file)}'
            logger.info(f"Matched {row['KOL Nickname']} -> {photo_file}")
        else:
            photo_url = 'https://via.placeholder.com/300x400?text=No+Photo'
            logger.warning(f"No photo found for: {row['KOL Nickname']}")
        
        kol = row.to_dict()
        kol['Photo'] = photo_url
        kols.append(kol)

    return jsonify(kols)

if __name__ == '__main__':
    app.run(debug=True)     