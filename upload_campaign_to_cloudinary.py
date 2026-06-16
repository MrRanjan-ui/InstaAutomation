import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials
import cloudinary
import cloudinary.uploader

from config import load_env, get_project_path

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    config = load_env()
    
    # Configure Cloudinary
    cloud_name = config.get("CLOUDINARY_CLOUD_NAME")
    api_key = config.get("CLOUDINARY_API_KEY")
    api_secret = config.get("CLOUDINARY_API_SECRET")
    
    if not all([cloud_name, api_key, api_secret]):
        print("Error: Cloudinary credentials missing in .env.")
        sys.exit(1)
        
    print(f"Configuring Cloudinary (Cloud: {cloud_name})...")
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret
    )
    
    # Configure Sheets
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    if not os.path.exists(creds_path):
        print(f"Error: Google credentials file '{creds_path}' not found.")
        sys.exit(1)
        
    print("Connecting to Google Sheets...")
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    
    sheet_id = config.get("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("Error: google_sheet_id missing in .env.")
        sys.exit(1)
        
    sh = gc.open_by_key(sheet_id)
    w = sh.worksheet("50DaysCampaign")
    
    # Get all records to find row indices
    records = w.get_all_records()
    headers = w.row_values(1)
    
    post_ids = [
        "day_01_cart_recovery",
        "day_02_cod_confirmation_call",
        "day_03_dm_to_order",
        "day_04_return_exchange_agent",
        "day_05_centralized_order_dashboard",
        "day_06_whatsapp_fit_faq",
        "day_07_order_status_bot"
    ]
    
    # Find columns for Slide_1_URL to Slide_6_URL
    col_indices = {}
    for i in range(1, 7):
        col_name = f"Slide_{i}_URL"
        if col_name in headers:
            col_indices[i] = headers.index(col_name) + 1
        else:
            print(f"Error: Header '{col_name}' not found in sheet.")
            sys.exit(1)
            
    # For each post, upload slides and update sheet
    for post_id in post_ids:
        print(f"\n--- Processing {post_id} ---")
        post_dir = os.path.join("post", post_id)
        if not os.path.exists(post_dir):
            print(f"Warning: Directory {post_dir} not found. Skipping.")
            continue
            
        # Find row in the sheet
        row_idx = None
        for idx, record in enumerate(records, start=2):
            if record.get("Post_ID") == post_id:
                row_idx = idx
                break
                
        if not row_idx:
            print(f"Warning: Post_ID '{post_id}' not found in sheet. Skipping.")
            continue
            
        print(f"Found in sheet at row {row_idx}")
        
        # Upload slides
        for i in range(1, 7):
            slide_file = f"slide_{i:02d}.png"
            slide_path = os.path.join(post_dir, slide_file)
            if not os.path.exists(slide_path):
                print(f"   Slide {slide_path} not found. Skipping column.")
                continue
                
            # 1. Delete previous flat public ID if exists to keep storage clean
            old_public_id = f"goran_ai_50days/{post_id}_slide_{i:02d}"
            try:
                print(f"   Deleting old public ID from Cloudinary: {old_public_id}...")
                cloudinary.uploader.destroy(old_public_id)
            except Exception as del_err:
                print(f"   Warning deleting old public ID: {del_err}")
                
            # 2. Upload to new subfolder-wise structure
            folder_name = f"goran_ai_50days/{post_id}"
            public_id_name = f"slide_{i:02d}"
            
            print(f"   Uploading {slide_file} to Cloudinary folder '{folder_name}' with ID '{public_id_name}'...")
            resp = cloudinary.uploader.upload(
                slide_path, 
                folder=folder_name,
                public_id=public_id_name,
                overwrite=True
            )
            secure_url = resp.get("secure_url")
            print(f"   Uploaded secure URL: {secure_url}")
            
            # 3. Update sheet cell
            col_idx = col_indices[i]
            w.update_cell(row_idx, col_idx, secure_url)
            print(f"   Updated Google Sheet cell at row {row_idx}, col {col_idx}")
            
    print("\n✅ All campaign uploads completed and Google Sheet updated successfully!")

if __name__ == "__main__":
    main()
