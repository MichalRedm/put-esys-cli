import re
from typing import Optional

import typer
from rich.console import Console

from put_esys.cli.display import display_course_content, display_courses_list
from put_esys.cli.helpers import (
    catch_errors,
    check_authenticated,
    handle_output,
    is_numeric_or_url,
)
from put_esys.services.ekursy import CourseService, EKursyClient

course_app = typer.Typer(help="Manage courses and content")
console = Console()


@course_app.command("list")
@catch_errors
def course_list(
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """List enrolled courses from eKursy."""
    if not json_format and not output:
        console.print("Fetching courses from eKursy...", err=True)

    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)
    courses, error = service.get_courses()
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    if not courses:
        handle_output([], output, json_format, None)
        if not json_format and not output:
            console.print("[yellow]No courses found or could not parse course list.[/yellow]")
        return

    handle_output(courses, output, json_format, display_courses_list)


@course_app.command("show")
@catch_errors
def course_show(
    id_or_url: str = typer.Argument(..., help="Course ID, URL, or course title query"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
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
        if not json_format and not output:
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

    if not json_format and not output:
        console.print(f"Fetching content for course [bold]{course_id}[/bold]...", err=True)

    content, error = service.get_course_content(course_id)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    handle_output(content, output, json_format, display_course_content)


@course_app.command("search")
@catch_errors
def course_search(
    query: str = typer.Argument(..., help="Substring to search in course titles"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
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
        handle_output([], output, json_format, None)
        if not json_format and not output:
            console.print(f"[yellow]No courses found matching '{query}'.[/yellow]")
        return

    handle_output(matches, output, json_format, display_courses_list)
