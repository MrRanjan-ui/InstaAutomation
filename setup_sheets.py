import os
import fetch_sheet_data

def main():
    config = fetch_sheet_data.load_config()
    client = fetch_sheet_data.get_sheets_client(config['google_creds_file'])
    spreadsheet = client.open_by_key(config['google_sheet_id'])
    
    headers = [
        "Post_ID", "Topic", "Caption", "Status",
        "Slide_1_URL", "Slide_2_URL", "Slide_3_URL", "Slide_4_URL", "Slide_5_URL", "Slide_6_URL"
    ]
    
    # 1. Create/Set up "Queue" sheet
    try:
        sheet_queue = spreadsheet.worksheet("Queue")
        print("Sheet 'Queue' already exists.")
    except Exception:
        sheet_queue = spreadsheet.add_worksheet(title="Queue", rows=100, cols=20)
        print("Created worksheet 'Queue'.")
        
    # Write headers if empty
    if not sheet_queue.row_values(1):
        sheet_queue.append_row(headers)
        # Append sample row
        sheet_queue.append_row([
            "post_01_random_audit",
            "Why manual workflows leak profits",
            "Are manual data entries costing you $10k+/mo? 🤖💼\n\nOperational friction is real. Here is why custom AI integrations are the solution.\n\n#AI #Operations",
            "Approved",
            "https://res.cloudinary.com/dikisauij/image/upload/v1781586747/w6iu9nnyud5rnf0aj41r.jpg"
        ])
        print("Added headers and sample row to 'Queue'.")

    # 2. Create/Set up "50DaysCampaign" sheet
    try:
        sheet_camp = spreadsheet.worksheet("50DaysCampaign")
        print("Sheet '50DaysCampaign' already exists.")
    except Exception:
        sheet_camp = spreadsheet.add_worksheet(title="50DaysCampaign", rows=100, cols=20)
        print("Created worksheet '50DaysCampaign'.")
        
    if not sheet_camp.row_values(1):
        sheet_camp.append_row(headers)
        # Append sample row
        sheet_camp.append_row([
            "day_01_ai_intro",
            "Day 1: AI Automation introduction",
            "Day 1 of 50 Days AI Automation for D2C Brand 🚀\n\nLet's automate lead routing. Custom Puppeteer scaper + CRM router qualifications in 180 seconds.\n\n#D2C #AI #Automation",
            "Approved",
            "https://res.cloudinary.com/dikisauij/image/upload/v1781586747/w6iu9nnyud5rnf0aj41r.jpg"
        ])
        print("Added headers and sample row to '50DaysCampaign'.")
        
    # Remove default Sheet1 if it's blank and we have our worksheets
    try:
        sheet1 = spreadsheet.worksheet("Sheet1")
        if not sheet1.row_values(1):
            spreadsheet.del_worksheet(sheet1)
            print("Deleted empty default 'Sheet1'.")
    except Exception:
        pass

if __name__ == "__main__":
    main()
