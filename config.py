"""
Centralized configuration loader for the GoRan AI Instagram Automation System.

All scripts and modules should import from here instead of
defining their own load_env() / load_config() functions.

Keys are stored in UPPERCASE to match standard environment variable conventions.
"""

import os

# Project root directory (where this file lives)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")


def load_env(env_path=None):
    """Load environment variables from the .env file and standard OS environment.

    Returns a dict with UPPERCASE keys matching standard env var naming:
        GOOGLE_SHEET_ID, CLOUDINARY_API_KEY, INSTAGRAM_ACCESS_TOKEN, etc.

    Args:
        env_path: Optional override for the .env file path.
                  Defaults to the .env file in the project root.
    """
    path = env_path or ENV_FILE
    config = {}
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    config[k.strip()] = v.strip()
                    
    # Fallback to standard OS environment variables (essential for Render/production)
    import os
    for key, value in os.environ.items():
        if value:
            config[key] = value
            
    # Dynamically generate Google service account file if GOOGLE_CREDS_JSON is provided
    import json
    creds_json = config.get("GOOGLE_CREDS_JSON")
    creds_file = config.get("GOOGLE_CREDS_FILE", "google_service_account.json")
    if creds_json and creds_file:
        if not os.path.isabs(creds_file):
            creds_file_path = os.path.join(PROJECT_ROOT, creds_file)
        else:
            creds_file_path = creds_file
            
        if not os.path.exists(creds_file_path):
            try:
                json_data = json.loads(creds_json)
                with open(creds_file_path, "w", encoding="utf-8") as out_f:
                    json.dump(json_data, out_f, indent=2)
            except Exception as write_err:
                print(f"Failed to generate credentials file from GOOGLE_CREDS_JSON: {write_err}")
                
    return config


def get_project_path(*parts):
    """Get an absolute path relative to the project root.

    Example:
        get_project_path("post", "post_temp")
        → "d:/InstagramPost/post/post_temp"
    """
    return os.path.join(PROJECT_ROOT, *parts)
