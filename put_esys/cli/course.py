import re
import sys
from typing import Optional

import typer
from rich.console import Console

from put_esys.cli.display import (
    display_categories,
    display_course_content,
    display_courses_list,
    display_discovered_courses,
    display_enrolment_result,
)
from put_esys.cli.helpers import (
    catch_errors,
    check_authenticated,
    handle_output,
    is_numeric_or_url,
)
from put_esys.models.course import EnrolmentStatus
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
    all_courses: bool = typer.Option(
        False, "--all", "-a", help="Search global university catalog instead of enrolled courses"
    ),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Search courses by title substring or ID (enrolled by default, or all courses via --all)."""
    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)

    if all_courses:
        if not json_format and not output:
            console.print(f"Searching global eKursy catalog for '{query}'...", err=True)
        courses, error = service.search_all_courses(query)
        if error:
            console.print(f"[red]Error: {error}[/red]", err=True)
            raise typer.Exit(code=1)

        if not courses:
            handle_output([], output, json_format, None)
            if not json_format and not output:
                console.print(f"[yellow]No courses found matching '{query}'.[/yellow]")
            return

        handle_output(courses, output, json_format, display_discovered_courses)
        return

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


@course_app.command("find")
@catch_errors
def course_find(
    query: str = typer.Argument(..., help="Substring to search in global course catalog"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Search global eKursy course catalog across all categories."""
    if not json_format and not output:
        console.print(f"Searching global eKursy catalog for '{query}'...", err=True)

    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)
    courses, error = service.search_all_courses(query)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    if not courses:
        handle_output([], output, json_format, None)
        if not json_format and not output:
            console.print(f"[yellow]No courses found matching '{query}'.[/yellow]")
        return

    handle_output(courses, output, json_format, display_discovered_courses)


@course_app.command("categories")
@catch_errors
def course_categories(
    category_id: Optional[str] = typer.Argument(
        None, help="Category ID to browse (leave empty for top-level faculties)"
    ),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Browse course categories and discover courses inside a category."""
    if not json_format and not output:
        target = f"category {category_id}" if category_id else "top-level categories"
        console.print(f"Fetching {target} from eKursy...", err=True)

    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)
    result, error = service.get_categories(category_id)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    handle_output(result, output, json_format, display_categories)


@course_app.command("enrol")
@catch_errors
def course_enrol(
    id_or_name: str = typer.Argument(..., help="Course ID, URL, or course title query"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Course enrolment key / password"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Non-interactive mode; skip prompts"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Self-enrol into a course, providing an enrolment key if required."""
    client = EKursyClient()
    check_authenticated(client)

    service = CourseService(client.session)
    course_id = id_or_name

    if not is_numeric_or_url(id_or_name):
        resolved_id, matches, error = service.resolve_course_id_from_all_courses(id_or_name)
        if error:
            console.print(f"[red]Error resolving course name: {error}[/red]", err=True)
            raise typer.Exit(code=1)
        if not matches:
            console.print(f"[red]Error: No courses matched '{id_or_name}'[/red]", err=True)
            raise typer.Exit(code=1)
        if len(matches) > 1 and not resolved_id:
            console.print(
                f"[yellow]Multiple courses matched '{id_or_name}':[/yellow]", err=True
            )
            for m in matches[:10]:
                console.print(f" - ID: {m.id} | {m.title}", err=True)
            raise typer.Exit(code=1)

        course_id = resolved_id
        if not json_format and not output:
            console.print(
                f"Auto-resolved '{id_or_name}' to course ID {course_id} ({matches[0].title})",
                err=True,
            )
    elif id_or_name.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_name)
        if match:
            course_id = match.group(1)
        else:
            console.print("[red]Could not parse course ID from URL.[/red]", err=True)
            raise typer.Exit(code=1)

    if not json_format and not output:
        console.print(f"Checking enrolment status for course {course_id}...", err=True)

    info, error = service.get_enrolment_info(course_id)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    if info.status == EnrolmentStatus.ALREADY_ENROLLED:
        msg = f"Already enrolled in course '{info.course_title}'."
        payload = {"course_id": course_id, "success": True, "message": msg}
        handle_output(
            payload,
            output,
            json_format,
            lambda _: display_enrolment_result(course_id, True, msg),
        )
        return

    if info.status == EnrolmentStatus.NO_SELF_ENROLMENT:
        msg = (
            f"Self-enrolment is not available for '{info.course_title}'. "
            "Please contact the instructor to be added."
        )
        payload = {"course_id": course_id, "success": False, "message": msg}
        handle_output(
            payload,
            output,
            json_format,
            lambda _: display_enrolment_result(course_id, False, msg),
        )
        raise typer.Exit(code=1)

    enrolment_key = key
    if info.status == EnrolmentStatus.CAN_ENROL_KEY_REQUIRED and not enrolment_key:
        if yes or not sys.stdin.isatty():
            msg = (
                f"Course '{info.course_title}' requires an enrolment key. "
                "Provide it via '--key <KEY>'."
            )
            payload = {"course_id": course_id, "success": False, "message": msg}
            handle_output(
                payload,
                output,
                json_format,
                lambda _: display_enrolment_result(course_id, False, msg),
            )
            raise typer.Exit(code=1)

        enrolment_key = typer.prompt(
            f"Enter enrolment key for '{info.course_title}'", hide_input=True
        )

    if not json_format and not output:
        console.print(f"Submitting self-enrolment for course {course_id}...", err=True)

    success, message = service.enrol_course(course_id, enrolment_key)
    payload = {"course_id": course_id, "success": success, "message": message}
    handle_output(
        payload,
        output,
        json_format,
        lambda _: display_enrolment_result(course_id, success, message),
    )

    if not success:
        raise typer.Exit(code=1)

