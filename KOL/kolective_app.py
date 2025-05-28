import pandas as pd
from flask import Flask, render_template, request, jsonify
import os
import re
import urllib.parse

app = Flask(__name__)

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
    """Normalize name by converting to lowercase only (preserve spaces, Chinese characters, and emojis)."""
    if pd.isna(name):
        return ""
    return str(name).lower().strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/kols')
def api_kols():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    excel_path = os.path.join(base_dir, 'List.xlsx')
    print("Reading from:", excel_path)

    try:
        df = pd.read_excel(excel_path, engine='openpyxl')
    except FileNotFoundError:
        return jsonify({"error": "List.xlsx not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to read Excel file: {str(e)}"}), 500

    print("Excel Columns:", df.columns.tolist())  # Debug
    df.columns = df.columns.str.strip()  # Clean header names

    required_cols = ['KOL Nickname', 'Followers', 'Engagement Rate']
    for col in required_cols:
        if col not in df.columns:
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
    valid_extensions = ('.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG')
    for f in os.listdir(photo_dir):
        if f.lower().endswith(valid_extensions):
            normalized_name = normalize_name(os.path.splitext(f)[0])
            photo_files[normalized_name] = f

    kols = []
    for _, row in df.iterrows():
        name = normalize_name(row['KOL Nickname'])
        photo_file = photo_files.get(name)
        if not photo_file:
            for photo_name, file in photo_files.items():
                if name in photo_name or photo_name in name:
                    photo_file = file
                    break
        # Use the filename directly without additional encoding since urllib.parse.quote will handle it
        photo_url = f'/static/KOL_Picture/{photo_file}' if photo_file else 'https://via.placeholder.com/300x400?text=No+Photo'
        kol = row.to_dict()
        kol['Photo'] = photo_url
        kols.append(kol)

    return jsonify(kols)

if __name__ == '__main__':
    app.run(debug=True)     