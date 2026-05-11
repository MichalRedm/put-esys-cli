from pathlib import Path
import json
import os

APP_DIR = Path.home() / ".put-esys"
SESSION_FILE = APP_DIR / "session.json"

def ensure_app_dir():
    APP_DIR.mkdir(parents=True, exist_ok=True)

def save_session(cookies_dict):
    ensure_app_dir()
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies_dict, f)

def load_session():
    if not SESSION_FILE.exists():
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)

def delete_session():
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
