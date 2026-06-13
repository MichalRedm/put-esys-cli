from functools import wraps

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
