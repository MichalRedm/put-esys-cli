import json
from pathlib import Path
from typing import Dict, Optional

APP_DIR = Path.home() / ".put-esys"
SESSION_FILE = APP_DIR / "session.json"
CONFIG_FILE = APP_DIR / "config.json"


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def save_session(cookies_dict: dict) -> None:
    ensure_app_dir()
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies_dict, f)


def load_session() -> Optional[dict]:
    if not SESSION_FILE.exists():
        return None
    with open(SESSION_FILE, "r") as f:
        return json.load(f)


def save_credentials(username: str, password: str) -> None:
    ensure_app_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump({"username": username, "password": password}, f)


def load_credentials() -> Optional[Dict[str, str]]:
    if not CONFIG_FILE.exists():
        return None
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def clear_credentials() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def delete_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
