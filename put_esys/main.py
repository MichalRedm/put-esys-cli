"""
Main entry point for the PUT Electronic Systems CLI application.
"""

import sys

# Force UTF-8 encoding on Windows to prevent UnicodeEncodeError
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .cli import app

if __name__ == "__main__":
    app()
