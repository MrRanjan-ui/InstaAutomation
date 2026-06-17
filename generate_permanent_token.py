import os
import sys
import requests

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

def load_env():
    config = {}
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
    return config

def update_env(key, value):
    lines = []
    updated = False
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    lines.append(f"{key}={value}\n")
                    updated = True
                else:
                    lines.append(line)
    if not updated:
        lines.append(f"{key}={value}\n")
        
    with open(".env", "w") as f:
        f.writelines(lines)
    print(f"Updated {key} in .env file successfully!")

def main():
    print("====================================================")
    print("   GoRan AI - Permanent Instagram Token Generator   ")
    print("====================================================\n")
    
    user_token = input("Paste your new short-lived User Access Token from Graph API Explorer: ").strip()
    if not user_token:
        print("Error: Access token is required.")
        return
    short_token = user_token
    
    app_id = input("Enter your Meta App ID: ").strip()
    app_secret = input("Enter your Meta App Secret: ").strip()
    
    if not app_id or not app_secret:
        print("Error: Both App ID and App Secret are required.")
        return

    # 1. Exchange short-lived token for long-lived user token (60 days)
    print("\nStep 1: Requesting 60-day Long-Lived User Token...")
    url_exchange = "https://graph.facebook.com/v19.0/oauth/access_token"
    params_exchange = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token
    }
    
    resp = requests.get(url_exchange, params=params_exchange)
    if resp.status_code != 200:
        print(f"Failed to generate long-lived token: {resp.text}")
        return
        
    long_lived_token = resp.json().get("access_token")
    print("✅ Successfully generated 60-day Long-Lived User Access Token!")
    
    # 2. Get connected Facebook Pages and Page tokens (Never Expiring)
    print("\nStep 2: Fetching connected Facebook Pages...")
    url_pages = "https://graph.facebook.com/v19.0/me/accounts"
    params_pages = {
        "access_token": long_lived_token
    }
    
    resp_pages = requests.get(url_pages, params=params_pages)
    if resp_pages.status_code != 200:
        print(f"Failed to fetch connected pages: {resp_pages.text}")
        return
        
    pages = resp_pages.json().get("data", [])
    if not pages:
        print("No Facebook Pages found connected to this account. Make sure your Instagram Business Account is linked to a Facebook Page.")
        return
        
    print("\nAvailable Pages:")
    for idx, page in enumerate(pages, start=1):
        print(f"[{idx}] {page.get('name')} (ID: {page.get('id')})")
        
    choice = input("\nSelect the page number connected to your Instagram account: ").strip()
    try:
        page_idx = int(choice) - 1
        if page_idx < 0 or page_idx >= len(pages):
            print("Invalid choice.")
            return
        selected_page = pages[page_idx]
    except ValueError:
        print("Invalid input.")
        return
        
    permanent_token = selected_page.get("access_token")
    page_name = selected_page.get("name")
    
    print(f"\n✅ Successfully retrieved never-expiring token for page '{page_name}'!")
    print(f"Token: {permanent_token[:30]}...[truncated]")
    
    # 3. Save to .env
    update_env("INSTAGRAM_ACCESS_TOKEN", permanent_token)
    
    print("\n🎉 Setup Complete! Your scheduler background worker has loaded the new token.")
    print("You can try publishing your post now.")

if __name__ == "__main__":
    main()
