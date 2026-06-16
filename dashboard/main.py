import os
import sys
import json
import time
import sqlite3
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
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

DB_PATH = "dashboard/scheduler.db"
ENV_FILE = ".env"

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
    
    yield  # Application runs
    
    # Shutdown: cancel the scheduler
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    logger.info("Scheduler worker stopped.")

app = FastAPI(title="GoRan AI Instagram Scheduler Dashboard", lifespan=lifespan)

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
    return config

# ─── Database Initialization ──────────────────────────────────
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Scheduled posts table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id TEXT,
            topic TEXT,
            source_sheet TEXT,
            caption TEXT,
            slide_urls TEXT, -- JSON string list of Cloudinary/image URLs
            schedule_time TEXT, -- ISO format timestamp
            status TEXT DEFAULT 'Pending', -- 'Pending', 'Posting', 'Success', 'Failed'
            published_id TEXT,
            error_message TEXT,
            row_index INTEGER,
            created_at TEXT
        )
    """)
    conn.commit()
    conn.close()

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
    resp = requests.post(url, data=payload)
    if resp.status_code != 200:
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
        resp = requests.post(item_url, data=payload)
        if resp.status_code != 200:
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
def _sync_publish_job(job_dict, account_id, token, creds_path, sheet_id):
    """Synchronous publish logic — runs in a thread to avoid blocking the event loop."""
    job_id = job_dict["id"]
    post_id = job_dict["post_id"]
    caption = job_dict["caption"]
    slide_urls = json.loads(job_dict["slide_urls"])
    source_sheet = job_dict["source_sheet"]
    row_index = job_dict["row_index"]

    # Update status to Posting
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE scheduled_posts SET status = 'Posting' WHERE id = ?", (job_id,))
    conn.commit()

    try:
        # Publish single image vs. carousel
        if len(slide_urls) == 1:
            published_id = publish_single_post(slide_urls[0], caption, account_id, token)
        else:
            published_id = publish_carousel_post(slide_urls, caption, account_id, token)

        # Mark database success
        cursor.execute(
            "UPDATE scheduled_posts SET status = 'Success', published_id = ? WHERE id = ?",
            (published_id, job_id)
        )
        conn.commit()
        logger.info(f"Successfully published Job {job_id} (Post {post_id}). Instagram ID: {published_id}")

        # Update Google Sheet status to 'Posted' if credentials available
        client = get_sheets_client(creds_path)
        if client and sheet_id and row_index:
            try:
                spreadsheet = client.open_by_key(sheet_id)
                sheet = spreadsheet.worksheet(source_sheet)
                headers = sheet.row_values(1)
                if "Status" in headers:
                    col_idx = headers.index("Status") + 1
                    sheet.update_cell(row_index, col_idx, "Posted")
            except Exception as sheet_err:
                logger.warning(f"Failed to update Google Sheet status for Job {job_id}: {sheet_err}")

    except Exception as ex:
        logger.error(f"Publish error on Job {job_id}: {ex}")
        cursor.execute(
            "UPDATE scheduled_posts SET status = 'Failed', error_message = ? WHERE id = ?",
            (str(ex), job_id)
        )
        conn.commit()
    finally:
        conn.close()

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

            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Find posts scheduled for now or in the past that are 'Pending'
            now_str = datetime.now().isoformat()
            cursor.execute(
                "SELECT * FROM scheduled_posts WHERE status = 'Pending' AND schedule_time <= ?",
                (now_str,)
            )
            jobs = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            for job in jobs:
                logger.info(f"Starting publish job {job['id']} for Post {job['post_id']}")
                # Run the blocking publish in a thread so the event loop stays responsive
                await asyncio.to_thread(
                    _sync_publish_job, job, account_id, token, creds_path, sheet_id
                )

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

@app.get("/api/config")
def get_dashboard_config():
    config = load_env()
    creds_exist = os.path.exists(config.get("GOOGLE_CREDS_FILE", "google_service_account.json"))
    return {
        "google_sheet_id": config.get("GOOGLE_SHEET_ID", "Not Configured"),
        "google_creds_configured": creds_exist,
        "instagram_account_id": config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "Not Configured"),
        "cloudinary_configured": bool(config.get("CLOUDINARY_API_KEY"))
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
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    
    cursor.execute(
        """
        INSERT INTO scheduled_posts 
        (post_id, topic, source_sheet, caption, slide_urls, schedule_time, status, row_index, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
        """,
        (
            req.post_id,
            req.topic,
            req.source_sheet,
            req.caption,
            json.dumps(req.slide_urls),
            req.schedule_time,
            req.row_index,
            created_at
        )
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Post {req.post_id} scheduled successfully for {req.schedule_time}."}

@app.get("/api/schedule/list")
def list_scheduled_posts():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scheduled_posts ORDER BY schedule_time DESC")
    rows = cursor.fetchall()
    conn.close()
    
    res = []
    for r in rows:
        d = dict(r)
        d["slide_urls"] = json.loads(d["slide_urls"])
        res.append(d)
    return res

@app.post("/api/schedule/delete/{job_id}")
def delete_scheduled_post(job_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM scheduled_posts WHERE id = ? AND status = 'Pending'", (job_id,))
    conn.commit()
    conn.close()
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
        safe_post_id = os.path.basename(post_id)
        post_dir = os.path.join("post", safe_post_id)
        if os.path.exists(post_dir) and os.path.isdir(post_dir):
            files = sorted([f for f in os.listdir(post_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
            local_slides = [f"/post/{safe_post_id}/{f}" for f in files]
        else:
            post_temp_dir = os.path.join("post", "post_temp")
            if os.path.exists(post_temp_dir) and os.path.isdir(post_temp_dir):
                files = sorted([f for f in os.listdir(post_temp_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                meta_file = "post_temp_meta.json"
                if os.path.exists(meta_file):
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                        if meta.get("Post_ID") == post_id:
                            local_slides = [f"/post/post_temp/{f}" for f in files]
                            
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
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT post_id, schedule_time, status FROM scheduled_posts WHERE source_sheet = ?", 
            (worksheet_name,)
        )
        db_schedules = {r["post_id"]: {"time": r["schedule_time"], "status": r["status"]} for r in cursor.fetchall()}
        conn.close()
        
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
            
        start_dt = datetime.datetime.strptime(f"{req.start_date} {req.posting_time}", "%Y-%m-%d %H:%M")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        scheduled_count = 0
        current_dt = start_dt
        
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
                    
            # Fallback to local files if slide URLs not in sheet yet
            if not slide_urls:
                safe_post_id = os.path.basename(post_id)
                post_dir = os.path.join("post", safe_post_id)
                if os.path.exists(post_dir) and os.path.isdir(post_dir):
                    files = sorted([f for f in os.listdir(post_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                    slide_urls = [f"/post/{safe_post_id}/{f}" for f in files]
                    
            caption = r.get("Caption", "")
            topic = r.get("Topic", "")
            schedule_time_str = current_dt.isoformat()
            
            # Delete any existing pending schedule in the local DB
            cursor.execute(
                "DELETE FROM scheduled_posts WHERE post_id = ? AND source_sheet = ? AND status = 'Pending'",
                (post_id, req.worksheet_name)
            )
            
            # Insert new pending schedule
            created_at = datetime.datetime.now().isoformat()
            cursor.execute(
                """
                INSERT INTO scheduled_posts 
                (post_id, topic, source_sheet, caption, slide_urls, schedule_time, status, row_index, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
                """,
                (
                    post_id,
                    topic,
                    req.worksheet_name,
                    caption,
                    json.dumps(slide_urls),
                    schedule_time_str,
                    idx,
                    created_at
                )
            )
            
            # Update status in the sheet worksheet to 'Scheduled'
            if status_col_idx:
                sheet.update_cell(idx, status_col_idx, "Scheduled")
                
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
                
        conn.commit()
        conn.close()
        
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
            
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Find all pending post rows for this campaign to revert sheet status
        cursor.execute(
            "SELECT post_id, row_index FROM scheduled_posts WHERE source_sheet = ? AND status = 'Pending'",
            (req.worksheet_name,)
        )
        pending_jobs = cursor.fetchall()
        
        # Delete pending jobs
        cursor.execute(
            "DELETE FROM scheduled_posts WHERE source_sheet = ? AND status = 'Pending'",
            (req.worksheet_name,)
        )
        
        reverted_count = 0
        for job in pending_jobs:
            row_idx = job[1]
            if status_col_idx and row_idx:
                sheet.update_cell(row_idx, status_col_idx, "Pending")
                reverted_count += 1
                
        conn.commit()
        conn.close()
        
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
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if a pending job already exists
        cursor.execute(
            "SELECT id FROM scheduled_posts WHERE post_id = ? AND source_sheet = ? AND status = 'Pending'",
            (req.post_id, req.worksheet_name)
        )
        existing_job = cursor.fetchone()
        
        client = get_sheets_client(creds_path)
        spreadsheet = client.open_by_key(sheet_id)
        sheet = spreadsheet.worksheet(req.worksheet_name)
        
        if existing_job:
            # Check the current scheduled time to prevent updates at/near posting time
            cursor.execute(
                "SELECT schedule_time FROM scheduled_posts WHERE id = ?",
                (existing_job[0],)
            )
            job_time_str = cursor.fetchone()[0]
            if job_time_str:
                job_time = datetime.fromisoformat(job_time_str)
                time_diff = (job_time - datetime.now()).total_seconds()
                if time_diff <= 60: # Within 60 seconds or in the past
                    conn.close()
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot update post schedule at or near its posting time."
                    )
            # Update the scheduled time of existing job
            cursor.execute(
                "UPDATE scheduled_posts SET schedule_time = ? WHERE post_id = ? AND source_sheet = ? AND status = 'Pending'",
                (req.schedule_time, req.post_id, req.worksheet_name)
            )
            conn.commit()
            conn.close()
            return {"status": "success", "message": f"Updated scheduled time for {req.post_id}."}
        else:
            # Fetch worksheet data to find the post row and details
            records = sheet.get_all_records()
            headers = sheet.row_values(1)
            
            status_col_idx = None
            if "Status" in headers:
                status_col_idx = headers.index("Status") + 1
                
            found_row = None
            row_idx = None
            for idx, r in enumerate(records, start=2):
                if str(r.get("Post_ID", "")).strip() == req.post_id:
                    found_row = r
                    row_idx = idx
                    break
                    
            if not found_row:
                conn.close()
                raise HTTPException(status_code=404, detail=f"Post '{req.post_id}' not found in campaign worksheet.")
                
            sheet_status = str(found_row.get("Status", "")).strip().lower()
            if sheet_status == "posted":
                conn.close()
                raise HTTPException(status_code=400, detail=f"Post '{req.post_id}' is already posted.")
                
            # Prepare slide URLs
            slide_urls = []
            for i in range(1, 7):
                url = found_row.get(f"Slide_{i}_URL")
                if url:
                    slide_urls.append(url)
                    
            if not slide_urls:
                safe_post_id = os.path.basename(req.post_id)
                post_dir = os.path.join("post", safe_post_id)
                if os.path.exists(post_dir) and os.path.isdir(post_dir):
                    files = sorted([f for f in os.listdir(post_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
                    slide_urls = [f"/post/{safe_post_id}/{f}" for f in files]
                    
            caption = found_row.get("Caption", "")
            topic = found_row.get("Topic", "")
            created_at = datetime.now().isoformat()
            
            # Insert new pending job
            cursor.execute(
                """
                INSERT INTO scheduled_posts 
                (post_id, topic, source_sheet, caption, slide_urls, schedule_time, status, row_index, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
                """,
                (
                    req.post_id,
                    topic,
                    req.worksheet_name,
                    caption,
                    json.dumps(slide_urls),
                    req.schedule_time,
                    row_idx,
                    created_at
                )
            )
            
            # Update sheet status to 'Scheduled'
            if status_col_idx:
                sheet.update_cell(row_idx, status_col_idx, "Scheduled")
                
            conn.commit()
            conn.close()
            return {"status": "success", "message": f"Successfully scheduled post {req.post_id} for {req.schedule_time}."}
            
    except HTTPException:
        raise
    except Exception as e:
        if 'conn' in locals() and conn:
            conn.close()
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
        
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get today's range in local time
        now = datetime.now()
        start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat()
        end_of_today = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat()
        
        cursor.execute(
            "SELECT * FROM scheduled_posts WHERE schedule_time >= ? AND schedule_time <= ? ORDER BY schedule_time ASC",
            (start_of_today, end_of_today)
        )
        today_rows = cursor.fetchall()
        today_posts = []
        for r in today_rows:
            d = dict(r)
            d["slide_urls"] = json.loads(d["slide_urls"])
            today_posts.append(d)
            
        campaigns_data = []
        for w_title in worksheets:
            try:
                sheet = spreadsheet.worksheet(w_title)
                records = sheet.get_all_records()
                total_posts = len(records)
                
                # Fetch DB statuses for stats
                cursor.execute(
                    "SELECT post_id, status FROM scheduled_posts WHERE source_sheet = ?",
                    (w_title,)
                )
                db_statuses = {row["post_id"]: row["status"] for row in cursor.fetchall()}
                
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
                print(f"Error processing worksheet {w_title}: {w_err}")
                
        conn.close()
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
    
    # 1. Fetch DB scheduler stats
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, COUNT(*) as cnt FROM scheduled_posts GROUP BY status")
    db_stats = {"Pending": 0, "Posting": 0, "Success": 0, "Failed": 0}
    for r in cursor.fetchall():
        status = r["status"]
        if status in db_stats:
            db_stats[status] = r["cnt"]
            
    # Get last 10 jobs
    cursor.execute("SELECT * FROM scheduled_posts ORDER BY schedule_time DESC LIMIT 10")
    recent_rows = cursor.fetchall()
    recent_jobs = []
    for r in recent_rows:
        d = dict(r)
        d["slide_urls"] = json.loads(d["slide_urls"])
        recent_jobs.append(d)
        
    # Get today's combined schedule
    now = datetime.now()
    start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0).isoformat()
    end_of_today = datetime(now.year, now.month, now.day, 23, 59, 59).isoformat()
    cursor.execute(
        "SELECT * FROM scheduled_posts WHERE schedule_time >= ? AND schedule_time <= ? ORDER BY schedule_time ASC",
        (start_of_today, end_of_today)
    )
    today_rows = cursor.fetchall()
    today_schedule = []
    for r in today_rows:
        d = dict(r)
        d["slide_urls"] = json.loads(d["slide_urls"])
        today_schedule.append(d)
        
    conn.close()
    
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
                    
                    # Fetch SQLite schedules for this sheet to compute stats
                    conn = sqlite3.connect(DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    cursor.execute("SELECT post_id, status FROM scheduled_posts WHERE source_sheet = ?", (w_title,))
                    db_statuses = {row["post_id"]: row["status"] for row in cursor.fetchall()}
                    conn.close()
                    
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
            "instagram": instagram_configured,
            "instagram_account": "@goran.dotin" if instagram_configured else "Not Configured"
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

@app.get("/preview", response_class=HTMLResponse)
def serve_preview():
    try:
        with open("dashboard/dist/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Frontend build missing</h1><p>Please run <code>npm run build</code> in the frontend folder.</p>", status_code=404)

