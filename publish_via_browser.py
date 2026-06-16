import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

SESSION_FILE = "instagram_session.json"
META_TEMP_FILE = "post_temp_meta.json"
SLIDES_DIR = r"d:\InstagramPost\post\post_temp"
SCREENSHOTS_DIR = r"d:\InstagramPost\post\automation_debug"

def load_post_metadata():
    if not os.path.exists(META_TEMP_FILE):
        print(f"Error: Post metadata file '{META_TEMP_FILE}' not found.")
        print("Please run 'fetch_sheet_data.py' first to retrieve an approved post.")
        sys.exit(1)
    with open(META_TEMP_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def run_browser_pipeline():
    meta = load_post_metadata()
    caption_text = meta.get("Caption", "")
    
    if not os.path.exists(SLIDES_DIR):
        print(f"Error: Slide directory '{SLIDES_DIR}' not found.")
        sys.exit(1)
        
    slide_files = sorted([
        os.path.abspath(os.path.join(SLIDES_DIR, f))
        for f in os.listdir(SLIDES_DIR)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ])
    
    if not slide_files:
        print(f"Error: No image files (.png, .jpg, .jpeg) found in {SLIDES_DIR}.")
        sys.exit(1)
        
    print(f"Found {len(slide_files)} slide files to publish.")
    os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

    with sync_playwright() as p:
        # Launch browser with stealth args to avoid bot flags
        # Try channel="chrome" first to use system Chrome, which bypasses reCAPTCHA blank iframe issues
        try:
            print("Launching system Chrome browser...")
            browser = p.chromium.launch(
                headless=False,
                channel="chrome",
                ignore_default_args=["--enable-automation"],
                args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            print(f"Could not launch system Chrome ({e}). Falling back to system Edge...")
            try:
                browser = p.chromium.launch(
                    headless=False,
                    channel="msedge",
                    ignore_default_args=["--enable-automation"],
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
                )
            except Exception as e2:
                print(f"Could not launch system Edge ({e2}). Falling back to standard Playwright Chromium...")
                browser = p.chromium.launch(
                    headless=False,
                    ignore_default_args=["--enable-automation"],
                    args=["--start-maximized", "--disable-blink-features=AutomationControlled"]
                )
        
        # Determine if session exists
        session_exists = os.path.exists(SESSION_FILE)
        
        # Set a real Chrome User-Agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        
        if not session_exists:
            print("\n🔑 SESSION NOT FOUND. Starting login flow...")
            context = browser.new_context(
                user_agent=user_agent,
                no_viewport=True
            )
            page = context.new_page()
            page.goto("https://www.instagram.com/")
            
            print("\n⚠️ ACTION REQUIRED:")
            print("Please log in to your Instagram account in the opened browser window.")
            print("Solve any 2FA/Security checks if prompted.")
            print("Once you are fully logged in and see your home feed, return here and press [ENTER]...")
            
            input("\nPress [ENTER] to save session and continue...")
            
            print("Verifying session cookies...")
            page.wait_for_timeout(2000) # Give cookies time to settle
            
            # Check if session cookie exists
            cookies = context.cookies()
            has_session = any(c['name'] == 'sessionid' for c in cookies)
            if not has_session:
                print("\n❌ ERROR: Login session cookie ('sessionid') not found.")
                print(f"Active cookies found: {[c['name'] for c in cookies]}")
                print("Make sure you log in inside the POPPED-UP Chromium browser window before pressing [ENTER].")
                browser.close()
                sys.exit(1)
                
            # Save storage state (cookies, localstorage)
            context.storage_state(path=SESSION_FILE)
            print(f"✅ Session state successfully saved to '{SESSION_FILE}'!")
            browser.close()
            return
            
        # Session exists - Autopilot Posting Flow
        print("\n🚀 SESSION FOUND. Loading login state from session file...")
        context = browser.new_context(
            storage_state=SESSION_FILE,
            user_agent=user_agent,
            no_viewport=True
        )
        page = context.new_page()
        
        # Navigate to Instagram
        print("Navigating to Instagram...")
        page.goto("https://www.instagram.com/")
        page.wait_for_timeout(6000) # Give more time to resolve redirects
        
        # Save verification screenshot
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_home_screen.png"))
        
        # Check session validity via cookies
        cookies = context.cookies()
        has_session = any(c['name'] == 'sessionid' for c in cookies)
        if not has_session:
            print("❌ Session expired or invalid (sessionid cookie missing). Please delete 'instagram_session.json' and run again to log in.")
            browser.close()
            return
            
        print("✅ Logged in successfully.")
        
        # 1. Click Create (+) button
        print("Opening Create Post window...")
        create_selectors = [
            "svg[aria-label='New post']",
            "svg[aria-label='Create']",
            "text='Create'",
            "span:has-text('Create')",
            "[aria-label='New post']",
            "[aria-label='Create']"
        ]
        
        clicked = False
        for selector in create_selectors:
            try:
                locator = page.locator(selector).first
                if locator.is_visible(timeout=1000):
                    try:
                        locator.locator("xpath=./ancestor::a").first.click(timeout=1000)
                    except:
                        try:
                            locator.locator("xpath=./ancestor::button").first.click(timeout=1000)
                        except:
                            locator.click(timeout=1000)
                    clicked = True
                    break
            except:
                continue
                
        if not clicked:
            print("Failed to find 'Create' button with standard selectors. Attempting fallback click...")
            try:
                page.get_by_role("link", name="New post").click(timeout=2000)
            except:
                try:
                    page.get_by_role("button", name="New post").click(timeout=2000)
                except:
                    page.get_by_text("Create", exact=True).first.click(timeout=2000)
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_create_window.png"))
        
        # 2. Upload multiple files
        print("Uploading slide files...")
        file_input = page.locator("input[type='file']")
        
        # Instagram web upload handles multiple files when set on the file input
        file_input.set_input_files(slide_files)
        page.wait_for_timeout(4000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_files_uploaded.png"))
        
        # 3. Click Next on Crop page
        print("Proceeding past cropping...")
        next_btn = page.locator("div[role='button']:has-text('Next')")
        next_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_filters_page.png"))
        
        # 4. Click Next on Filters page
        print("Proceeding past filters...")
        next_btn.click()
        page.wait_for_timeout(3000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_details_page.png"))
        
        # 5. Type Caption
        print("Entering post caption...")
        caption_box = page.locator("div[aria-label='Write a caption...']")
        caption_box.fill(caption_text)
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_caption_written.png"))
        
        # 6. Click Share
        print("Publishing post (clicking Share)...")
        share_btn = page.locator("div[role='button']:has-text('Share')")
        share_btn.click()
        
        # Wait for success screen
        print("Waiting for upload confirmation (this can take up to 60 seconds)...")
        success_locator = page.get_by_text("Your post has been shared.", exact=False)
        
        try:
            success_locator.wait_for(state="visible", timeout=60000)
            page.wait_for_timeout(3000)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_post_success.png"))
            print("\n🎉 SUCCESS! Your carousel post has been successfully shared live on Instagram!")
            
            # Clean up metadata cache
            if os.path.exists(META_TEMP_FILE):
                os.remove(META_TEMP_FILE)
                
        except Exception as e:
            print("\n❌ Timeout or error waiting for confirmation. Check the screenshots folder to see the state.")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "error_state.png"))
            
        browser.close()

if __name__ == "__main__":
    run_browser_pipeline()
