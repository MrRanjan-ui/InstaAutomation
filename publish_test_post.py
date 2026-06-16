import os
import sys
import requests
import time

ENV_FILE = ".env"
IMAGE_URL = "https://res.cloudinary.com/dikisauij/image/upload/v1781580080/pqgxjqz0bluvwgux2mpu.jpg"

CAPTION = (
    "AI Automation Nahi Toh... Business Ka Kya Future? 🤖💼\n\n"
    "In 2026, relying on manual data entry, copy-pasting records, and fragmented lead routing is an operational death sentence. "
    "While you waste hours on repetitive tasks, your competitors are scaling on autopilot.\n\n"
    "Here is why custom AI Automation is the only way forward for B2B & D2C brands:\n"
    "1️⃣ Operational Leverage: AI agents handle 80% of routine workflows (inbound leads, CRM entries, invoicing) so your team can focus on the 20% that drives revenue.\n"
    "2️⃣ Instant Response Times: Customers don't wait. AI automation scores, qualifies, and routes leads in seconds, boosting conversions by 70%+.\n"
    "3️⃣ Human Error = 0: Automated system syncs between ERPs, Shopify, and CRMs mean zero data entry mistakes.\n\n"
    "At GoRan AI Agency, we design and build robust system integrations and autonomous digital agents tailored to your business operations.\n\n"
    "🚀 Stop letting manual processes bottleneck your growth.\n\n"
    "DM us 'AUTOMATE' or click the link in our bio to book a free 30-minute operational workflow audit with our founder, Ashish Ranjan.\n\n"
    "#AI #AIAutomation #BusinessAutomation #CRMAutomation #SoftwareEngineering #InstagramSEO #OperationsManagement #LeadGeneration #BuildInPublic #GoRanAI #AIAgency #AIAgent"
)

def load_config():
    config = {}
    if not os.path.exists(ENV_FILE):
        print(f"Error: Env file '{ENV_FILE}' not found.")
        sys.exit(1)
    with open(ENV_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                config[k.strip().lower()] = v.strip()
    return config

def main():
    config = load_config()
    account_id = config.get("instagram_business_account_id")
    token = config.get("instagram_access_token")
    
    if not account_id or not token:
        print("Error: instagram_business_account_id or instagram_access_token not found in .env")
        sys.exit(1)
        
    print(f"1. Creating Instagram media container for single image...")
    url = f"https://graph.facebook.com/v19.0/{account_id}/media"
    payload = {
        "image_url": IMAGE_URL,
        "caption": CAPTION,
        "access_token": token
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"Error creating media container: {response.status_code} - {response.text}")
        sys.exit(1)
        
    creation_id = response.json().get("id")
    print(f"   Success! Container ID: {creation_id}")
    
    print("Waiting 10 seconds for Instagram container processing...")
    time.sleep(10)
    
    print(f"2. Publishing post to Instagram feed...")
    publish_url = f"https://graph.facebook.com/v19.0/{account_id}/media_publish"
    publish_payload = {
        "creation_id": creation_id,
        "access_token": token
    }
    publish_response = requests.post(publish_url, data=publish_payload)
    if publish_response.status_code != 200:
        print(f"Error publishing post: {publish_response.status_code} - {publish_response.text}")
        sys.exit(1)
        
    post_id = publish_response.json().get("id")
    print(f"\n🎉 SUCCESS! Post published live to Instagram.")
    print(f"   Instagram Post ID: {post_id}")

if __name__ == "__main__":
    main()
