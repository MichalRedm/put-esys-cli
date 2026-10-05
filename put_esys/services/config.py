import json
import os
from pathlib import Path
from typing import Dict, Optional

import appdirs

# Preferred OS user config dir
_APPDIRS_DIR = Path(appdirs.user_config_dir("put-esys"))
# Legacy home directory fallback
_LEGACY_DIR = Path.home() / ".put-esys"


def get_app_dir() -> Path:
    """
    Returns application configuration directory.
    Prefers OS-compliant appdirs directory; if legacy ~/.put-esys exists with data,
    uses that for backwards compatibility.
    """
    if _LEGACY_DIR.exists() and any(_LEGACY_DIR.iterdir()):
        return _LEGACY_DIR
    return _APPDIRS_DIR


APP_DIR = get_app_dir()
SESSION_FILE = APP_DIR / "session.json"
CONFIG_FILE = APP_DIR / "config.json"


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def _write_secure_json(path: Path, data: dict) -> None:
    ensure_app_dir()
    # Write to a temporary file or set restrictive permissions
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    # Set POSIX restrictive permissions (0600)
    try:
        os.chmod(path, 0o600)
    except (OSError, AttributeError):
        pass


def save_session(cookies_dict: dict) -> None:
    _write_secure_json(SESSION_FILE, cookies_dict)


def load_session() -> Optional[dict]:
    if not SESSION_FILE.exists():
        return None
    try:
        with open(SESSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_credentials(username: str, password: str) -> None:
    _write_secure_json(CONFIG_FILE, {"username": username, "password": password})


def load_credentials() -> Optional[Dict[str, str]]:
    if not CONFIG_FILE.exists():
        return None
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def clear_credentials() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()


def delete_session() -> None:
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
