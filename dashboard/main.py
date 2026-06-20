import os
import sys
import json
import time
from pymongo import MongoClient
from bson import ObjectId
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, List
import requests
import gspread
from google.oauth2.service_account import Credentials
import fastapi
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import cloudinary
import cloudinary.uploader

# Ensure stdout handles UTF-8 on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# ─── Structured Logging ───────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("goran-scheduler")

# Resolve paths relative to project root (one level up from dashboard/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scheduler.db")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

from Posting.comment_automation import router as comment_automation_router, comment_polling_worker

# ─── Lifespan (replaces deprecated on_event) ──────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate environment and launch scheduler
    config = load_env()
    missing = []
    for key in ["INSTAGRAM_BUSINESS_ACCOUNT_ID", "INSTAGRAM_ACCESS_TOKEN", "GOOGLE_SHEET_ID"]:
        if not config.get(key):
            missing.append(key)
    if missing:
        logger.warning(f"Missing environment variables: {', '.join(missing)}. Some features will be disabled.")
    else:
        logger.info("All required environment variables are configured.")
    
    # Start the background scheduler worker
    scheduler_task = asyncio.create_task(scheduler_worker())
    logger.info("Background scheduler worker started.")
    
    # Start the comment poller background worker
    comment_poller_task = asyncio.create_task(comment_polling_worker())
    logger.info("Comment automation background poller started.")
    
    yield  # Application runs
    
    # Shutdown: cancel the scheduler and poller
    scheduler_task.cancel()
    comment_poller_task.cancel()
    try:
        await asyncio.gather(scheduler_task, comment_poller_task, return_exceptions=True)
    except Exception:
        pass
    logger.info("Scheduler and Comment Poller workers stopped.")

app = FastAPI(title="GoRan AI Instagram Scheduler Dashboard", lifespan=lifespan)
app.include_router(comment_automation_router)

# ─── CORS Middleware ──────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Load Environment Configuration ───────────────────────────
def load_env():
    config = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
                    
    # Fallback to standard OS environment variables (essential for Render/production)
    for key, value in os.environ.items():
        if value:
            config[key] = value
            
    # Dynamically generate Google service account file if GOOGLE_CREDS_JSON is provided
    creds_json = config.get("GOOGLE_CREDS_JSON")
    creds_file = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    if creds_json and creds_file:
        if not os.path.isabs(creds_file):
            creds_file_path = os.path.join(PROJECT_ROOT, creds_file)
        else:
            creds_file_path = creds_file
            
        if not os.path.exists(creds_file_path):
            try:
                # Validate it is valid JSON and write it
                json_data = json.loads(creds_json)
                with open(creds_file_path, "w", encoding="utf-8") as out_f:
                    json.dump(json_data, out_f, indent=2)
                logger.info(f"Dynamically generated credentials file from GOOGLE_CREDS_JSON at: {creds_file_path}")
            except Exception as write_err:
                logger.error(f"Failed to generate credentials file from GOOGLE_CREDS_JSON: {write_err}")
                
    # Self-healing for duplicated token segments
    token = config.get("INSTAGRAM_ACCESS_TOKEN")
    if token and len(token) > 220:
        for length in range(30, len(token) // 2 + 1):
            found = False
            for i in range(len(token) - 2 * length + 1):
                sub = token[i:i+length]
                if token[i+length:i+2*length] == sub:
                    config["INSTAGRAM_ACCESS_TOKEN"] = token[:i] + sub + token[i+2*length:]
                    found = True
                    break
            if found:
                break
                
    return config

# ─── Database Initialization ──────────────────────────────────
_mongo_client = None

def get_mongo_db():
    global _mongo_client
    config = load_env()
    mongo_uri = config.get("MONGO_URI", "mongodb://localhost:27017")
    
    if "<db_password>" in mongo_uri or "<" in mongo_uri or ">" in mongo_uri:
        raise ValueError("MongoDB URI contains '<db_password>' placeholder. Please configure your actual password in the .env file.")
        
    # Automatically escape special characters in MongoDB credentials if present
    try:
        from urllib.parse import urlsplit, urlunsplit, quote_plus, unquote
        split_uri = urlsplit(mongo_uri)
        if '@' in split_uri.netloc:
            creds, hosts = split_uri.netloc.rsplit('@', 1)
            if ':' in creds:
                username, password = creds.split(':', 1)
            else:
                username, password = creds, ''
            escaped_username = quote_plus(unquote(username)) if username else ''
            escaped_password = quote_plus(unquote(password)) if password else ''
            if escaped_username:
                if escaped_password:
                    new_creds = f'{escaped_username}:{escaped_password}'
                else:
                    new_creds = escaped_username
                new_netloc = f'{new_creds}@{hosts}'
            else:
                new_netloc = hosts
            mongo_uri = urlunsplit((split_uri.scheme, new_netloc, split_uri.path, split_uri.query, split_uri.fragment))
    except Exception as parse_err:
        logger.warning(f"Failed to auto-escape MongoDB URI: {parse_err}")

    if _mongo_client is None:
        _mongo_client = MongoClient(mongo_uri)
    return _mongo_client["goran_ai"]

def serialize_doc(doc):
    if not doc:
        return None
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    del doc["_id"]
    # If slide_urls in MongoDB is list, return it directly, else deserialize from string
    if isinstance(doc.get("slide_urls"), str):
        try:
            doc["slide_urls"] = json.loads(doc["slide_urls"])
        except Exception:
            doc["slide_urls"] = [doc["slide_urls"]]
    return doc

def init_db():
    try:
        db = get_mongo_db()
        db.scheduled_posts.create_index("status")
        db.scheduled_posts.create_index("schedule_time")
        logger.info("MongoDB connection verified & indexes created successfully.")
    except ValueError as val_err:
        logger.warning(f"MongoDB connection skipped: {val_err}")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {e}")

init_db()

# ─── Google Sheets Client Helper ──────────────────────────────
def get_sheets_client(creds_path):
    if not os.path.exists(creds_path):
        return None
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)

# ─── Instagram Publisher Logic ────────────────────────────────
def publish_single_post(image_url: str, caption: str, account_id: str, token: str) -> str:
    """Publish a single image post. Runs in a thread via asyncio.to_thread."""
    # 1. Create Media Container
    url = f"https://graph.facebook.com/v19.0/{account_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": token
    }
    
    max_retries = 3
    backoff = 5
    resp = None
    for attempt in range(max_retries):
        resp = requests.post(url, data=payload)
        if resp.status_code == 200:
            break
            
        error_data = {}
        try:
            error_data = resp.json().get("error", {})
        except Exception:
            pass
            
        subcode = error_data.get("error_subcode")
        # Retry on media fetch/download failures (2207052)
        if subcode == 2207052 and attempt < max_retries - 1:
            logger.warning(f"Media download failed for single post {image_url} (subcode 2207052). Retrying in {backoff} seconds...")
            time.sleep(backoff)
            backoff *= 2
        else:
            raise Exception(f"Failed to create media container: {resp.text}")
            
    container_id = resp.json().get("id")

    # Wait for processing
    time.sleep(10)

    # 2. Publish Media
    pub_url = f"https://graph.facebook.com/v19.0/{account_id}/media_publish"
    pub_payload = {
        "creation_id": container_id,
        "access_token": token
    }
    pub_resp = requests.post(pub_url, data=pub_payload)
    if pub_resp.status_code != 200:
        raise Exception(f"Failed to publish container: {pub_resp.text}")
    return pub_resp.json().get("id")

def publish_carousel_post(image_urls: List[str], caption: str, account_id: str, token: str) -> str:
    """Publish a carousel post. Runs in a thread via asyncio.to_thread."""
    # 1. Create individual item containers
    item_ids = []
    for url in image_urls:
        item_url = f"https://graph.facebook.com/v19.0/{account_id}/media"
        payload = {
            "image_url": url,
            "is_carousel_item": "true",
            "access_token": token
        }
        
        max_retries = 3
        backoff = 5
        resp = None
        for attempt in range(max_retries):
            resp = requests.post(item_url, data=payload)
            if resp.status_code == 200:
                break
                
            error_data = {}
            try:
                error_data = resp.json().get("error", {})
            except Exception:
                pass
                
            subcode = error_data.get("error_subcode")
            # Retry on media fetch/download failures (2207052)
            if subcode == 2207052 and attempt < max_retries - 1:
                logger.warning(f"Media download failed for carousel item {url} (subcode 2207052). Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2
            else:
                raise Exception(f"Failed to create carousel item container: {resp.text}")
                
        item_ids.append(resp.json().get("id"))
        time.sleep(1)

    # 2. Create Parent Container
    parent_url = f"https://graph.facebook.com/v19.0/{account_id}/media"
    parent_payload = {
        "media_type": "CAROUSEL",
        "children": ",".join(item_ids),
        "caption": caption,
        "access_token": token
    }
    parent_resp = requests.post(parent_url, data=parent_payload)
    if parent_resp.status_code != 200:
        raise Exception(f"Failed to create parent carousel container: {parent_resp.text}")
    carousel_id = parent_resp.json().get("id")

    # Wait for processing
    time.sleep(10)

    # 3. Publish
    pub_url = f"https://graph.facebook.com/v19.0/{account_id}/media_publish"
    pub_payload = {
        "creation_id": carousel_id,
        "access_token": token
    }
    pub_resp = requests.post(pub_url, data=pub_payload)
    if pub_resp.status_code != 200:
        raise Exception(f"Failed to publish carousel: {pub_resp.text}")
    return pub_resp.json().get("id")


# ─── Background Worker ────────────────────────────────────────
def ensure_cloudinary_urls(slide_urls: List[str], post_id: str) -> List[str]:
    """Auto-upload local slide URLs to Cloudinary and return secure URLs."""
    config = load_env()
    cloud_name = config.get("CLOUDINARY_CLOUD_NAME")
    api_key = config.get("CLOUDINARY_API_KEY")
    api_secret = config.get("CLOUDINARY_API_SECRET")
    
    if not all([cloud_name, api_key, api_secret]):
        logger.warning("Cloudinary credentials missing, cannot auto-upload local paths.")
        return slide_urls
        
    try:
        import cloudinary
        import cloudinary.uploader
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret
        )
    except Exception as init_err:
        logger.error(f"Failed to configure Cloudinary client: {init_err}")
        return slide_urls
        
    from urllib.parse import urlparse
    uploaded_urls = []
    for idx, url in enumerate(slide_urls, start=1):
        is_local = False
        if not (url.startswith("http://") or url.startswith("https://")):
            is_local = True
        elif "localhost" in url or "127.0.0.1" in url or "onrender.com" in url:
            is_local = True
        else:
            # Check if it points to a local file path on this server
            try:
                parsed = urlparse(url)
                clean_url = parsed.path.lstrip("/")
                if clean_url.startswith("post/"):
                    local_path = os.path.join(PROJECT_ROOT, clean_url)
                else:
                    local_path = os.path.join(PROJECT_ROOT, "post", clean_url)
                if os.path.exists(local_path):
                    is_local = True
            except Exception:
                pass

        if not is_local:
            uploaded_urls.append(url)
        else:
            # Resolve relative local path
            if url.startswith("http://") or url.startswith("https://"):
                parsed = urlparse(url)
                clean_url = parsed.path.lstrip("/")
            else:
                clean_url = url.lstrip("/")

            if clean_url.startswith("post/"):
                local_path = os.path.join(PROJECT_ROOT, clean_url)
            else:
                local_path = os.path.join(PROJECT_ROOT, "post", clean_url)
                
            if os.path.exists(local_path):
                try:
                    folder_name = f"goran_ai_50days/{post_id}"
                    public_id_name = f"slide_{idx:02d}"
                    logger.info(f"Uploading local file {local_path} to Cloudinary folder '{folder_name}' with ID '{public_id_name}'...")
                    resp = cloudinary.uploader.upload(
                        local_path,
                        folder=folder_name,
                        public_id=public_id_name,
                        overwrite=True
                    )
                    secure_url = resp.get("secure_url")
                    if secure_url:
                        uploaded_urls.append(secure_url)
                    else:
                        uploaded_urls.append(url)
                except Exception as e:
                    logger.error(f"Failed to upload {local_path} to Cloudinary: {e}")
                    uploaded_urls.append(url)
            else:
                logger.warning(f"Local file {local_path} not found for auto-upload.")
                uploaded_urls.append(url)
    return uploaded_urls

_token_status_cache = {"timestamp": 0, "data": None}

def check_token_status(token: str) -> dict:
    url = "https://graph.facebook.com/debug_token"
    params = {
        "input_token": token,
        "access_token": token
    }
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            is_valid = data.get("is_valid", False)
            expires_at = data.get("expires_at", 0) # epoch time
            scopes = data.get("scopes", [])
            app_name = data.get("application", "Unknown App")
            
            days_remaining = None
            expires_at_dt = None
            if expires_at and expires_at > 0:
                expires_at_dt = datetime.fromtimestamp(expires_at).isoformat()
                delta = datetime.fromtimestamp(expires_at) - datetime.now()
                days_remaining = max(0, delta.days)
            else:
                days_remaining = 36500  # basically infinite/never expires
                
            return {
                "is_valid": is_valid,
                "expires_at": expires_at_dt,
                "days_remaining": days_remaining,
                "scopes": scopes,
                "app_name": app_name,
                "error": None
            }
        else:
            return {
                "is_valid": False,
                "expires_at": None,
                "days_remaining": 0,
                "scopes": [],
                "app_name": "N/A",
                "error": resp.json().get("error", {}).get("message", "API Error")
            }
    except Exception as e:
        return {
            "is_valid": False,
            "expires_at": None,
            "days_remaining": 0,
            "scopes": [],
            "app_name": "N/A",
            "error": str(e)
        }

def get_cached_token_status(token: str) -> dict:
    now = time.time()
    if _token_status_cache["data"] and (now - _token_status_cache["timestamp"] < 300): # cache for 5 minutes
        return _token_status_cache["data"]
    
    data = check_token_status(token)
    _token_status_cache["data"] = data
    _token_status_cache["timestamp"] = now
    return data

def _sync_publish_job(job_dict, account_id, token, creds_path, sheet_id):
    """Synchronous publish logic — runs in a thread to avoid blocking the event loop."""
    job_id = job_dict["id"]
    post_id = job_dict["post_id"]
    caption = job_dict["caption"]
    slide_urls = job_dict["slide_urls"]
    if isinstance(slide_urls, str):
        try:
            slide_urls = json.loads(slide_urls)
        except Exception:
            slide_urls = [slide_urls]
    source_sheet = job_dict["source_sheet"]
    row_index = job_dict["row_index"]

    # Update status to Posting
    db = get_mongo_db()
    db.scheduled_posts.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "Posting"}})

    try:
        # 1. Ensure all slide URLs are uploaded to Cloudinary
        slide_urls = ensure_cloudinary_urls(slide_urls, post_id)
        
        # 2. Update DB with uploaded URLs
        db.scheduled_posts.update_one({"_id": ObjectId(job_id)}, {"$set": {"slide_urls": slide_urls}})

        # 3. Publish single image vs. carousel
        if len(slide_urls) == 1:
            published_id = publish_single_post(slide_urls[0], caption, account_id, token)
        else:
            published_id = publish_carousel_post(slide_urls, caption, account_id, token)

        # Mark database success
        db.scheduled_posts.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {"status": "Success", "published_id": published_id}}
        )
        logger.info(f"Successfully published Job {job_id} (Post {post_id}). Instagram ID: {published_id}")

        # Update Google Sheet status to 'Posted' and update Slide URLs if credentials available
        if os.path.exists(creds_path) and sheet_id and row_index:
            try:
                client = get_sheets_client(creds_path)
                spreadsheet = client.open_by_key(sheet_id)
                sheet = spreadsheet.worksheet(source_sheet)
                headers = sheet.row_values(1)
                
                cells_to_update = []
                if "Status" in headers:
                    col_idx = headers.index("Status") + 1
                    cells_to_update.append(gspread.Cell(row=row_index, col=col_idx, value="Posted"))
                    
                if "Post_Date" in headers:
                    col_idx = headers.index("Post_Date") + 1
                    cells_to_update.append(gspread.Cell(row=row_index, col=col_idx, value=datetime.now().isoformat()))
                    
                # Update Slide URLs if they are currently not Cloudinary URLs or not populated
                for i in range(1, 7):
                    col_name = f"Slide_{i}_URL"
                    if col_name in headers:
                        col_idx = headers.index(col_name) + 1
                        if i - 1 < len(slide_urls):
                            cells_to_update.append(gspread.Cell(row=row_index, col=col_idx, value=slide_urls[i - 1]))
                
                if cells_to_update:
                    sheet.update_cells(cells_to_update, value_input_option="RAW")
            except Exception as sheet_err:
                logger.warning(f"Failed to update Google Sheet status for Job {job_id}: {sheet_err}")

    except Exception as ex:
        logger.error(f"Publish error on Job {job_id}: {ex}")
        # Retrieve current retry count
        job = db.scheduled_posts.find_one({"_id": ObjectId(job_id)})
        current_retry = job.get("retry_count", 0) if job and job.get("retry_count") is not None else 0
        
        if current_retry < 3:
            new_retry = current_retry + 1
            next_retry_time = (datetime.now() + timedelta(minutes=2)).isoformat()
            db.scheduled_posts.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": {
                    "status": "Pending",
                    "retry_count": new_retry,
                    "error_message": f"Attempt {new_retry} failed: {ex}",
                    "schedule_time": next_retry_time
                }}
            )
            logger.info(f"Retrying Job {job_id} in 2 minutes (Attempt {new_retry}/3)")
        else:
            db.scheduled_posts.update_one(
                {"_id": ObjectId(job_id)},
                {"$set": {
                    "status": "Failed",
                    "error_message": f"Failed after 3 attempts. Last error: {ex}"
                }}
            )
    # connection doesn't need closing because MongoClient manages it

async def scheduler_worker():
    """Background worker that polls for pending posts and publishes them.
    Uses asyncio.to_thread() so blocking HTTP calls don't freeze the event loop."""
    while True:
        try:
            config = load_env()
            account_id = config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
            token = config.get("INSTAGRAM_ACCESS_TOKEN")
            creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
            sheet_id = config.get("GOOGLE_SHEET_ID")

            if not account_id or not token:
                await asyncio.sleep(10)
                continue

            db = get_mongo_db()
            
            # Find posts scheduled for now or in the past that are 'Pending'
            now_str = datetime.now().isoformat()
            cursor = db.scheduled_posts.find({
                "status": "Pending",
                "schedule_time": {"$lte": now_str}
            })
            jobs = [serialize_doc(doc) for doc in cursor]
            
            for job in jobs:
                logger.info(f"Starting publish job {job['id']} for Post {job['post_id']}")
                # Run the blocking publish in a thread so the event loop stays responsive
                await asyncio.to_thread(
                    _sync_publish_job, job, account_id, token, creds_path, sheet_id
                )

        except ValueError as val_err:
            logger.warning(f"Scheduler worker waiting for MongoDB configuration: {val_err}")
            await asyncio.sleep(60)
            continue
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Scheduler outer loop error: {e}")
        
        await asyncio.sleep(10)

# ─── API Endpoints ───────────────────────────────────────────

class ScheduleRequest(BaseModel):
    post_id: str
    topic: str
    source_sheet: str
    caption: str
    slide_urls: List[str]
    schedule_time: str # ISO string
    row_index: Optional[int] = None

class PublishNowRequest(BaseModel):
    post_id: str
    source_sheet: str
    row_index: int
    slide_urls: List[str]
    caption: str

@app.get("/api/token/status")
def get_token_status():
    config = load_env()
    token = config.get("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        return {
            "is_valid": False,
            "expires_at": None,
            "days_remaining": 0,
            "scopes": [],
            "app_name": "N/A",
            "error": "Instagram access token not configured in .env file."
        }
    status = get_cached_token_status(token)
    return status

@app.get("/api/config")
def get_dashboard_config():
    config = load_env()
    creds_exist = os.path.exists(config.get("GOOGLE_CREDS_FILE", "google_service_account.json"))
    instagram_configured = bool(config.get("INSTAGRAM_ACCESS_TOKEN"))
    mongodb_configured = False
    try:
        db = get_mongo_db()
        db.command("ping")
        mongodb_configured = True
    except Exception as e:
        logger.error(f"MongoDB connection check failed: {e}")
        
    return {
        "google_sheet_id": config.get("GOOGLE_SHEET_ID", "Not Configured"),
        "google_creds_configured": creds_exist,
        "instagram_account_id": config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "Not Configured"),
        "cloudinary_configured": bool(config.get("CLOUDINARY_API_KEY")),
        "mongodb_configured": mongodb_configured,
        "token_status": get_cached_token_status(config.get("INSTAGRAM_ACCESS_TOKEN")) if instagram_configured else None
    }

@app.get("/api/posts")
def get_posts_from_sheets():
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    
    if not os.path.exists(creds_path) or not sheet_id:
        # Return empty list and status warning if Google sheets integration is unconfigured
        return {
            "campaign_posts": [],
            "random_posts": [],
            "error": "Google Sheets configuration missing. Run the app, add your Service Account JSON, and verify spreadsheet IDs."
        }

    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        
        # 1. Fetch random queue posts (standard Queue sheet)
        random_posts = []
        try:
            sheet_queue = spreadsheet.worksheet(config.get("GOOGLE_SHEET_NAME", "Queue"))
            records = sheet_queue.get_all_records()
            for idx, r in enumerate(records, start=2):
                r["row_index"] = idx
                random_posts.append(r)
        except Exception as e:
            print(f"Error loading Queue sheet: {e}")

        # 2. Fetch daily campaign posts
        campaign_posts = []
        try:
            sheet_camp = spreadsheet.worksheet("50DaysCampaign")
            records_camp = sheet_camp.get_all_records()
            for idx, r in enumerate(records_camp, start=2):
                r["row_index"] = idx
                campaign_posts.append(r)
        except Exception as e:
            # Fallback if worksheet does not exist yet
            print(f"50DaysCampaign sheet not found: {e}. Auto-creating sample campaign sheet data...")
        
        return {
            "campaign_posts": campaign_posts,
            "random_posts": random_posts
        }
    except Exception as e:
        return {"error": str(e), "campaign_posts": [], "random_posts": []}

@app.post("/api/schedule")
def schedule_post(req: ScheduleRequest):
    db = get_mongo_db()
    created_at = datetime.now().isoformat()
    
    # Check for existing Pending job
    existing = db.scheduled_posts.find_one({
        "post_id": req.post_id,
        "source_sheet": req.source_sheet,
        "status": "Pending"
    })
    
    if existing:
        db.scheduled_posts.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "topic": req.topic,
                "caption": req.caption,
                "slide_urls": req.slide_urls,
                "schedule_time": req.schedule_time,
                "row_index": req.row_index
            }}
        )
        message = f"Post {req.post_id} schedule updated successfully for {req.schedule_time}."
    else:
        db.scheduled_posts.insert_one({
            "post_id": req.post_id,
            "topic": req.topic,
            "source_sheet": req.source_sheet,
            "caption": req.caption,
            "slide_urls": req.slide_urls,
            "schedule_time": req.schedule_time,
            "status": "Pending",
            "row_index": req.row_index,
            "created_at": created_at,
            "retry_count": 0
        })
        message = f"Post {req.post_id} scheduled successfully for {req.schedule_time}."
        
    # Sync Google Sheet status and Post_Date if row_index is provided
    if req.row_index and req.source_sheet:
        config = load_env()
        creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
        sheet_id = config.get("GOOGLE_SHEET_ID")
        if os.path.exists(creds_path) and sheet_id:
            try:
                client = get_sheets_client(creds_path)
                spreadsheet = client.open_by_key(sheet_id)
                sheet = spreadsheet.worksheet(req.source_sheet)
                headers = sheet.row_values(1)
                
                cells_to_update = []
                if "Status" in headers:
                    col_idx = headers.index("Status") + 1
                    cells_to_update.append(gspread.Cell(row=req.row_index, col=col_idx, value="Scheduled"))
                if "Post_Date" in headers:
                    col_idx = headers.index("Post_Date") + 1
                    cells_to_update.append(gspread.Cell(row=req.row_index, col=col_idx, value=req.schedule_time))
                if cells_to_update:
                    sheet.update_cells(cells_to_update, value_input_option="RAW")
            except Exception as sheet_err:
                logger.warning(f"Failed to update Google Sheet for scheduled post: {sheet_err}")
                
    return {"status": "success", "message": message}

@app.get("/api/schedule/list")
def list_scheduled_posts():
    db = get_mongo_db()
    cursor = db.scheduled_posts.find().sort("schedule_time", -1)
    res = [serialize_doc(doc) for doc in cursor]
    return res

@app.post("/api/schedule/delete/{job_id}")
def delete_scheduled_post(job_id: str):
    db = get_mongo_db()
    try:
        db.scheduled_posts.delete_one({"_id": ObjectId(job_id), "status": "Pending"})
    except Exception as e:
        logger.error(f"Error deleting scheduled post {job_id}: {e}")
        raise HTTPException(status_code=400, detail="Invalid job ID format.")
    return {"status": "success"}

# Serve static files
app.mount("/assets", StaticFiles(directory="dashboard/dist/assets"), name="assets")
app.mount("/post", StaticFiles(directory="post"), name="post")

@app.get("/api/post/details")
def get_post_details(post_id: str, source_sheet: str, row_index: Optional[int] = None):
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    
    if not os.path.exists(creds_path) or not sheet_id:
        raise HTTPException(status_code=400, detail="Google Sheets configuration missing.")
        
    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet(source_sheet)
        
        row_data = None
        if row_index:
            headers = sheet.row_values(1)
            row_values = sheet.row_values(row_index)
            row_values += [""] * (len(headers) - len(row_values))
            row_data = dict(zip(headers, row_values))
            row_data["row_index"] = row_index
        else:
            records = sheet.get_all_records()
            for idx, r in enumerate(records, start=2):
                if r.get("Post_ID") == post_id:
                    row_data = r
                    row_data["row_index"] = idx
                    break
                    
        if not row_data:
            raise HTTPException(status_code=404, detail=f"Post with ID '{post_id}' not found in '{source_sheet}'.")
            
        local_slides = []
                            
        return {
            "post_id": post_id,
            "source_sheet": source_sheet,
            "row_index": row_data.get("row_index"),
            "data": row_data,
            "local_slides": local_slides
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Campaign Automation API Endpoints ────────────────────────

class BulkScheduleRequest(BaseModel):
    worksheet_name: str
    start_date: str  # YYYY-MM-DD
    posting_time: str # HH:MM
    frequency: str  # "daily", "weekday", "custom"
    interval_days: int = 1

class UnscheduleRequest(BaseModel):
    worksheet_name: str

class UpdateSingleScheduleRequest(BaseModel):
    worksheet_name: str
    post_id: str
    schedule_time: str # ISO format string

@app.get("/api/worksheets")
def get_worksheets():
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    if not os.path.exists(creds_path) or not sheet_id:
        return {"worksheets": []}
    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        # Return all worksheet titles
        titles = [w.title for w in spreadsheet.worksheets()]
        return {"worksheets": titles}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaign/posts")
def get_campaign_posts(worksheet_name: str):
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    if not os.path.exists(creds_path) or not sheet_id:
        return {"posts": []}
    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet(worksheet_name)
        records = sheet.get_all_records()
        
        # Query local database to get active scheduled times and database status
        db = get_mongo_db()
        cursor = db.scheduled_posts.find({"source_sheet": worksheet_name})
        db_schedules = {r["post_id"]: {"time": r["schedule_time"], "status": r["status"]} for r in cursor}
        
        posts = []
        for idx, r in enumerate(records, start=2):
            post_id = r.get("Post_ID")
            if not post_id:
                continue
            db_sched = db_schedules.get(post_id)
            posts.append({
                "post_id": post_id,
                "topic": r.get("Topic", "Untitled Post"),
                "sheet_status": r.get("Status"),
                "row_index": idx,
                "db_status": db_sched["status"] if db_sched else None,
                "schedule_time": db_sched["time"] if db_sched else None
            })
        return {"posts": posts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/bulk-schedule")
def bulk_schedule_campaign(req: BulkScheduleRequest):
    import datetime
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    if not os.path.exists(creds_path) or not sheet_id:
        raise HTTPException(status_code=400, detail="Google Sheets configuration missing.")
        
    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet(req.worksheet_name)
        records = sheet.get_all_records()
        headers = sheet.row_values(1)
        
        status_col_idx = None
        if "Status" in headers:
            status_col_idx = headers.index("Status") + 1
            
        post_date_col_idx = None
        if "Post_Date" in headers:
            post_date_col_idx = headers.index("Post_Date") + 1
            
        start_dt = datetime.datetime.strptime(f"{req.start_date} {req.posting_time}", "%Y-%m-%d %H:%M")
        
        db = get_mongo_db()
        
        scheduled_count = 0
        current_dt = start_dt
        
        cells_to_update = []
        
        # Find columns for Slide_1_URL to Slide_6_URL
        col_indices = {}
        for i in range(1, 7):
            col_name = f"Slide_{i}_URL"
            if col_name in headers:
                col_indices[i] = headers.index(col_name) + 1
                
        for idx, r in enumerate(records, start=2):
            post_id = r.get("Post_ID")
            if not post_id:
                continue
            sheet_status = str(r.get("Status", "")).strip().lower()
            
            # Skip already posted ones
            if sheet_status == "posted":
                continue
                
            # Prepare slide URLs from sheet columns
            slide_urls = []
            for i in range(1, 7):
                url = r.get(f"Slide_{i}_URL")
                if url:
                    slide_urls.append(url)
                    

                            
            caption = r.get("Caption", "")
            topic = r.get("Topic", "")
            schedule_time_str = current_dt.isoformat()
            
            # Delete any existing pending schedule in the DB
            db.scheduled_posts.delete_many({
                "post_id": post_id,
                "source_sheet": req.worksheet_name,
                "status": "Pending"
            })
            
            # Insert new pending schedule
            created_at = datetime.datetime.now().isoformat()
            db.scheduled_posts.insert_one({
                "post_id": post_id,
                "topic": topic,
                "source_sheet": req.worksheet_name,
                "caption": caption,
                "slide_urls": slide_urls,
                "schedule_time": schedule_time_str,
                "status": "Pending",
                "row_index": idx,
                "created_at": created_at,
                "retry_count": 0
            })
            
            # Update status in the sheet worksheet to 'Scheduled' (queue it for batch update)
            if status_col_idx:
                cells_to_update.append(gspread.Cell(row=idx, col=status_col_idx, value="Scheduled"))
            if post_date_col_idx:
                cells_to_update.append(gspread.Cell(row=idx, col=post_date_col_idx, value=schedule_time_str))
                
            scheduled_count += 1
            
            # Advance time based on frequency
            if req.frequency == "daily":
                current_dt += datetime.timedelta(days=1)
            elif req.frequency == "weekday":
                current_dt += datetime.timedelta(days=1)
                while current_dt.weekday() >= 5: # Monday is 0, Sunday is 6
                    current_dt += datetime.timedelta(days=1)
            elif req.frequency == "custom":
                current_dt += datetime.timedelta(days=req.interval_days)
                
        # Perform Google Sheets batch update
        if cells_to_update:
            sheet.update_cells(cells_to_update, value_input_option="RAW")
            
        return {
            "status": "success",
            "message": f"Successfully bulk-scheduled {scheduled_count} posts from '{req.worksheet_name}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/unschedule")
def unschedule_campaign(req: UnscheduleRequest):
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    if not os.path.exists(creds_path) or not sheet_id:
        raise HTTPException(status_code=400, detail="Google Sheets configuration missing.")
        
    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet(req.worksheet_name)
        headers = sheet.row_values(1)
        
        status_col_idx = None
        if "Status" in headers:
            status_col_idx = headers.index("Status") + 1
            
        post_date_col_idx = None
        if "Post_Date" in headers:
            post_date_col_idx = headers.index("Post_Date") + 1
            
        db = get_mongo_db()
        
        # Find all pending post rows for this campaign to revert sheet status
        cursor = db.scheduled_posts.find({
            "source_sheet": req.worksheet_name,
            "status": "Pending"
        })
        pending_jobs = list(cursor)
        
        # Delete pending jobs
        db.scheduled_posts.delete_many({
            "source_sheet": req.worksheet_name,
            "status": "Pending"
        })
        
        reverted_count = 0
        cells_to_update = []
        for job in pending_jobs:
            row_idx = job.get("row_index")
            if row_idx:
                if status_col_idx:
                    cells_to_update.append(gspread.Cell(row=row_idx, col=status_col_idx, value="Pending"))
                if post_date_col_idx:
                    cells_to_update.append(gspread.Cell(row=row_idx, col=post_date_col_idx, value=""))
                reverted_count += 1
                
        if cells_to_update:
            sheet.update_cells(cells_to_update, value_input_option="RAW")
            
        return {
            "status": "success",
            "message": f"Successfully unscheduled {reverted_count} pending posts from '{req.worksheet_name}'."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/campaign/update-single-schedule")
def update_single_schedule(req: UpdateSingleScheduleRequest):
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    if not os.path.exists(creds_path) or not sheet_id:
        raise HTTPException(status_code=400, detail="Google Sheets configuration missing.")
        
    try:
        db = get_mongo_db()
        
        # Check if a pending job already exists
        existing_job = db.scheduled_posts.find_one({
            "post_id": req.post_id,
            "source_sheet": req.worksheet_name,
            "status": "Pending"
        })
        
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet(req.worksheet_name)
        headers = sheet.row_values(1)
        
        status_col_idx = None
        if "Status" in headers:
            status_col_idx = headers.index("Status") + 1
            
        post_date_col_idx = None
        if "Post_Date" in headers:
            post_date_col_idx = headers.index("Post_Date") + 1
            
        if existing_job:
            # Check the current scheduled time to prevent updates at/near posting time
            job_time_str = existing_job.get("schedule_time")
            if job_time_str:
                job_time = datetime.fromisoformat(job_time_str)
                time_diff = (job_time - datetime.now()).total_seconds()
                if time_diff <= 60: # Within 60 seconds or in the past
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot update post schedule at or near its posting time."
                    )
            # Update the scheduled time of existing job
            db.scheduled_posts.update_one(
                {"_id": existing_job["_id"]},
                {"$set": {"schedule_time": req.schedule_time}}
            )
            
            # Sync to sheet
            if post_date_col_idx and existing_job.get("row_index"):
                sheet.update_cell(existing_job["row_index"], post_date_col_idx, req.schedule_time)
                
            return {"status": "success", "message": f"Updated scheduled time for {req.post_id}."}
        else:
            # Fetch worksheet data to find the post row and details
            records = sheet.get_all_records()
            
            col_indices = {}
            for i in range(1, 7):
                col_name = f"Slide_{i}_URL"
                if col_name in headers:
                    col_indices[i] = headers.index(col_name) + 1
                    
            found_row = None
            row_idx = None
            for idx, r in enumerate(records, start=2):
                if str(r.get("Post_ID", "")).strip() == req.post_id:
                    found_row = r
                    row_idx = idx
                    break
                    
            if not found_row:
                raise HTTPException(status_code=404, detail=f"Post '{req.post_id}' not found in campaign worksheet.")
                
            sheet_status = str(found_row.get("Status", "")).strip().lower()
            if sheet_status == "posted":
                raise HTTPException(status_code=400, detail=f"Post '{req.post_id}' is already posted.")
                
            # Prepare slide URLs
            slide_urls = []
            for i in range(1, 7):
                url = found_row.get(f"Slide_{i}_URL")
                if url:
                    slide_urls.append(url)
                    

            caption = found_row.get("Caption", "")
            topic = found_row.get("Topic", "")
            created_at = datetime.now().isoformat()
            
            # Insert new pending job
            db.scheduled_posts.insert_one({
                "post_id": req.post_id,
                "topic": topic,
                "source_sheet": req.worksheet_name,
                "caption": caption,
                "slide_urls": slide_urls,
                "schedule_time": req.schedule_time,
                "status": "Pending",
                "row_index": row_idx,
                "created_at": created_at,
                "retry_count": 0
            })
            
            # Update sheet status to 'Scheduled' and update Slide URLs and Post_Date in batch
            cells_to_update = []
            if status_col_idx:
                cells_to_update.append(gspread.Cell(row=row_idx, col=status_col_idx, value="Scheduled"))
            if post_date_col_idx:
                cells_to_update.append(gspread.Cell(row=row_idx, col=post_date_col_idx, value=req.schedule_time))
                
            # Update Slide URLs if they are currently not Cloudinary URLs or not populated
            for i, uploaded_url in enumerate(slide_urls, start=1):
                if i in col_indices:
                    cells_to_update.append(gspread.Cell(row=row_idx, col=col_indices[i], value=uploaded_url))
            
            if cells_to_update:
                sheet.update_cells(cells_to_update, value_input_option="RAW")
                
            return {"status": "success", "message": f"Successfully scheduled post {req.post_id} for {req.schedule_time}."}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/campaigns/overview")
def get_campaigns_overview():
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    if not os.path.exists(creds_path) or not sheet_id:
        return {"campaigns": [], "today_posts": []}
        
    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        worksheets = [w.title for w in spreadsheet.worksheets() if w.title != "Queue"]
        
        db = get_mongo_db()
        
        # Get today's range in local time
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat()
        end_of_today = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat()
        
        cursor_today = db.scheduled_posts.find({
            "schedule_time": {"$gte": start_of_today, "$lte": end_of_today}
        }).sort("schedule_time", 1)
        today_posts = [serialize_doc(doc) for doc in cursor_today]
            
        campaigns_data = []
        for w_title in worksheets:
            try:
                sheet = spreadsheet.worksheet(w_title)
                records = sheet.get_all_records()
                total_posts = len(records)
                
                # Fetch DB statuses for stats
                cursor_stat = db.scheduled_posts.find({"source_sheet": w_title})
                db_statuses = {row["post_id"]: row["status"] for row in cursor_stat}
                
                posted_count = 0
                scheduled_count = 0
                pending_count = 0
                
                for r in records:
                    p_id = r.get("Post_ID")
                    if not p_id:
                        continue
                    sh_status = str(r.get("Status", "")).strip().lower()
                    db_status = db_statuses.get(p_id)
                    
                    if sh_status == "posted" or db_status == "Success":
                        posted_count += 1
                    elif db_status == "Pending" or sh_status == "scheduled":
                        scheduled_count += 1
                    else:
                        pending_count += 1
                        
                campaigns_data.append({
                    "worksheet_name": w_title,
                    "campaign_name": "50-Day D2C Automation" if w_title == "50DaysCampaign" else w_title,
                    "total_posts": total_posts,
                    "posted": posted_count,
                    "scheduled": scheduled_count,
                    "pending": pending_count
                })
            except Exception as w_err:
                logger.error(f"Error processing worksheet {w_title}: {w_err}")
                
        return {
            "campaigns": campaigns_data,
            "today_posts": today_posts
        }
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/dashboard")
def get_system_dashboard_data():
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    
    # Defaults
    google_sheet_configured = os.path.exists(creds_path) and bool(sheet_id)
    cloudinary_configured = bool(config.get("CLOUDINARY_API_KEY"))
    instagram_configured = bool(config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")) and bool(config.get("INSTAGRAM_ACCESS_TOKEN"))
    
    db = get_mongo_db()
    
    # Check if MongoDB is connected
    mongodb_configured = False
    try:
        db.command("ping")
        mongodb_configured = True
    except Exception:
        pass
        
    # 1. Fetch DB scheduler stats
    db_stats = {"Pending": 0, "Posting": 0, "Success": 0, "Failed": 0}
    try:
        pipeline = [{"$group": {"_id": "$status", "cnt": {"$sum": 1}}}]
        results = db.scheduled_posts.aggregate(pipeline)
        for r in results:
            status = r["_id"]
            if status in db_stats:
                db_stats[status] = r["cnt"]
    except Exception as e:
        logger.error(f"Error fetching MongoDB stats: {e}")
            
    # Get last 10 jobs
    try:
        cursor_recent = db.scheduled_posts.find().sort("schedule_time", -1).limit(10)
        recent_jobs = [serialize_doc(doc) for doc in cursor_recent]
    except Exception as e:
        logger.error(f"Error fetching recent jobs: {e}")
        recent_jobs = []
        
    # Get today's combined schedule
    try:
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat()
        end_of_today = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat()
        cursor_today = db.scheduled_posts.find({
            "schedule_time": {"$gte": start_of_today, "$lte": end_of_today}
        }).sort("schedule_time", 1)
        today_schedule = [serialize_doc(doc) for doc in cursor_today]
    except Exception as e:
        logger.error(f"Error fetching today schedule: {e}")
        today_schedule = []
        
    # 2. Fetch Google Sheets stats (Campaigns + Queue)
    campaigns_data = []
    queue_stats = {"total": 0, "posted": 0, "approved": 0, "pending": 0}
    
    if google_sheet_configured:
        try:
            client = get_sheets_client(creds_path)
            spreadsheet = client.open_by_key(sheet_id)
            
            # Fetch Queue statistics
            try:
                queue_sheet = spreadsheet.worksheet("Queue")
                queue_records = queue_sheet.get_all_records()
                queue_stats["total"] = len(queue_records)
                for r in queue_records:
                    status = str(r.get("Status", "")).strip().lower()
                    if status == "posted":
                        queue_stats["posted"] += 1
                    elif status == "approved":
                        queue_stats["approved"] += 1
                    else:
                        queue_stats["pending"] += 1
            except Exception as q_err:
                logger.error(f"Error reading Queue stats: {q_err}")
                
            # Fetch Campaign statistics
            worksheets = [w.title for w in spreadsheet.worksheets() if w.title != "Queue"]
            for w_title in worksheets:
                try:
                    sheet = spreadsheet.worksheet(w_title)
                    records = sheet.get_all_records()
                    total_posts = len(records)
                    
                    # Fetch DB statuses for this sheet to compute stats
                    cursor_stat = db.scheduled_posts.find({"source_sheet": w_title})
                    db_statuses = {row["post_id"]: row["status"] for row in cursor_stat}
                    
                    posted = 0
                    scheduled = 0
                    pending = 0
                    for r in records:
                        p_id = r.get("Post_ID")
                        if not p_id:
                            continue
                        sh_status = str(r.get("Status", "")).strip().lower()
                        db_status = db_statuses.get(p_id)
                        
                        if sh_status == "posted" or db_status == "Success":
                            posted += 1
                        elif db_status == "Pending" or sh_status == "scheduled":
                            scheduled += 1
                        else:
                            pending += 1
                            
                    campaigns_data.append({
                        "worksheet_name": w_title,
                        "campaign_name": "50-Day D2C Automation" if w_title == "50DaysCampaign" else w_title,
                        "total_posts": total_posts,
                        "posted": posted,
                        "scheduled": scheduled,
                        "pending": pending
                    })
                except Exception as w_err:
                    logger.error(f"Error reading campaign stats for {w_title}: {w_err}")
        except Exception as sheet_err:
            logger.error(f"Error connecting to Google Sheets: {sheet_err}")
            
    return {
        "integrations": {
            "google_sheets": google_sheet_configured,
            "cloudinary": cloudinary_configured,
            "mongodb": mongodb_configured,
            "instagram": instagram_configured,
            "instagram_account": "@goran.dotin" if instagram_configured else "Not Configured",
            "token_status": get_cached_token_status(config.get("INSTAGRAM_ACCESS_TOKEN")) if instagram_configured else None
        },
        "database_stats": db_stats,
        "campaigns": campaigns_data,
        "queue": queue_stats,
        "today_schedule": today_schedule,
        "recent_jobs": recent_jobs
    }

@app.post("/api/ideas/seed")
def seed_brand_ideas():
    config = load_env()
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    
    if not os.path.exists(creds_path) or not sheet_id:
        raise HTTPException(status_code=400, detail="Google Sheets configuration missing.")
        
    try:
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet("Queue")
        
        # 5 fresh brand-aligned ideas (NOT AI for D2C)
        new_ideas = [
            {
                "Post_ID": "random_no_code_limits",
                "Topic": "The limits of No-Code: When you should build custom code instead",
                "Caption": (
                    "No-code tools like Zapier and Make are amazing. Until they aren't. 🛑💻\n\n"
                    "We build millions of automations, and here is when we advise clients to ditch Make/Zapier and write Python/NodeJS instead:\n\n"
                    "1️⃣ High Volume Data Processing\n"
                    "→ If you are running 100,000 tasks/month, Zapier bills will eat your margin. A custom script on AWS Lambda costs pennies.\n\n"
                    "2️⃣ Complex Business Logic\n"
                    "→ Nested if-else filters, loops, and custom error handling are a nightmare to maintain in visual builders. Code is cleaner, version-controlled, and testable.\n\n"
                    "3️⃣ Intellectual Property (IP)\n"
                    "→ If your automation is core to your business value, you shouldn't lease it from a third-party builder. Code it, own it.\n\n"
                    "The best tech stack is hybrid: No-code for fast prototyping, custom code for scale.\n\n"
                    "#NoCode #SoftwareEngineering #Python #Scalability #TechStack #GoRanAI"
                ),
                "Status": "Approved"
            },
            {
                "Post_ID": "random_automated_reports",
                "Topic": "How we automated our client reporting — saving 10 hours every week",
                "Caption": (
                    "Client reporting is the ultimate time sink. ⏰📊\n\n"
                    "We used to spend Friday mornings compiling metrics, styling PDFs, and writing summaries. Now, it's 100% automated.\n\n"
                    "Our stack:\n"
                    "1️⃣ Data Collector: Scripts pull weekly metrics from Cloudinary, SQLite, and Meta APIs.\n"
                    "2️⃣ Template Engine: ReportLab generates a brand-aligned, professional PDF.\n"
                    "3️⃣ Delivery: Slack webhook alerts our team, and Gmail API drafts the email to the client.\n\n"
                    "Result: Zero friction, 100% accurate metrics, and 10 hours back to work on what matters.\n\n"
                    "Stop doing manual copy-paste work. If you repeat it every week, automate it.\n\n"
                    "#AgencyOps #BusinessAutomation #ReportLab #ProductivityHacks #GoRanAI"
                ),
                "Status": "Approved"
            },
            {
                "Post_ID": "random_ai_safety_privacy",
                "Topic": "Data Privacy in the age of AI: How to keep your client data secure",
                "Caption": (
                    "Using OpenAI for client data? You might be leaking IP. 🔒⚠️\n\n"
                    "Here's how we keep data secure at GoRan AI:\n\n"
                    "1️⃣ Zero Data Retention (ZDR) APIs\n"
                    "→ We use API endpoints with ZDR guarantees (like OpenAI API, Anthropic API, or Google Vertex AI) instead of consumer web interfaces. Your data is NEVER used for training.\n\n"
                    "2️⃣ Local Open-Source Models\n"
                    "→ For highly sensitive client data, we host models (like Llama 3) locally on private secure cloud instances.\n\n"
                    "3️⃣ Anonymization Pipelines\n"
                    "→ Automatically scrub names, emails, and financial details before sending data to external APIs.\n\n"
                    "Security is not an afterthought in automation. It is the foundation.\n\n"
                    "#DataPrivacy #AICloseup #InformationSecurity #Llama3 #AIAgency #GoRanAI"
                ),
                "Status": "Approved"
            },
            {
                "Post_ID": "random_hiring_for_automation",
                "Topic": "Hiring a 'Chief Automation Officer' — why your company needs one in 2026",
                "Caption": (
                    "Hiring managers, software developers, designers... but who owns your operational efficiency? 💼🤖\n\n"
                    "In 2026, the companies winning aren't those hiring the most heads. They are those leveraging system architects.\n\n"
                    "Why you need a Chief Automation Officer (CAO) / Operations Engineer:\n"
                    "→ They connect siloed departments (Sales, Marketing, HR) through unified pipelines.\n"
                    "→ They audit manual work and eliminate redundancies.\n"
                    "→ They build the enterprise 'operating system' that lets humans focus on high-leverage tasks.\n\n"
                    "Scale your systems, not your headcount.\n\n"
                    "#Hiring #Operations #Efficiency #BusinessStrategy #ChiefAutomationOfficer #GoRanAI"
                ),
                "Status": "Approved"
            },
            {
                "Post_ID": "random_systems_over_goals",
                "Topic": "Systems vs. Goals: Why a solid workflow beats a target sheet every time",
                "Caption": (
                    "Goals tell you where you want to go. Systems get you there. 🎯⚙️\n\n"
                    "We see startups setting massive targets (e.g., 'Publish 30 carousels a month') without setting up the workflow to make it happen.\n\n"
                    "Without an automated pipeline:\n"
                    "→ Creators miss deadlines.\n"
                    "→ Captions are rushed on the day of posting.\n"
                    "→ High-stress, low-quality output.\n\n"
                    "With an automated system (like our GoRan AI Scheduler):\n"
                    "→ Templates are auto-generated.\n"
                    "→ Sheets sync to the database automatically.\n"
                    "→ Posts go live on schedule, even when the team is asleep.\n\n"
                    "Stop obsessing over goals. Start designing systems.\n\n"
                    "#SystemsThinking #Operations #GoalSetting #StartupTips #GoRanAI"
                ),
                "Status": "Approved"
            }
        ]
        
        headers = sheet.row_values(1)
        existing_records = sheet.get_all_records()
        existing_post_ids = {str(r.get("Post_ID", "")).strip() for r in existing_records}
        
        added_count = 0
        for idea in new_ideas:
            if idea["Post_ID"] in existing_post_ids:
                continue
            row = []
            for h in headers:
                row.append(idea.get(h, ""))
            sheet.append_row(row, value_input_option="RAW")
            added_count += 1
            
        return {
            "status": "success",
            "message": f"Successfully seeded {added_count} brand-aligned post ideas to the Queue worksheet."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Health Check ─────────────────────────────────────────────
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "goran-instagram-scheduler"}

@app.get("/", response_class=HTMLResponse)
def serve_index():
    try:
        with open("dashboard/dist/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend build missing</h1><p>Please run <code>npm run build</code> in the frontend folder.</p>", status_code=404)

@app.post("/api/publish/now")
async def publish_now(req: PublishNowRequest):
    config = load_env()
    account_id = config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    token = config.get("INSTAGRAM_ACCESS_TOKEN")
    creds_path = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    sheet_id = config.get("GOOGLE_SHEET_ID")
    
    if not account_id or not token:
        raise HTTPException(status_code=400, detail="Instagram Business Account ID or Access Token is missing.")
        
    try:
        # 1. Ensure all URLs are Cloudinary URLs (auto-upload local paths)
        slide_urls = await asyncio.to_thread(ensure_cloudinary_urls, req.slide_urls, req.post_id)
        
        # 2. Publish immediately
        if len(slide_urls) == 1:
            published_id = await asyncio.to_thread(publish_single_post, slide_urls[0], req.caption, account_id, token)
        else:
            published_id = await asyncio.to_thread(publish_carousel_post, slide_urls, req.caption, account_id, token)
            
        # 3. Insert/Update schedule entry in MongoDB database as 'Success'
        db = get_mongo_db()
        created_at = datetime.now().isoformat()
        
        existing = db.scheduled_posts.find_one({
            "post_id": req.post_id,
            "source_sheet": req.source_sheet,
            "status": "Pending"
        })
        
        if existing:
            db.scheduled_posts.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "status": "Success",
                    "published_id": published_id,
                    "slide_urls": slide_urls,
                    "caption": req.caption
                }}
            )
        else:
            db.scheduled_posts.insert_one({
                "post_id": req.post_id,
                "topic": req.post_id,
                "source_sheet": req.source_sheet,
                "caption": req.caption,
                "slide_urls": slide_urls,
                "schedule_time": created_at,
                "status": "Success",
                "published_id": published_id,
                "row_index": req.row_index,
                "created_at": created_at,
                "retry_count": 0
            })
        
        # 4. Update Google Sheet status to 'Posted' and URLs if needed
        if os.path.exists(creds_path) and sheet_id and req.row_index:
            try:
                def update_sheet():
                    client = get_sheets_client(creds_path)
                    spreadsheet = client.open_by_key(sheet_id)
                    sheet = spreadsheet.worksheet(req.source_sheet)
                    headers = sheet.row_values(1)
                    
                    cells_to_update = []
                    if "Status" in headers:
                        col_idx = headers.index("Status") + 1
                        cells_to_update.append(gspread.Cell(row=req.row_index, col=col_idx, value="Posted"))
                    if "Post_Date" in headers:
                        col_idx = headers.index("Post_Date") + 1
                        cells_to_update.append(gspread.Cell(row=req.row_index, col=col_idx, value=datetime.now().isoformat()))
                    
                    # Update columns for Slide_1_URL to Slide_6_URL
                    for i in range(1, 7):
                        col_name = f"Slide_{i}_URL"
                        if col_name in headers:
                            col_idx = headers.index(col_name) + 1
                            if i - 1 < len(slide_urls):
                                cells_to_update.append(gspread.Cell(row=req.row_index, col=col_idx, value=slide_urls[i - 1]))
                                
                    if cells_to_update:
                        sheet.update_cells(cells_to_update, value_input_option="RAW")
                        
                await asyncio.to_thread(update_sheet)
            except Exception as sheet_err:
                logger.warning(f"Failed to update Google Sheet for immediate post: {sheet_err}")
                
        return {"status": "success", "published_id": published_id}
        
    except Exception as e:
        logger.error(f"Immediate publish failed for {req.post_id}: {e}")
        try:
            db = get_mongo_db()
            existing = db.scheduled_posts.find_one({
                "post_id": req.post_id,
                "source_sheet": req.source_sheet,
                "status": "Pending"
            })
            if existing:
                db.scheduled_posts.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "status": "Failed",
                        "error_message": str(e)
                    }}
                )
            else:
                created_at = datetime.now().isoformat()
                db.scheduled_posts.insert_one({
                    "post_id": req.post_id,
                    "topic": req.post_id,
                    "source_sheet": req.source_sheet,
                    "caption": req.caption,
                    "slide_urls": req.slide_urls,
                    "schedule_time": created_at,
                    "status": "Failed",
                    "error_message": str(e),
                    "row_index": req.row_index,
                    "created_at": created_at,
                    "retry_count": 0
                })
        except Exception as db_err:
            logger.error(f"Failed to update DB failure state: {db_err}")
            
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/preview", response_class=HTMLResponse)
def serve_preview():
    try:
        with open("dashboard/dist/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend build missing</h1><p>Please run <code>npm run build</code> in the frontend folder.</p>", status_code=404)


