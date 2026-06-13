import re

import typer
from rich.console import Console

from put_esys.cli.display import display_course_content, display_courses_list, display_json
from put_esys.cli.helpers import catch_errors, check_authenticated, is_numeric_or_url
from put_esys.services.ekursy import CourseService, EKursyClient

course_app = typer.Typer(help="Manage courses and content")
console = Console()


@course_app.command("list")
@catch_errors
def course_list(
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """List enrolled courses from eKursy."""
    if not json_format:
        console.print("Fetching courses from eKursy...", err=True)

    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)
    courses, error = service.get_courses()
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    if not courses:
        if json_format:
            display_json([])
        else:
            console.print("[yellow]No courses found or could not parse course list.[/yellow]")
        return

    if json_format:
        display_json(courses)
    else:
        display_courses_list(courses)


@course_app.command("show")
@catch_errors
def course_show(
    id_or_url: str = typer.Argument(..., help="Course ID, URL, or course title query"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """Show content of a specific course."""
    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)
    course_id = id_or_url

    if not is_numeric_or_url(id_or_url):
        resolved_id, matches, error = service.resolve_course_id_by_name(id_or_url)
        if error:
            console.print(f"[red]Error resolving course name: {error}[/red]", err=True)
            raise typer.Exit(code=1)
        if not matches:
            console.print(f"[red]Error: No courses matched '{id_or_url}'[/red]", err=True)
            raise typer.Exit(code=1)
        if len(matches) > 1:
            console.print(
                f"[yellow]Multiple courses matched '{id_or_url}':[/yellow]", err=True
            )
            for m in matches:
                console.print(f" - ID: {m.id} | {m.title}", err=True)
            raise typer.Exit(code=1)

        course_id = resolved_id
        if not json_format:
            console.print(
                f"Auto-resolved '{id_or_url}' to course ID {course_id} ({matches[0].title})",
                err=True,
            )
    elif id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            course_id = match.group(1)
        else:
            console.print("[red]Could not parse course ID from URL.[/red]", err=True)
            raise typer.Exit(code=1)

    if not json_format:
        console.print(f"Fetching content for course [bold]{course_id}[/bold]...", err=True)

    content, error = service.get_course_content(course_id)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    if json_format:
        display_json(content)
    else:
        display_course_content(content)


@course_app.command("search")
@catch_errors
def course_search(
    query: str = typer.Argument(..., help="Substring to search in course titles"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """Search enrolled courses by title substring or ID."""
    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)
    _, matches, error = service.resolve_course_id_by_name(query)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    if not matches:
        if json_format:
            display_json([])
        else:
            console.print(f"[yellow]No courses found matching '{query}'.[/yellow]")
        return

    if json_format:
        display_json(matches)
    else:
        display_courses_list(matches)
