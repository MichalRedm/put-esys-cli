import typer
from typing import Optional
from .auth import authenticate, ensure_authenticated_session
from .scraper import get_ekursy_courses
from .config import save_credentials, load_credentials, clear_credentials
from rich.console import Console
from rich.table import Table

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
        console.print("[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]")
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
            console.print("[yellow]No credentials provided and none stored. Run 'put-esys config set' or provide options.[/yellow]")
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
            if activity['type'] == 'folder': icon = "[DIR]"
            elif activity['type'] == 'assign': icon = "[ASSIGN]"
            elif activity['type'] == 'quiz': icon = "[QUIZ]"
            elif activity['type'] == 'forum': icon = "[FORUM]"
            elif activity['type'] == 'url': icon = "[URL]"
            
            section_tree.add(f"{icon} [magenta]{activity['name']}[/magenta] ([blue]{activity['url']}[/blue])")
            
    console.print(tree)

if __name__ == "__main__":
    app()
