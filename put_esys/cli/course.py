import re

import typer
from rich.console import Console

from put_esys.cli.display import display_course_content, display_courses_list
from put_esys.services.ekursy import CourseService, EKursyClient

course_app = typer.Typer(help="Manage courses and content")
console = Console()


@course_app.command("list")
def course_list():
    """List enrolled courses from eKursy."""
    console.print("Fetching courses from eKursy...")

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        console.print("Please run [bold]put-esys config set[/bold] first to save your credentials.")
        raise typer.Exit(code=1)

    service = CourseService(client.session)
    courses, error = service.get_courses()
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    if not courses:
        console.print("[yellow]No courses found or could not parse course list.[/yellow]")
        return

    display_courses_list(courses)


@course_app.command("show")
def course_show(id_or_url: str = typer.Argument(..., help="Course ID or eKursy URL")):
    """Show content of a specific course."""
    course_id = id_or_url
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            course_id = match.group(1)
        else:
            console.print("[red]Could not parse course ID from URL.[/red]")
            raise typer.Exit(code=1)

    console.print(f"Fetching content for course [bold]{course_id}[/bold]...")

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        console.print("Please run [bold]put-esys config set[/bold] first.")
        raise typer.Exit(code=1)

    service = CourseService(client.session)
    content, error = service.get_course_content(course_id)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    display_course_content(content)
