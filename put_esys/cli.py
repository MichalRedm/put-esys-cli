import io
import sys
from typing import Optional

import typer
from markdownify import markdownify
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from .auth import authenticate, ensure_authenticated_session
from .config import clear_credentials, load_credentials, save_credentials
from .scraper import get_ekursy_courses

# Fix UnicodeEncodeError on Windows by forcing UTF-8 if necessary
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        # Fallback for older python versions or specific environments
        pass

app = typer.Typer(help="PUT Electronic Systems CLI")
config_app = typer.Typer(help="Manage your PUT credentials")
app.add_typer(config_app, name="config")

console = Console()

@config_app.command("set")
def config_set():
    """Set your PUT credentials."""
    username = typer.prompt("PUT email (e.g. jan.kowalski@student.put.poznan.pl)")
    password = typer.prompt("PUT password", hide_input=True)
    save_credentials(username, password)
    console.print("[green]Credentials saved successfully.[/green]")

@config_app.command("show")
def config_show():
    """Show current configuration (password masked)."""
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg)
        return
    
    table = Table(title="PUT CLI Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Username", creds['username'])
    table.add_row("Password", "*" * 8)
    
    console.print(table)

@config_app.command("delete")
def config_delete():
    """Remove stored credentials."""
    if typer.confirm("Are you sure you want to delete your stored credentials?"):
        clear_credentials()
        console.print("[red]Credentials deleted.[/red]")

@app.command()
def login(
    username: Optional[str] = typer.Option(None, help="PUT username"),
    password: Optional[str] = typer.Option(None, help="PUT password", hide_input=True),
):
    """Authenticate with PUT eLogin systems."""
    if not username or not password:
        creds = load_credentials()
        if creds:
            username = username or creds['username']
            password = password or creds['password']
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
def ekursy():
    """List enrolled courses from eKursy."""
    console.print("Fetching courses from eKursy...")
    
    # Use lazy authentication
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        console.print("Please run [bold]put-esys config set[/bold] first to save your credentials.")
        raise typer.Exit(code=1)
        
    courses, error = get_ekursy_courses(session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    if not courses:
        console.print("[yellow]No courses found or could not parse course list.[/yellow]")
        return

    table = Table(title=f"Enrolled Courses ({len(courses)})")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Course Title", style="magenta")
    table.add_column("URL", style="blue")

    for i, course in enumerate(courses, 1):
        table.add_row(str(i), course['title'], course['url'])

    console.print(table)

@app.command()
def course(id_or_url: str = typer.Argument(..., help="Course ID or eKursy URL")):
    """Show content of a specific course."""
    import re

    from rich.tree import Tree
    
    # Extract ID if URL is provided
    course_id = id_or_url
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            course_id = match.group(1)
        else:
            console.print("[red]Could not parse course ID from URL.[/red]")
            raise typer.Exit(code=1)

    console.print(f"Fetching content for course [bold]{course_id}[/bold]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        console.print("Please run [bold]put-esys config set[/bold] first.")
        raise typer.Exit(code=1)
        
    from .scraper import get_course_content
    content, error = get_course_content(course_id, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    tree = Tree(f"[bold white on blue] {content['title']} [/bold white on blue]")
    
    for section in content['sections']:
        section_tree = tree.add(f"[bold cyan]{section['name']}[/bold cyan]")
        for activity in section['activities']:
            icon = "[FILE]"
            if activity['type'] == 'folder':
                icon = "[DIR]"
            elif activity['type'] == 'assign':
                icon = "[ASSIGN]"
            elif activity['type'] == 'quiz':
                icon = "[QUIZ]"
            elif activity['type'] == 'forum':
                icon = "[FORUM]"
            elif activity['type'] == 'url':
                icon = "[URL]"
            
            section_tree.add(
                f"{icon} [magenta]{activity['name']}[/magenta] ([blue]{activity['url']}[/blue])"
            )
            
    console.print(tree)

@app.command()
def save(
    url: str = typer.Argument(..., help="URL to save as HTML"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
):
    """Save a web page as an HTML file."""
    import re
    
    if not output:
        # Create a simple filename from the URL
        slug = re.sub(r'[^a-zA-Z0-9]', '_', url.replace('https://', '').replace('http://', ''))
        output = f"{slug[:50]}.html"

    console.print(f"Fetching [blue]{url}[/blue]...")
    
    session = ensure_authenticated_session()
    if not session:
        msg = "[yellow]Warning: Not authenticated. Attempting to fetch without session.[/yellow]"
        console.print(msg)
        import requests
        session = requests.Session()
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        session.headers.update({"User-Agent": ua})
    
    try:
        resp = session.get(url, stream=True)
        resp.raise_for_status()
        
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            console.print(f"[yellow]Warning: Content-Type is {content_type}.[/yellow]")
            console.print("[yellow]For binary files, use 'put-esys download' instead.[/yellow]")
            
        # Check if we were redirected to a login page
        if "elogin.put.poznan.pl" in resp.url and "elogin.put.poznan.pl" not in url:
             console.print("[yellow]Detected redirection to eLogin.[/yellow]")
        
        with open(output, "w", encoding="utf-8") as f:
            f.write(resp.text)
        
        console.print(f"[green]Successfully saved to [bold]{output}[/bold][/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def download(
    url: str = typer.Argument(..., help="URL of the resource to download"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
):
    """Download a resource (file, document, etc.) from eKursy or other PUT systems."""
    import os
    import re
    
    console.print(f"Downloading [blue]{url}[/blue]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    try:
        resp = session.get(url, stream=True)
        resp.raise_for_status()
        
        # Try to get filename from Content-Disposition
        cd = resp.headers.get('Content-Disposition')
        if not output and cd:
            match = re.findall('filename=(.+)', cd)
            if match:
                output = match[0].strip(' "')
        
        # Fallback: get filename from URL
        if not output:
            output = os.path.basename(url.split('?')[0])
            if not output or output == 'pluginfile.php':
                 # If it's a generic Moodle file URL, try to find the filename in the path
                 parts = url.split('/')
                 if len(parts) > 1:
                      output = parts[-1].split('?')[0]
            
            if not output:
                 output = "downloaded_file"

        with open(output, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                
        console.print(f"[green]Successfully downloaded [bold]{output}[/bold][/green]")
        console.print(f"Size: [bold]{resp.headers.get('Content-Length', 'unknown')}[/bold] bytes")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def quiz(id_or_url: str = typer.Argument(..., help="Quiz ID or eKursy URL")):
    """Show status and attempts for a specific quiz."""
    import re
    
    # Extract ID if URL is provided
    quiz_id = id_or_url
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            quiz_id = match.group(1)
        else:
            console.print("[red]Could not parse quiz ID from URL.[/red]")
            raise typer.Exit(code=1)

    console.print(f"Fetching info for quiz [bold]{quiz_id}[/bold]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    from .scraper import get_quiz_info
    info, error = get_quiz_info(quiz_id, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold white on blue] {info['title']} [/bold white on blue]")
    console.print(f"[bold]{info['grading_method']}[/bold]\n")

    if not info['attempts']:
        console.print("[yellow]No attempts found for this quiz.[/yellow]")
    else:
        table = Table(title="Your Attempts")
        table.add_column("Attempt", style="cyan")
        table.add_column("ID", style="yellow")
        table.add_column("Status", style="magenta")
        table.add_column("Started", style="blue")
        table.add_column("Grade", style="green")

        for att in info['attempts']:
            table.add_row(
                att.get('number', '1'),
                att.get('id', 'N/A'),
                att.get('status', 'Unknown'),
                att.get('started', 'Unknown'),
                att.get('grade', 'N/A')
            )
        console.print(table)

    if info['buttons']:
        console.print("\n[bold]Available Actions:[/bold]")
        for btn in info['buttons']:
            console.print(f" - {btn['text']}: [blue]{btn['url']}[/blue]")

@app.command()
def attempt(quiz_id: str, attempt_id: str):
    """View a particular quiz attempt (questions and answers)."""
    console.print(f"Fetching attempt [bold]{attempt_id}[/bold] for quiz [bold]{quiz_id}[/bold]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    from .scraper import get_quiz_attempt
    info, error = get_quiz_attempt(quiz_id, attempt_id, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    import re

    for q in info['questions']:
        console.print(f"\n[bold cyan]Question {q['number']}[/bold cyan] ({q['state']})")
        
        # Convert HTML to markdown
        q_md_raw = markdownify(q['text'])
        a_md_raw = markdownify(q['answer'])
        
        # Post-process to show URLs explicitly: [Text](URL) -> [Text] (URL)
        # Using a regex that handles basic markdown links
        link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
        q_md_text = re.sub(link_pattern, r'[\1] (\2)', q_md_raw)
        a_md_text = re.sub(link_pattern, r'[\1] (\2)', a_md_raw)

        q_md = Markdown(q_md_text)
        a_md = Markdown(a_md_text)
        
        console.print(Panel(q_md, title="Question Text", border_style="blue"))
        console.print(Panel(a_md, title="Your Answer", border_style="green"))

if __name__ == "__main__":
    app()
