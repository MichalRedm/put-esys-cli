import sys
from functools import wraps
from typing import Optional

import typer
from rich.console import Console

from put_esys.services.auth import SessionExpiredError
from put_esys.services.config import load_credentials

console = Console(stderr=True)


def is_numeric_or_url(id_or_url: str) -> bool:
    """Checks if the given string is a numeric ID or a URL."""
    if id_or_url.isdigit():
        return True
    if id_or_url.startswith("http://") or id_or_url.startswith("https://"):
        return True
    return False


def catch_errors(f):
    """
    Decorator for Typer commands to catch SessionExpiredError and other
    exceptions, printing them cleanly to stderr and exiting with code 1.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except typer.Exit:
            raise
        except SessionExpiredError as e:

            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(code=1)


    return wrapper


def check_authenticated(client) -> None:
    """
    Checks if the client session is authenticated. If not, checks if credentials exist.
    If credentials exist, it indicates the session expired / couldn't be refreshed.
    If no credentials exist, it indicates a first-time configuration is needed.
    """
    if not client.is_authenticated:
        if load_credentials():
            raise SessionExpiredError(
                "eKursy session expired. Please run 'put-esys login' to refresh your session."
            )
        else:
            console.print("[red]Not authenticated.[/red]")
            console.print(
                "Please run [bold]put-esys config set[/bold] first to save your credentials."
            )
            raise typer.Exit(code=1)


def handle_output(
    data,
    output_path: Optional[str] = None,
    json_format: bool = False,
    display_fn=None,
    *args,
    **kwargs
) -> None:
    """
    Handles displaying data (JSON or Rich text/table) and writing to file if specified.
    Uses UTF-8 encoding for file output and strips ANSI color codes.
    """
    import json

    if json_format:
        if hasattr(data, "model_dump_json"):
            content = data.model_dump_json(indent=2)
        elif isinstance(data, list):
            serialized = [
                item.model_dump() if hasattr(item, "model_dump") else item for item in data
            ]
            content = json.dumps(serialized, indent=2)
        elif hasattr(data, "model_dump"):
            content = json.dumps(data.model_dump(), indent=2)
        else:
            content = json.dumps(data, indent=2)

        if output_path:
            import os
            parent = os.path.dirname(output_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
        else:
            sys.stdout.write(content + "\n")
    else:
        if output_path:
            import os

            from rich.console import Console
            parent = os.path.dirname(output_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            # Disable colors/styles for plain-text file output
            capture_console = Console(color_system=None, width=120)
            with capture_console.capture() as capture:
                if display_fn:
                    display_fn(data, *args, **kwargs)
            content = capture.get()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            if display_fn:
                display_fn(data, *args, **kwargs)
