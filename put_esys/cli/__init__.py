import io
import os
import re
import sys
from typing import Optional

import requests
import typer
from rich.console import Console

from put_esys.cli.helpers import catch_errors, check_authenticated
from put_esys.services.auth import authenticate
from put_esys.services.config import load_credentials
from put_esys.services.ekursy import EKursyClient

from .assignment import assignment_app

# Import sub-apps
from .config import config_app
from .course import course_app
from .files import files_app
from .mail import mail_app
from .quiz import quiz_app

# Fix UnicodeEncodeError on Windows by forcing UTF-8 if necessary
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, io.UnsupportedOperation):
        # Fallback for older python versions or specific environments
        pass

app = typer.Typer(help="PUT Electronic Systems CLI")
console = Console()

app.add_typer(config_app, name="config")
app.add_typer(course_app, name="course")
app.add_typer(quiz_app, name="quiz")
app.add_typer(mail_app, name="mail")
app.add_typer(assignment_app, name="assignment")
app.add_typer(files_app, name="files")


@app.command()
@catch_errors
def login(
    username: Optional[str] = typer.Option(None, help="PUT username"),
    password: Optional[str] = typer.Option(None, help="PUT password", hide_input=True),
):
    """Authenticate with PUT eLogin systems."""
    if not username or not password:
        creds = load_credentials()
        if creds:
            username = username or creds["username"]
            password = password or creds["password"]
        else:
            msg = (
                "[yellow]No credentials provided and none stored. "
                "Run 'put-esys config set' or provide options.[/yellow]"
            )
            console.print(msg)
            return

    console.print(f"Logging in as [bold]{username}[/bold]...")
    try:
        authenticate(username, password)
        console.print("[green]Successfully authenticated and session saved.[/green]")
    except Exception as e:
        console.print(f"[red]Login failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
@catch_errors
def save(
    url: str = typer.Argument(..., help="URL to save as HTML"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
):
    """Save a web page as an HTML file."""
    if not output:
        # Create a simple filename from the URL
        slug = re.sub(r"[^a-zA-Z0-9]", "_", url.replace("https://", "").replace("http://", ""))
        output = f"{slug[:50]}.html"

    console.print(f"Fetching [blue]{url}[/blue]...")

    client = EKursyClient()
    session = client.session
    if not session:
        msg = "[yellow]Warning: Not authenticated. Attempting to fetch without session.[/yellow]"
        console.print(msg)
        session = requests.Session()
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        session.headers.update({"User-Agent": ua})

    try:
        resp = session.get(url, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")
        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            console.print(f"[yellow]Warning: Content-Type is {content_type}.[/yellow]")
            console.print("[yellow]For binary files, use 'put-esys download' instead.[/yellow]")

        if "elogin.put.poznan.pl" in resp.url and "elogin.put.poznan.pl" not in url:
            console.print("[yellow]Detected redirection to eLogin.[/yellow]")

        with open(output, "w", encoding="utf-8") as f:
            f.write(resp.text)

        console.print(f"[green]Successfully saved to [bold]{output}[/bold][/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
@catch_errors
def download(
    url: str = typer.Argument(..., help="URL of the resource to download"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
):
    """Download a resource (file, document, etc.) from eKursy or other PUT systems."""
    console.print(f"Downloading [blue]{url}[/blue]...")

    client = EKursyClient()
    check_authenticated(client)

    try:
        resp = client.download_resource(url)

        # Check if it's an HTML landing page for a resource
        content_type = resp.headers.get("Content-Type", "")
        html_content = None
        if "text/html" in content_type:
            from bs4 import BeautifulSoup

            html_content = resp.text
            soup = BeautifulSoup(html_content, "html.parser")
            plugin_links = [
                a["href"]
                for a in soup.find_all("a")
                if a.get("href") and "pluginfile.php" in a["href"]
            ]
            if plugin_links:
                url = plugin_links[0]
                console.print(f"Resolving resource landing page to direct URL: [blue]{url}[/blue]")
                resp = client.download_resource(url)
                html_content = None

        from put_esys.utils.http import download_stream_to_file, extract_filename_from_response

        if not output:
            output = extract_filename_from_response(resp)

        if html_content is not None:
            parent = os.path.dirname(output)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(output, "w", encoding="utf-8") as f:
                f.write(html_content)
            bytes_written = len(html_content.encode("utf-8"))
        else:
            bytes_written = download_stream_to_file(resp, output, chunk_size=8192)

        console.print(f"[green]Successfully downloaded [bold]{output}[/bold][/green]")
        console.print(f"Size: [bold]{bytes_written}[/bold] bytes")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)
