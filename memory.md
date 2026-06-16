# Project Memory: Google Sheets to Instagram Carousel Pipeline

This file serves as a persistent session memory record to resume development, testing, or publishing at any time.

---

## 📌 Project Overview
The project automates the workflow of generating and publishing Instagram Carousel posts for **GoRan AI Agency** (`@goran.dotin` / [goran.in](https://goran.in)) using a hybrid automated/manual pipeline:
1. **Fetch:** A script pulls structured slide copy and captions from an approved row in a Google Sheet.
2. **Generate:** The agent manually generates visual slides (with text embedded) using style reference files during chat sessions.
3. **Publish:** A script uploads the local slide images to Cloudinary (for public URLs) and invokes the Meta/Instagram Graph API to create and publish a live Instagram carousel.

---

## 📂 Active Codebase Structure
* [fetch_sheet_data.py](file:///d:/InstagramPost/fetch_sheet_data.py): Reads approved posts from Google Sheets, locks the row status to `Generating`, prints prompt templates for the agent, and caches local metadata.
* [publish_to_instagram.py](file:///d:/InstagramPost/publish_to_instagram.py): Scans the `post/post_temp` folder, uploads slides to Cloudinary, registers containers on Instagram, publishes the post, and updates the Google Sheet row status to `Posted` (Graph API Method).
* [publish_via_browser.py](file:///d:/InstagramPost/publish_via_browser.py): Uses Playwright browser automation to log in to Instagram Web, upload the slides directly from disk, write the caption, and publish (Browser Automation Method).
* [.env](file:///d:/InstagramPost/.env): Structured key-value credential storage file.
* [reference_style/](file:///d:/InstagramPost/reference_style): Folder for visual reference images to maintain slide styling consistency.
* [post/](file:///d:/InstagramPost/post): Houses current and historical post records:
  * [post_03_silent_profit_killers](file:///d:/InstagramPost/post/post_03_silent_profit_killers): Slide PNG assets, captions, and blueprints.
  * [post_04_ecommerce_automation](file:///d:/InstagramPost/post/post_04_ecommerce_automation): Actionable solution slides, captions, and blueprints.
  * [post_05_d2c_automation_day1](file:///d:/InstagramPost/post/post_05_d2c_automation_day1): **[TESTING POST]** Slide copy blueprints and captions representing Day 1 of the 50 Days AI Automation campaign.

---

## 🔧 Resolved Issues & Configurations
* **Python Environment & Imports:** All pipeline dependencies (`gspread`, `google-auth`, `requests`, `cloudinary`) have been successfully installed using `uv pip` into your active virtual environment (`C:\Users\ranja\AppData\Local\hermes\hermes-agent\venv\`). IDE static analysis import diagnostics are 100% clean.
* **Execution Commands:** The pipeline can be executed using your default `python` command:
  ```bash
  python fetch_sheet_data.py --dry-run
  python publish_to_instagram.py --dry-run
  ```

---

## 🚀 How to Resume and Execute the Session

When you return to this workspace:

### Step 1: Set Up Credentials
Fill out the variables in [.env](file:///d:/InstagramPost/.env) and place your service account key at `d:\InstagramPost\google_service_account.json` (see instructions in [walkthrough.md](file:///C:/Users/ranja/.gemini/antigravity-ide/brain/62b97619-390a-4e4e-865f-e67fcc3e7783/walkthrough.md) for details on Google, Cloudinary, and Instagram API tokens).

### Step 2: Validate Connection
Run dry-run checks to verify connections and credentials:
```bash
python fetch_sheet_data.py --dry-run
python publish_to_instagram.py --dry-run
```

### Step 3: Run the Publishing Loop
1. Add post records to your Google Sheet queue. Set a row's `Status` column to **`Approved`**.
2. Run the fetch script:
   ```bash
   python fetch_sheet_data.py
   ```
3. Copy the printed prompts and instruct the AI Agent (Antigravity) to generate slide images via chat using the style guidelines from the `reference_style/` folder.
4. Save the 6 generated PNG images to `d:\InstagramPost\post\post_temp\` as `slide_01.png` to `slide_06.png`.
5. Run the publishing script. You have two options:
   * **Option A (Browser Automation - Recommended):** Direct upload from disk (no developer tokens or image hosting needed). Run:
     ```bash
     python publish_via_browser.py
     ```
     *(Note: On the first run, a browser window will open for a one-time manual login. The session is saved to `instagram_session.json` and reused automatically in subsequent runs).*
   * **Option B (Graph API):** Programmatic upload using Cloudinary hosting. Run:
     ```bash
     python publish_to_instagram.py
     ```
     This will upload the slides to Cloudinary, register containers, publish the carousel, and update the Google Sheet status to `Posted`.
