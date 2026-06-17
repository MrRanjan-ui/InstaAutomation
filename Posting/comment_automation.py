import os
import sys
import json
import logging
import asyncio
import requests
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from bson import ObjectId
from pymongo import MongoClient

# Add project root to path if not present to ensure imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import load_env, PROJECT_ROOT

logger = logging.getLogger("goran-comment-automation")
router = APIRouter()

# ─── Database Helpers ─────────────────────────────────────────

def get_db():
    config = load_env()
    mongo_uri = config.get("MONGO_URI", "mongodb://localhost:27017")
    if "<db_password>" in mongo_uri or "<" in mongo_uri or ">" in mongo_uri:
        raise ValueError("MongoDB URI is not configured correctly.")
    
    # URL escape username and password if necessary
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
            new_netloc = f"{escaped_username}:{escaped_password}@{hosts}" if escaped_username else hosts
            mongo_uri = urlunsplit((split_uri.scheme, new_netloc, split_uri.path, split_uri.query, split_uri.fragment))
    except Exception as e:
        logger.warning(f"Failed to parse and escape MongoDB URI: {e}")
        
    client = MongoClient(mongo_uri)
    return client["goran_ai"]

def init_collections():
    try:
        db = get_db()
        db.auto_dm_rules.create_index("post_id")
        db.processed_comments.create_index("comment_id", unique=True)
        db.processed_comments.create_index("username")
        logger.info("Comment Automation MongoDB collections initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Comment Automation collections: {e}")

# Call init_collections on load
try:
    init_collections()
except Exception:
    pass

# Helper to serialize Mongo docs
def serialize_mongo(doc):
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(d["_id"])
    del d["_id"]
    return d

# ─── Meta Graph API Helpers ───────────────────────────────────

def get_page_info(instagram_account_id: str, token: str):
    """
    Fetch Facebook Page ID and Page Access Token connected to the Instagram Business Account ID.
    """
    config = load_env()
    
    # 0. Check if explicitly defined in env
    page_id = config.get("INSTAGRAM_PAGE_ID")
    if page_id:
        logger.info(f"Using explicitly configured INSTAGRAM_PAGE_ID: {page_id}")
        # Try fetching the Page Access Token for this configured Page ID
        try:
            page_url = f"https://graph.facebook.com/v19.0/{page_id}"
            page_params = {
                "fields": "access_token",
                "access_token": token
            }
            resp = requests.get(page_url, params=page_params)
            if resp.status_code == 200:
                page_token = resp.json().get("access_token") or token
                return page_id, page_token
        except Exception as e:
            logger.error(f"Failed to fetch Page Access Token for configured Page ID {page_id}: {e}")
        return page_id, token

    # 1. Standard approach: Query the /me/accounts endpoint
    url = f"https://graph.facebook.com/v19.0/me/accounts?fields=name,id,access_token,instagram_business_account{{id}}&access_token={token}"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            pages = resp.json().get("data", [])
            for page in pages:
                ig_acct = page.get("instagram_business_account")
                if ig_acct and ig_acct.get("id") == instagram_account_id:
                    logger.info(f"Auto-resolved Page ID from /me/accounts: {page['id']}")
                    return page["id"], page.get("access_token") or token
    except Exception as e:
        logger.error(f"Error checking /me/accounts: {e}")

    # 2. Fallback: Parse token debug info to find target Page IDs (useful for Business Manager tokens)
    debug_url = f"https://graph.facebook.com/debug_token"
    debug_params = {
        "input_token": token,
        "access_token": token
    }
    try:
        resp = requests.get(debug_url, params=debug_params)
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            granular_scopes = data.get("granular_scopes", [])
            page_ids = set()
            for scope_obj in granular_scopes:
                scope_name = scope_obj.get("scope", "")
                if "page" in scope_name or "pages" in scope_name:
                    for tid in scope_obj.get("target_ids", []):
                        page_ids.add(tid)
            
            # Query each resolved Page ID to check its connected Instagram account
            for pid in page_ids:
                page_url = f"https://graph.facebook.com/v19.0/{pid}"
                page_params = {
                    "fields": "id,name,instagram_business_account,access_token",
                    "access_token": token
                }
                page_resp = requests.get(page_url, params=page_params)
                if page_resp.status_code == 200:
                    page_data = page_resp.json()
                    ig_acct = page_data.get("instagram_business_account")
                    if ig_acct and ig_acct.get("id") == instagram_account_id:
                        page_token = page_data.get("access_token") or token
                        logger.info(f"Auto-resolved Page ID from token debug: {pid} ({page_data.get('name')})")
                        return pid, page_token
    except Exception as e:
        logger.error(f"Error checking debug_token fallback: {e}")

    logger.warning(f"Could not resolve Page ID for Instagram Account: {instagram_account_id}.")
    return None, token

def send_private_reply(comment_id: str, message: str, page_id: str, token: str) -> bool:
    """Send a single private reply (DM) to a comment using Messenger Platform API."""
    url = f"https://graph.facebook.com/v19.0/{page_id}/messages"
    payload = {
        "recipient": {"comment_id": comment_id},
        "message": {"text": message},
        "access_token": token
    }
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            logger.info(f"Successfully sent private reply DM for comment {comment_id}")
            return True
        else:
            logger.error(f"Failed to send private reply for comment {comment_id}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending private reply for comment {comment_id}: {e}")
        return False

def send_dm(recipient_id: str, message: str, page_id: str, token: str) -> bool:
    """Send a DM directly to a user's IGSID."""
    url = f"https://graph.facebook.com/v19.0/{page_id}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "access_token": token
    }
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            logger.info(f"Successfully sent DM to user {recipient_id}")
            return True
        else:
            logger.error(f"Failed to send DM to user {recipient_id}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending DM to user {recipient_id}: {e}")
        return False

def post_public_reply(comment_id: str, message: str, token: str) -> bool:
    """Post a public reply to an Instagram comment."""
    url = f"https://graph.facebook.com/v19.0/{comment_id}/replies"
    payload = {
        "message": message,
        "access_token": token
    }
    try:
        resp = requests.post(url, data=payload)
        if resp.status_code == 200:
            logger.info(f"Successfully posted public reply to comment {comment_id}")
            return True
        else:
            logger.error(f"Failed to post public reply to comment {comment_id}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Error posting public reply to comment {comment_id}: {e}")
        return False

def check_user_follows(user_id: str, token: str) -> bool:
    """Check if the user (IGSID) follows our Business Account."""
    url = f"https://graph.facebook.com/v19.0/{user_id}"
    params = {
        "fields": "is_user_follow_business",
        "access_token": token
    }
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            follows = data.get("is_user_follow_business", False)
            logger.info(f"Follow status checked for user {user_id}: {follows}")
            return follows
        else:
            logger.warning(f"Failed to check follow status for user {user_id}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Error checking follow status for user {user_id}: {e}")
        return False

def get_instagram_username(user_id: str, token: str) -> Optional[str]:
    """Retrieve the Instagram username for a specific IGSID."""
    url = f"https://graph.facebook.com/v19.0/{user_id}"
    params = {
        "fields": "username",
        "access_token": token
    }
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("username")
    except Exception as e:
        logger.error(f"Error fetching username for IGSID {user_id}: {e}")
    return None

# ─── Core Processing Engine ───────────────────────────────────

def process_comment_event(
    comment_id: str,
    media_id: str,
    comment_text: str,
    username: str,
    user_id: str,
    page_id: str,
    page_token: str,
    token: str
):
    """
    Process a single comment.
    Find matching rules, reply publicly, send DM, and handle follow verification logic.
    """
    db = get_db()
    
    # Check if comment already processed
    existing = db.processed_comments.find_one({"comment_id": comment_id})
    if existing:
        return
    
    logger.info(f"Processing comment {comment_id} by @{username} on media {media_id}: '{comment_text}'")
    
    # Find matching rules
    # We look for rules targeting this specific media_id or 'all'
    cursor = db.auto_dm_rules.find({"is_active": True, "post_id": {"$in": [media_id, "all"]}})
    rules = list(cursor)
    
    matched_rule = None
    cleaned_comment = comment_text.strip().lower()
    
    for rule in rules:
        keyword = rule.get("keyword", "").strip().lower()
        # Wildcard match or keyword match
        if keyword == "*" or keyword == "any" or keyword in cleaned_comment:
            matched_rule = rule
            break
            
    if not matched_rule:
        # Save log of comment but mark as no rule matched
        db.processed_comments.insert_one({
            "comment_id": comment_id,
            "media_id": media_id,
            "username": username,
            "user_id": user_id,
            "comment_text": comment_text,
            "timestamp": datetime.now().isoformat(),
            "status": "ignored",
            "log": "No active rule matched comment keyword."
        })
        return

    rule_id = str(matched_rule["_id"])
    logger.info(f"Matched comment {comment_id} to rule {rule_id} (Keyword: {matched_rule.get('keyword')})")
    
    # Insert entry with 'processing' status
    db.processed_comments.insert_one({
        "comment_id": comment_id,
        "media_id": media_id,
        "username": username,
        "user_id": user_id,
        "comment_text": comment_text,
        "timestamp": datetime.now().isoformat(),
        "status": "processing",
        "rule_id": rule_id
    })
    
    # 1. Post Public Comment Reply if configured
    public_msg = matched_rule.get("public_reply", "").strip()
    if public_msg:
        post_public_reply(comment_id, public_msg, page_token)
        
    # 2. Check follow status / DM
    require_follow = matched_rule.get("require_follow", False)
    private_msg = matched_rule.get("private_reply", "").strip()
    
    if not require_follow:
        # Send direct DM
        success = send_private_reply(comment_id, private_msg, page_id, page_token)
        status = "processed" if success else "failed"
        db.processed_comments.update_one(
            {"comment_id": comment_id},
            {"$set": {"status": status, "log": "Direct DM reply sent." if success else "Failed to send private reply."}}
        )
    else:
        # Check follow status immediately. Note: meta api might throw error if user has never interacted.
        # But if they already follow and have sent DMs before, this works!
        follows = False
        api_consent_valid = False
        try:
            url = f"https://graph.facebook.com/v19.0/{user_id}"
            params = {"fields": "is_user_follow_business", "access_token": page_token}
            r = requests.get(url, params=params)
            if r.status_code == 200:
                follows = r.json().get("is_user_follow_business", False)
                api_consent_valid = True
        except Exception:
            pass
            
        if api_consent_valid and follows:
            # User already follows us and consent exists! Send DM immediately.
            success = send_private_reply(comment_id, private_msg, page_id, page_token)
            status = "processed" if success else "failed"
            db.processed_comments.update_one(
                {"comment_id": comment_id},
                {"$set": {"status": status, "log": "Immediate DM sent (Follower verification succeeded)."}}
            )
        else:
            # Fallback to the 2-step verification. Send DM asking for follow + keyword reply.
            trigger_word = matched_rule.get("keyword", "INFO").upper()
            if trigger_word == "*":
                trigger_word = "GO"
            prompt_msg = (
                f"Hey! Thanks for commenting. 🌟\n\n"
                f"To receive your download link, please make sure you are following @goran.dotin and reply to this message with '{trigger_word}'."
            )
            success = send_private_reply(comment_id, prompt_msg, page_id, page_token)
            if success:
                db.processed_comments.update_one(
                    {"comment_id": comment_id},
                    {"$set": {"status": "pending_follow", "log": "Follow-gate prompt sent. Waiting for message reply."}}
                )
            else:
                db.processed_comments.update_one(
                    {"comment_id": comment_id},
                    {"$set": {"status": "failed", "log": "Failed to send follow-gate prompt."}}
                )

def process_message_event(
    sender_id: str,
    message_text: str,
    page_id: str,
    page_token: str,
    token: str
):
    """
    Process incoming direct messages.
    Checks if this user has a pending comment waiting for follow verification.
    """
    db = get_db()
    
    # Query user's username
    username = get_instagram_username(sender_id, page_token)
    if not username:
        logger.warning(f"Could not resolve username for sender {sender_id}. Cannot match message.")
        return
        
    cleaned_message = message_text.strip().lower()
    
    # Find latest pending_follow comment for this username
    pending_comment = db.processed_comments.find_one(
        {"username": username, "status": "pending_follow"},
        sort=[("timestamp", -1)]
    )
    
    if not pending_comment:
        # No pending comment, ignore message
        return
        
    rule_id = pending_comment.get("rule_id")
    rule = db.auto_dm_rules.find_one({"_id": ObjectId(rule_id)})
    if not rule:
        db.processed_comments.update_one(
            {"comment_id": pending_comment["comment_id"]},
            {"$set": {"status": "failed", "log": "Matched rule not found in database."}}
        )
        return
        
    keyword = rule.get("keyword", "").strip().lower()
    expected_trigger = keyword if keyword != "*" else "go"
    
    # Verify if they replied with keyword or anything to trigger the check
    if expected_trigger in cleaned_message or len(cleaned_message) > 0:
        # Check follow status
        is_following = check_user_follows(sender_id, page_token)
        if is_following:
            # Deliver the resource!
            private_msg = rule.get("private_reply", "").strip()
            success = send_dm(sender_id, private_msg, page_id, page_token)
            if success:
                db.processed_comments.update_one(
                    {"comment_id": pending_comment["comment_id"]},
                    {"$set": {"status": "processed", "log": "Follow status verified. Resource delivered via DM."}}
                )
            else:
                db.processed_comments.update_one(
                    {"comment_id": pending_comment["comment_id"]},
                    {"$set": {"status": "failed", "log": "Follow verified, but failed to send resource DM."}}
                )
        else:
            # Remind them to follow
            trigger_word = rule.get("keyword", "INFO").upper()
            if trigger_word == "*":
                trigger_word = "GO"
            remind_msg = (
                f"Oops! It looks like you're not following us yet. 😕\n\n"
                f"Please follow @goran.dotin and reply with '{trigger_word}' again to unlock the link!"
            )
            send_dm(sender_id, remind_msg, page_id, page_token)
            db.processed_comments.update_one(
                {"comment_id": pending_comment["comment_id"]},
                {"$set": {"log": "Follow check failed. Sent follow reminder."}}
            )

# ─── Background Polling Task ──────────────────────────────────

async def comment_polling_worker():
    """
    Background polling worker. Checks Instagram comments and inbox messages every 2 minutes
    when webhook endpoints are not receiving live traffic.
    """
    await asyncio.sleep(5) # Let startup complete
    logger.info("Instagram comment & message poller background worker started.")
    
    while True:
        try:
            config = load_env()
            instagram_account_id = config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
            token = config.get("INSTAGRAM_ACCESS_TOKEN")
            
            if not instagram_account_id or not token:
                await asyncio.sleep(60)
                continue
                
            page_id, page_token = get_page_info(instagram_account_id, token)
            if not page_id:
                logger.warning("Polling skipped: Connected Facebook Page ID could not be resolved.")
                await asyncio.sleep(60)
                continue
                
            db = get_db()
            
            # 1. Fetch recent media (latest 15 posts)
            media_url = f"https://graph.facebook.com/v19.0/{instagram_account_id}/media"
            media_params = {
                "fields": "id,caption,media_type,timestamp",
                "limit": 15,
                "access_token": token
            }
            media_resp = requests.get(media_url, params=media_params)
            
            if media_resp.status_code == 200:
                posts = media_resp.json().get("data", [])
                
                # Fetch rules to check what posts we care about
                active_rules_posts = db.auto_dm_rules.distinct("post_id", {"is_active": True})
                
                for post in posts:
                    post_id = post["id"]
                    # If there's an active rule for this post, or a general rule for 'all'
                    if post_id in active_rules_posts or "all" in active_rules_posts:
                        # Fetch comments
                        comments_url = f"https://graph.facebook.com/v19.0/{post_id}/comments"
                        comments_params = {
                            "fields": "id,text,username,timestamp,from",
                            "limit": 50,
                            "access_token": token
                        }
                        comments_resp = requests.get(comments_url, params=comments_params)
                        if comments_resp.status_code == 200:
                            comments = comments_resp.json().get("data", [])
                            for comment in comments:
                                c_id = comment["id"]
                                c_text = comment.get("text", "")
                                c_username = comment.get("username", "")
                                from_user = comment.get("from")
                                c_user_id = from_user.get("id") if from_user else None
                                
                                if c_id and c_text and c_username and c_user_id:
                                    # Run the processing engine
                                    process_comment_event(
                                        comment_id=c_id,
                                        media_id=post_id,
                                        comment_text=c_text,
                                        username=c_username,
                                        user_id=c_user_id,
                                        page_id=page_id,
                                        page_token=page_token,
                                        token=token
                                    )
            
            # 2. Fetch conversations to poll recent messages
            conv_url = f"https://graph.facebook.com/v19.0/{page_id}/conversations"
            conv_params = {
                "fields": "id,updated_time,participants,messages.limit(2){id,message,from,created_time}",
                "access_token": page_token
            }
            conv_resp = requests.get(conv_url, params=conv_params)
            if conv_resp.status_code == 200:
                conversations = conv_resp.json().get("data", [])
                for conv in conversations:
                    messages = conv.get("messages", {}).get("data", [])
                    for msg in messages:
                        from_info = msg.get("from", {})
                        sender_id = from_info.get("id")
                        msg_text = msg.get("message", "")
                        
                        # Only process messages NOT from our own page
                        if sender_id and sender_id != page_id and msg_text:
                            # Let's inspect the message timestamp. If created in the last 15 minutes, process it
                            try:
                                msg_time = datetime.strptime(msg.get("created_time").split("+")[0], "%Y-%m-%dT%H:%M:%S")
                                delta = datetime.utcnow() - msg_time
                                if delta.total_seconds() < 900: # 15 minutes
                                    process_message_event(
                                        sender_id=sender_id,
                                        message_text=msg_text,
                                        page_id=page_id,
                                        page_token=page_token,
                                        token=token
                                    )
                            except Exception as parse_err:
                                logger.error(f"Error parsing message time: {parse_err}")
                                
        except Exception as outer_err:
            logger.error(f"Error in background comment polling: {outer_err}")
            
        await asyncio.sleep(10) # Poll every 10 seconds for fast local response

# ─── FastAPI Routes ───────────────────────────────────────────

class RuleSaveRequest(BaseModel):
    id: Optional[str] = None
    name: str
    post_id: str
    post_caption: Optional[str] = ""
    keyword: str
    public_reply: str
    private_reply: str
    require_follow: bool
    is_active: Optional[bool] = True

@router.get("/api/instagram/posts")
def get_instagram_posts():
    """Fetch recent Instagram posts to populate the visual post selector."""
    config = load_env()
    instagram_account_id = config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    token = config.get("INSTAGRAM_ACCESS_TOKEN")
    
    if not instagram_account_id or not token:
        raise HTTPException(status_code=400, detail="Instagram Business Account ID or Access Token is missing in environment.")
        
    url = f"https://graph.facebook.com/v19.0/{instagram_account_id}/media"
    params = {
        "fields": "id,caption,media_url,permalink,timestamp,media_type",
        "limit": 30,
        "access_token": token
    }
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        else:
            raise HTTPException(status_code=resp.status_code, detail=f"Meta API Error: {resp.text}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/automation/rules")
def get_rules():
    """List all auto-DM response rules."""
    try:
        db = get_db()
        cursor = db.auto_dm_rules.find().sort("created_at", -1)
        return [serialize_mongo(doc) for doc in cursor]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/automation/rule/save")
def save_rule(req: RuleSaveRequest):
    """Save or update an auto-DM response rule."""
    try:
        db = get_db()
        rule_data = {
            "name": req.name,
            "post_id": req.post_id,
            "post_caption": req.post_caption,
            "keyword": req.keyword,
            "public_reply": req.public_reply,
            "private_reply": req.private_reply,
            "require_follow": req.require_follow,
            "is_active": req.is_active,
            "updated_at": datetime.now().isoformat()
        }
        
        if req.id:
            # Update
            db.auto_dm_rules.update_one(
                {"_id": ObjectId(req.id)},
                {"$set": rule_data}
            )
            message = "Rule updated successfully."
        else:
            # Create
            rule_data["created_at"] = datetime.now().isoformat()
            db.auto_dm_rules.insert_one(rule_data)
            message = "Rule created successfully."
            
        return {"status": "success", "message": message}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/automation/rule/{rule_id}")
def delete_rule(rule_id: str):
    """Delete an auto-DM response rule."""
    try:
        db = get_db()
        db.auto_dm_rules.delete_one({"_id": ObjectId(rule_id)})
        return {"status": "success", "message": "Rule deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/automation/rule/toggle/{rule_id}")
def toggle_rule(rule_id: str):
    """Toggle a rule's active state."""
    try:
        db = get_db()
        rule = db.auto_dm_rules.find_one({"_id": ObjectId(rule_id)})
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found.")
        new_state = not rule.get("is_active", True)
        db.auto_dm_rules.update_one(
            {"_id": ObjectId(rule_id)},
            {"$set": {"is_active": new_state}}
        )
        return {"status": "success", "is_active": new_state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/automation/logs")
def get_logs():
    """Fetch recent processed comment logs."""
    try:
        db = get_db()
        cursor = db.processed_comments.find().sort("timestamp", -1).limit(100)
        return [serialize_mongo(doc) for doc in cursor]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ─── Meta Webhook Integration ────────────────────────────────

@router.get("/api/webhook/instagram")
def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token")
):
    """Meta Webhook validation callback."""
    config = load_env()
    expected_token = config.get("INSTAGRAM_WEBHOOK_VERIFY_TOKEN", "goran_verify_token")
    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Webhook verification challenge passed.")
        from fastapi.responses import Response
        # Verification requires raw challenge response
        return Response(content=hub_challenge, media_type="text/plain")
    logger.warning("Webhook verification challenge failed.")
    raise HTTPException(status_code=403, detail="Verification token mismatch.")

@router.post("/api/webhook/instagram")
async def receive_webhook(payload: dict, background_tasks: BackgroundTasks):
    """Meta Webhook receiver. Runs event processing in background thread."""
    config = load_env()
    instagram_account_id = config.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    token = config.get("INSTAGRAM_ACCESS_TOKEN")
    
    if not instagram_account_id or not token:
        return {"status": "error", "message": "Instagram access keys not configured."}
        
    page_id, page_token = get_page_info(instagram_account_id, token)
    if not page_id:
        return {"status": "error", "message": "Facebook Page connection not resolved."}
        
    # Standard Meta event payload parsing
    if payload.get("object") != "instagram":
        return {"status": "ignored"}
        
    entries = payload.get("entry", [])
    for entry in entries:
        # 1. Process comment changes
        changes = entry.get("changes", [])
        for change in changes:
            if change.get("field") == "comments":
                val = change.get("value", {})
                comment_id = val.get("id")
                media_id = val.get("media", {}).get("id")
                comment_text = val.get("text", "")
                from_user = val.get("from", {})
                username = from_user.get("username", "")
                user_id = from_user.get("id")
                
                if comment_id and media_id and comment_text and username and user_id:
                    # Execute in background task
                    background_tasks.add_task(
                        process_comment_event,
                        comment_id=comment_id,
                        media_id=media_id,
                        comment_text=comment_text,
                        username=username,
                        user_id=user_id,
                        page_id=page_id,
                        page_token=page_token,
                        token=token
                    )
                    
        # 2. Process message notifications
        messaging = entry.get("messaging", [])
        for msg_event in messaging:
            sender_id = msg_event.get("sender", {}).get("id")
            recipient_id = msg_event.get("recipient", {}).get("id")
            message = msg_event.get("message", {})
            msg_text = message.get("text", "")
            
            # Avoid infinite loops (ignore messages sent by the Page itself)
            if sender_id and sender_id != page_id and msg_text:
                background_tasks.add_task(
                    process_message_event,
                    sender_id=sender_id,
                    message_text=msg_text,
                    page_id=page_id,
                    page_token=page_token,
                    token=token
                )
                
    return {"status": "processing"}
