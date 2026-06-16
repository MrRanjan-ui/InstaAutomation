import os
import sys
import json
import time
import requests
import gspread
import cloudinary
import cloudinary.uploader
from google.oauth2.service_account import Credentials

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

ENV_FILE = ".env"
CONFIG_FILE = "config.json"
META_TEMP_FILE = "post_temp_meta.json"
SLIDES_DIR = r"d:\InstagramPost\post\post_temp"

# 1x1 transparent pixel in Base64 for testing uploads
TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8"
    "AAAAASUVORK5CYII="
)

def load_config():
    config = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip().lower()] = v.strip()
        return config
    elif os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return {k.lower(): v for k, v in json.load(f).items()}
    else:
        print("Error: Neither '.env' nor 'config.json' was found. Please create a '.env' file.")
        sys.exit(1)

def load_post_metadata():
    if not os.path.exists(META_TEMP_FILE):
        print(f"Error: Post metadata file '{META_TEMP_FILE}' not found.")
        print("Please run 'fetch_sheet_data.py' first to retrieve an approved post.")
        sys.exit(1)
    with open(META_TEMP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def upload_image_to_cloudinary(image_path, config):
    """Uploads a local image file to Cloudinary and returns the secure URL."""
    try:
        cloudinary.config(
            cloud_name=config["cloudinary_cloud_name"],
            api_key=config["cloudinary_api_key"],
            api_secret=config["cloudinary_api_secret"],
            secure=True
        )
        response = cloudinary.uploader.upload(image_path)
        return response.get("secure_url")
    except Exception as e:
        print(f"Error uploading to Cloudinary: {e}")
        return None

def test_cloudinary_upload(config):
    """Uploads a base64 tiny image to verify Cloudinary connection and credentials."""
    try:
        cloudinary.config(
            cloud_name=config["cloudinary_cloud_name"],
            api_key=config["cloudinary_api_key"],
            api_secret=config["cloudinary_api_secret"],
            secure=True
        )
        data_uri = f"data:image/png;base64,{TINY_PNG_BASE64}"
        response = cloudinary.uploader.upload(data_uri)
        public_url = response.get("secure_url")
        public_id = response.get("public_id")
        if public_url:
            cloudinary.uploader.destroy(public_id)
            return public_url
    except Exception as e:
        print(f"Cloudinary test failed: {e}")
    return None

def test_instagram_token(account_id, token):
    """Validates Instagram API credentials."""
    url = f"https://graph.facebook.com/v19.0/{account_id}"
    params = {"fields": "username,name", "access_token": token}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None

def create_instagram_carousel_item(image_url, account_id, token):
    """Creates a container for an individual item in a carousel."""
    url = f"https://graph.facebook.com/v19.0/{account_id}/media"
    payload = {
        "image_url": image_url,
        "is_carousel_item": "true",
        "access_token": token
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get("id")
    else:
        print(f"Error creating Instagram item container: {response.status_code} - {response.text}")
        return None

def create_instagram_carousel_container(item_ids, caption, account_id, token):
    """Creates a parent container combining all slide items."""
    url = f"https://graph.facebook.com/v19.0/{account_id}/media"
    children_str = ",".join(item_ids)
    payload = {
        "media_type": "CAROUSEL",
        "children": children_str,
        "caption": caption,
        "access_token": token
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get("id")
    else:
        print(f"Error creating Instagram carousel container: {response.status_code} - {response.text}")
        return None

def publish_instagram_container(creation_id, account_id, token):
    """Publishes the media container to the live Instagram feed."""
    url = f"https://graph.facebook.com/v19.0/{account_id}/media_publish"
    payload = {
        "creation_id": creation_id,
        "access_token": token
    }
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json().get("id")
    else:
        print(f"Error publishing Instagram container: {response.status_code} - {response.text}")
        return None

def update_google_sheet_status(config, row_idx, new_status):
    """Connects to Google Sheets and updates the Status column."""
    creds_path = config["google_creds_file"]
    if not os.path.exists(creds_path):
        print("Warning: Google Sheets credential file not found. Skipping sheet status update.")
        return False
        
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    client = gspread.authorize(creds)
    
    try:
        spreadsheet = client.open_by_key(config["google_sheet_id"])
        sheet = spreadsheet.worksheet(config["google_sheet_name"])
        headers = sheet.row_values(1)
        if "Status" in headers:
            col_idx = headers.index("Status") + 1
            sheet.update_cell(row_idx, col_idx, new_status)
            print(f"Successfully updated status in sheet row {row_idx} to '{new_status}'.")
            return True
        else:
            print("Warning: 'Status' column not found in Google Sheet headers.")
    except Exception as e:
        print(f"Error updating Google Sheet status: {e}")
    return False

def main():
    config = load_config()
    meta = load_post_metadata()
    
    dry_run = "--dry-run" in sys.argv
    
    if dry_run:
        print("🔍 RUNNING DRY-RUN CONNECTIONS VERIFICATION...")
        
        # 1. Test Cloudinary
        print("\n1. Testing Cloudinary API connection...")
        img_link = test_cloudinary_upload(config)
        if img_link:
            print(f"   ✅ Cloudinary upload & delete verification successful! Test Image: {img_link}")
        else:
            print("   ❌ Cloudinary API test failed. Check your Cloudinary credentials in .env.")
            
        # 2. Test Instagram Graph API
        print("\n2. Testing Instagram Graph API token...")
        ig_profile = test_instagram_token(config["instagram_business_account_id"], config["instagram_access_token"])
        if ig_profile:
            print(f"   ✅ Instagram API connection successful!")
            print(f"   ✅ Instagram Account: @{ig_profile.get('username')} ({ig_profile.get('name')})")
        else:
            print("   ❌ Instagram Graph API verification failed. Check account ID and access token.")
            
        # 3. Check local slide directory
        print(f"\n3. Checking local slides folder '{SLIDES_DIR}'...")
        if os.path.exists(SLIDES_DIR):
            files = sorted([f for f in os.listdir(SLIDES_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            print(f"   ✅ Slide directory exists. Found {len(files)} image files:")
            for f in files:
                print(f"      - {f}")
        else:
            print(f"   ❌ Slide directory '{SLIDES_DIR}' does not exist.")
            
        print("\nVerification checks complete.")
        return

    # Normal Publishing Flow
    print(f"Starting publishing flow for Post: {meta.get('Post_ID')}")
    
    if not os.path.exists(SLIDES_DIR):
        print(f"Error: Slide folder not found at {SLIDES_DIR}.")
        sys.exit(1)
        
    slide_files = sorted([
        os.path.join(SLIDES_DIR, f) 
        for f in os.listdir(SLIDES_DIR) 
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    
    if not slide_files:
        print(f"Error: No image files (.png, .jpg, .jpeg) found in {SLIDES_DIR}.")
        sys.exit(1)
        
    print(f"Found {len(slide_files)} slide files to publish.")
    
    # 1. Upload Slides to Cloudinary
    public_urls = []
    print("\nStep 1: Uploading slides to Cloudinary...")
    for idx, path in enumerate(slide_files, start=1):
        print(f"   Uploading slide {idx}/{len(slide_files)}: {os.path.basename(path)}...")
        url = upload_image_to_cloudinary(path, config)
        if not url:
            print("Error: Upload failed. Terminating publishing pipeline.")
            sys.exit(1)
        print(f"      Public URL: {url}")
        public_urls.append(url)
        time.sleep(1) # Rate limit padding
        
    # 2. Create Instagram Carousel Item Containers
    print("\nStep 2: Creating Instagram media item containers...")
    item_ids = []
    for idx, url in enumerate(public_urls, start=1):
        print(f"   Creating container for slide {idx}/{len(public_urls)}...")
        item_id = create_instagram_carousel_item(url, config["instagram_business_account_id"], config["instagram_access_token"])
        if not item_id:
            print("Error: Failed to create item container. Terminating.")
            sys.exit(1)
        print(f"      Container ID: {item_id}")
        item_ids.append(item_id)
        time.sleep(1)
        
    # 3. Create Carousel Parent Container
    print("\nStep 3: Creating Instagram parent carousel container...")
    caption_text = meta.get("Caption", "")
    carousel_id = create_instagram_carousel_container(
        item_ids, 
        caption_text, 
        config["instagram_business_account_id"], 
        config["instagram_access_token"]
    )
    if not carousel_id:
        print("Error: Failed to create parent carousel container. Terminating.")
        sys.exit(1)
    print(f"   Carousel Container ID: {carousel_id}")
    
    # Wait for Instagram backend to process containers (usually 10-30 seconds is safe)
    print("   Waiting 10 seconds for Instagram container processing...")
    time.sleep(10)
    
    # 4. Publish Carousel
    print("\nStep 4: Publishing carousel to Instagram live feed...")
    publish_id = publish_instagram_container(carousel_id, config["instagram_business_account_id"], config["instagram_access_token"])
    if not publish_id:
        print("Error: Failed to publish carousel post.")
        sys.exit(1)
    print(f"🎉 SUCCESS! Carousel successfully published to Instagram.")
    print(f"   Instagram Post ID: {publish_id}")
    
    # 5. Update Google Sheet status to Posted
    print("\nStep 5: Updating Google Sheet status...")
    update_google_sheet_status(config, meta["Row_Index"], "Posted")
    
    # Cleanup metadata cache
    if os.path.exists(META_TEMP_FILE):
        os.remove(META_TEMP_FILE)
        
    print("\nAll done!")

if __name__ == "__main__":
    main()
