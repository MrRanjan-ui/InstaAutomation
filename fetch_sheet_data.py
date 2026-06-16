import os
import sys
import json
import gspread
from google.oauth2.service_account import Credentials

from config import load_env, get_project_path

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

META_TEMP_FILE = "post_temp_meta.json"

def get_sheets_client(creds_path):
    if not os.path.exists(creds_path):
        print(f"Error: Google credentials file '{creds_path}' not found.")
        print("Please place your Service Account JSON key in the workspace.")
        sys.exit(1)
        
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)

def find_approved_post(sheet):
    records = sheet.get_all_records()
    for idx, row in enumerate(records, start=2): # Row 1 is header, index is 2-indexed for gspread
        status = str(row.get("Status", "")).strip().lower()
        if status == "approved":
            return row, idx
    return None, None

def format_prompt_output(row):
    post_id = row.get("Post_ID", "temp_post")
    topic = row.get("Topic", "AI Automation")
    print("=" * 80)
    print(f"🚀 FOUND APPROVED POST: {post_id} | Topic: {topic}")
    print("=" * 80)
    print("\n--- INSTRUCTIONS FOR AGENT (ANTIGRAVITY) ---")
    print("Please use the 'generate_image' tool to manually generate the 6 slides for this carousel.")
    print("Use visual style reference images from the 'reference_style/' directory to maintain branding.\n")
    
    # Slide 1 (Cover)
    print(f"📸 SLIDE 1 (Cover):")
    print(f"   Category Tag: {row.get('Slide_1_Category', 'OPERATIONS')}")
    print(f"   Header: {row.get('Slide_1_Title', '')}")
    print(f"   Subtitle: {row.get('Slide_1_Subtitle', '')}")
    print(f"   Suggested Prompt: 'A premium dark tech style Instagram carousel cover slide with carbon grid background. Large bold text at center: \"{row.get('Slide_1_Title', '')}\". Subtitle at bottom-left: \"{row.get('Slide_1_Subtitle', '')}\". Category tag at top-left: \"{row.get('Slide_1_Category', '')}\". Accent color: Acid Lime green.'")
    print("-" * 50)
    
    # Slides 2-4 (Body slides)
    for s in [2, 3, 4]:
        cat = row.get(f"Slide_{s}_Category", "")
        title = row.get(f"Slide_{s}_Title", "")
        body = row.get(f"Slide_{s}_Body", "")
        cure_title = row.get(f"Slide_{s}_Cure_Title", "")
        cure_body = row.get(f"Slide_{s}_Cure_Body", "")
        
        print(f"📸 SLIDE {s}:")
        print(f"   Tag: {cat}")
        print(f"   Title: {title}")
        print(f"   Body: {body}")
        print(f"   Highlight Card Title: {cure_title}")
        print(f"   Highlight Card Body: {cure_body}")
        print(f"   Suggested Prompt: 'A premium dark tech style slide with carbon grid background. Category tag at top-left: \"[{cat}]\" in acid green. Large header: \"{title}\". Body text below it: \"{body}\". At the bottom, a rounded glassmorphic card with a light green border containing text: \"{cure_title} {cure_body}\".'")
        print("-" * 50)

    # Slide 5 (Metrics)
    print(f"📸 SLIDE 5 (Metrics):")
    print(f"   Title: {row.get('Slide_5_Title', 'The GoRan AI Standard')}")
    print(f"   Metric 1: {row.get('Slide_5_Metric_1_Num', '')} | {row.get('Slide_5_Metric_1_Label', '')} | {row.get('Slide_5_Metric_1_Desc', '')}")
    print(f"   Metric 2: {row.get('Slide_5_Metric_2_Num', '')} | {row.get('Slide_5_Metric_2_Label', '')} | {row.get('Slide_5_Metric_2_Desc', '')}")
    print(f"   Metric 3: {row.get('Slide_5_Metric_3_Num', '')} | {row.get('Slide_5_Metric_3_Label', '')} | {row.get('Slide_5_Metric_3_Desc', '')}")
    print(f"   Suggested Prompt: 'A premium dark tech style slide with carbon grid background. Header: \"{row.get('Slide_5_Title', 'The GoRan AI Standard')}\". Three metrics displayed in a clean vertical grid with acid green numbers and white labels: 1st: {row.get('Slide_5_Metric_1_Num', '')} {row.get('Slide_5_Metric_1_Label', '')} ({row.get('Slide_5_Metric_1_Desc', '')}), 2nd: {row.get('Slide_5_Metric_2_Num', '')} {row.get('Slide_5_Metric_2_Label', '')} ({row.get('Slide_5_Metric_2_Desc', '')}), 3rd: {row.get('Slide_5_Metric_3_Num', '')} {row.get('Slide_5_Metric_3_Label', '')} ({row.get('Slide_5_Metric_3_Desc', '')}).'")
    print("-" * 50)

    # Slide 6 (CTA)
    print(f"📸 SLIDE 6 (CTA):")
    print(f"   Title: {row.get('Slide_6_Title', 'Ready to scale?')}")
    print(f"   Body: {row.get('Slide_6_Body', '')}")
    print(f"   CTA Trigger Box: {row.get('Slide_6_CTA_Box', '')}")
    print(f"   Suggested Prompt: 'A high-contrast call-to-action slide. Bold header: \"{row.get('Slide_6_Title', '')}\". Subtitle: \"{row.get('Slide_6_Body', '')}\". At bottom, a prominent highlighted box containing the comment trigger: \"{row.get('Slide_6_CTA_Box', '')}\". Accent: Acid Lime green.'")
    print("=" * 80)

def main():
    config = load_env()
    
    dry_run = "--dry-run" in sys.argv
    
    print("Connecting to Google Sheets...")
    client = get_sheets_client(config.get("GOOGLE_CREDS_FILE", "google_service_account.json"))
    
    try:
        spreadsheet = client.open_by_key(config["GOOGLE_SHEET_ID"])
        sheet = spreadsheet.worksheet(config.get("GOOGLE_SHEET_NAME", "Queue"))
    except Exception as e:
        print(f"Error opening spreadsheet: {e}")
        print("Please check your google_sheet_id and google_sheet_name in config.json.")
        sys.exit(1)
        
    if dry_run:
        print("\n✅ CONNECTION SUCCESSFUL!")
        print(f"Spreadsheet Title: {spreadsheet.title}")
        print(f"Worksheets found: {[w.title for w in spreadsheet.worksheets()]}")
        print(f"Target Sheet '{config.get('GOOGLE_SHEET_NAME', 'Queue')}' is accessible.")
        return

    # Normal Execution
    row, row_idx = find_approved_post(sheet)
    if not row:
        print("No approved posts found (Status = 'Approved').")
        return
        
    # Format and display prompts
    format_prompt_output(row)
    
    # Save local metadata for publishing script
    meta_data = {
        "Post_ID": row.get("Post_ID", "temp_post"),
        "Topic": row.get("Topic", "AI Automation"),
        "Caption": row.get("Caption", ""),
        "CTA_Trigger": row.get("Slide_6_CTA_Box", ""),
        "Row_Index": row_idx
    }
    with open(META_TEMP_FILE, "w", encoding="utf-8") as f:
        json.dump(meta_data, f, indent=2, ensure_ascii=False)
    print(f"\nSaved metadata locally to '{META_TEMP_FILE}' for publishing.")
    
    # Update status to Generating
    # Find column index for Status
    headers = sheet.row_values(1)
    if "Status" in headers:
        col_idx = headers.index("Status") + 1
        sheet.update_cell(row_idx, col_idx, "Generating")
        print(f"Updated post status to 'Generating' in Google Sheet (Row {row_idx}, Column {col_idx}).")
    else:
        print("Warning: 'Status' column not found in sheet headers. Status not updated.")

if __name__ == "__main__":
    main()
