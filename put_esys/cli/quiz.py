import re
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from put_esys.cli.display import (
    display_json,
    display_quiz_attempt,
    display_quiz_info,
    display_quiz_search_results,
)
from put_esys.cli.helpers import catch_errors, check_authenticated, is_numeric_or_url
from put_esys.models.quiz import QuizSearchResult
from put_esys.services.ekursy import CourseService, EKursyClient, QuizService

quiz_app = typer.Typer(help="Manage quizzes and attempts")
console = Console()


def _extract_id(id_or_url: str) -> str:
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            return match.group(1)
        else:
            console.print("[red]Could not parse quiz ID from URL.[/red]", err=True)
            raise typer.Exit(code=1)
    return id_or_url


@quiz_app.command("info")
@catch_errors
def quiz_info(
    id_or_url: str = typer.Argument(..., help="Quiz ID or eKursy URL"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """Show status and attempts for a specific quiz."""
    quiz_id = _extract_id(id_or_url)
    if not json_format:
        console.print(f"Fetching info for quiz [bold]{quiz_id}[/bold]...", err=True)

    client = EKursyClient()
    check_authenticated(client)

    service = QuizService(client.session)
    info, error = service.get_quiz_info(quiz_id)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    if json_format:
        display_json(info)
    else:
        display_quiz_info(info, quiz_id)


@quiz_app.command("attempt")
@catch_errors
def quiz_attempt(
    quiz_id: int,
    attempt_id: int = typer.Argument(None),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """View a particular quiz attempt (questions and answers)."""
    if not json_format:
        if attempt_id:
            console.print(
                f"Fetching attempt [bold]{attempt_id}[/bold] for quiz [bold]{quiz_id}[/bold]...",
                err=True,
            )
        else:
            console.print(f"Fetching current attempt for quiz [bold]{quiz_id}[/bold]...", err=True)

    client = EKursyClient()
    check_authenticated(client)

    service = QuizService(client.session)
    info, error = service.get_quiz_attempt(str(quiz_id), str(attempt_id) if attempt_id else None)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        if not json_format:
            console.print(
                f"[yellow]Try running [bold]put-esys quiz start {quiz_id}[/bold] "
                "to start a new attempt, "
                f"or [bold]put-esys quiz info {quiz_id}[/bold] to see details.[/yellow]",
                err=True,
            )
        raise typer.Exit(code=1)

    if json_format:
        display_json(info)
    else:
        display_quiz_attempt(info)


@quiz_app.command("edit")
@catch_errors
def quiz_edit(
    quiz_id: int,
    q_no: int,
    text: str = typer.Option(None, "--text", "-t", help="New answer text"),
    file: str = typer.Option(None, "--file", "-f", help="Read answer text from file"),
    attach: Optional[str] = typer.Option(
        None, "--attach", "-a", help="Path to file to attach to the question"
    ),
    remove: Optional[str] = typer.Option(
        None, "--remove", "-r", help="Name of attachment file to remove"
    ),
    rename: Optional[str] = typer.Option(
        None, "--rename", help="Name of existing attachment to rename"
    ),
    new_name: Optional[str] = typer.Option(
        None, "--new-name", help="New filename for the uploaded or renamed attachment"
    ),
):
    """Edit an answer for a specific question in an in-progress attempt."""
    client = EKursyClient()
    check_authenticated(client)

    if file:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()

    if text is None and attach is None and remove is None and rename is None:
        console.print(
            "[red]Error: You must provide --text/--file, --attach, --remove, or --rename.[/red]",
            err=True,
        )
        raise typer.Exit(1)

    if rename is not None and new_name is None:
        console.print(
            "[red]Error: You must provide --new-name when renaming a file via --rename.[/red]",
            err=True,
        )
        raise typer.Exit(1)

    service = QuizService(client.session)
    info, error = service.get_quiz_attempt(str(quiz_id), None)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(1)

    attempt_id = str(info.attempt_id)

    with console.status(f"[bold green]Saving answer for Question {q_no}..."):
        try:
            success = service.save_quiz_answer(
                quiz_id=str(quiz_id),
                attempt_id=attempt_id,
                question_number=q_no,
                new_text=text,
                attachment_path=attach,
                remove_attachment=remove,
                new_name=new_name,
                rename_attachment=rename,
            )
        except Exception as e:
            console.print(f"[red]Error saving answer: {e}[/red]", err=True)
            raise typer.Exit(1)

    if success:
        console.print(
            f"[bold green]Successfully saved answer for Question {q_no} "
            f"in Attempt {attempt_id}.[/bold green]"
        )
        console.print(
            "[yellow]Note: The quiz has NOT been submitted. "
            "You can continue editing or finish in the browser.[/yellow]"
        )
    else:
        console.print("[red]Failed to save answer.[/red]", err=True)


@quiz_app.command("start")
@catch_errors
def quiz_start(quiz_id: int):
    """Start a new quiz attempt."""
    client = EKursyClient()
    check_authenticated(client)

    console.print(f"Starting new attempt for quiz [bold]{quiz_id}[/bold]...")

    with console.status("[bold green]Communicating with eKursy..."):
        service = QuizService(client.session)
        attempt_id, error = service.start_quiz_attempt(str(quiz_id))

    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    console.print(f"[bold green]Successfully started/found attempt {attempt_id}.[/bold green]")
    console.print(f"Run [bold]put-esys quiz attempt {quiz_id} {attempt_id}[/bold] to view it.")


@quiz_app.command("download")
@catch_errors
def quiz_download(
    quiz_id: int,
    q_no: int,
    filename: str,
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename/path"),
):
    """Download an attached file from a quiz question."""
    client = EKursyClient()
    check_authenticated(client)

    service = QuizService(client.session)
    info, error = service.get_quiz_attempt(str(quiz_id), None)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(1)

    target_q = None
    for q in info.questions:
        if q.number == str(q_no):
            target_q = q
            break

    if not target_q:
        console.print(f"[red]Error: Question {q_no} not found in attempt.[/red]", err=True)
        raise typer.Exit(1)

    target_att = None
    for att in target_q.attachments:
        if att.name == filename:
            target_att = att
            break

    if not target_att:
        msg = f"[red]Error: Attachment '{filename}' not found on Question {q_no}.[/red]"
        console.print(msg, err=True)
        if target_q.attachments:
            console.print("Available files:", err=True)
            for att in target_q.attachments:
                console.print(f" - {att.name}", err=True)
        raise typer.Exit(1)

    if not output:
        output = filename

    console.print(f"Downloading [blue]{filename}[/blue] from Question {q_no}...")
    try:
        resp = client.download_resource(target_att.url)
        with open(output, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        console.print(f"[green]Successfully downloaded to [bold]{output}[/bold][/green]")
    except Exception as e:
        console.print(f"[red]Error downloading file: {e}[/red]", err=True)
        raise typer.Exit(1)


@quiz_app.command("submit")
@catch_errors
def quiz_submit(
    quiz_id: int,
    attempt_id: Optional[int] = typer.Argument(
        None, help="Specific attempt ID to submit. If omitted, the active attempt will be found."
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y", "--force", "-f", help="Submit without asking for confirmation."
    ),
):
    """Submit a quiz attempt to finalize and grade it. WARNING: This action is irreversible!"""
    client = EKursyClient()
    check_authenticated(client)

    service = QuizService(client.session)

    if not attempt_id:
        with console.status("[bold green]Checking quiz attempts..."):
            info, error = service.get_quiz_info(str(quiz_id))

        if error:
            console.print(f"[red]Error: {error}[/red]", err=True)
            raise typer.Exit(1)

        in_progress = [a for a in info.attempts if a.status in ["In progress", "W toku"]]
        if in_progress and in_progress[0].id:
            attempt_id = int(in_progress[0].id)
        else:
            msg = "[red]No active (in progress) attempt found for this quiz.[/red]"
            console.print(msg, err=True)
            raise typer.Exit(1)

    if not yes:
        msg = (
            f"[bold red]WARNING:[/bold red] You are about to submit [bold]Quiz {quiz_id}[/bold] "
            f"(Attempt [bold]{attempt_id}[/bold]).\n"
            f"[bold yellow]THIS ACTION IS IRREVERSIBLE![/bold yellow] "
            "Your answers will be submitted for grading."
        )
        console.print(Panel(msg, border_style="red", title="Confirm Quiz Submission"))

        confirm = typer.confirm("Are you absolutely sure you want to submit and finish?")
        if not confirm:
            console.print("[yellow]Submission cancelled.[/yellow]")
            return

    with console.status(f"[bold green]Submitting Attempt {attempt_id} for Quiz {quiz_id}..."):
        success, error = service.submit_quiz_attempt(str(quiz_id), str(attempt_id))

    if success:
        console.print(
            f"[bold green]Successfully submitted and finalized Quiz {quiz_id} "
            f"(Attempt {attempt_id})![/bold green]"
        )
        if error:
            console.print(f"[yellow]{error}[/yellow]")
    else:
        console.print(f"[red]Failed to submit quiz: {error}[/red]", err=True)
        raise typer.Exit(1)


@quiz_app.command("search")
@catch_errors
def quiz_search(
    query: str = typer.Argument(..., help="Quiz name query to search for"),
    course: str = typer.Option(..., "--course", "-c", help="Course ID, URL, or name query"),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """Search for quizzes in a course by name substring."""
    client = EKursyClient()
    check_authenticated(client)

    course_service = CourseService(client.session)
    course_id = course

    if not is_numeric_or_url(course):
        resolved_id, matches, error = course_service.resolve_course_id_by_name(course)
        if error:
            console.print(f"[red]Error resolving course name: {error}[/red]", err=True)
            raise typer.Exit(code=1)
        if not matches:
            console.print(f"[red]Error: No courses matched '{course}'[/red]", err=True)
            raise typer.Exit(code=1)
        if len(matches) > 1:
            console.print(
                f"[yellow]Multiple courses matched '{course}':[/yellow]", err=True
            )
            for m in matches:
                console.print(f" - ID: {m.id} | {m.title}", err=True)
            raise typer.Exit(code=1)

        course_id = resolved_id
        if not json_format:
            console.print(
                f"Auto-resolved course '{course}' to ID {course_id} ({matches[0].title})",
                err=True,
            )
    elif course.startswith("http"):
        match = re.search(r"id=(\d+)", course)
        if match:
            course_id = match.group(1)
        else:
            console.print("[red]Could not parse course ID from URL.[/red]", err=True)
            raise typer.Exit(code=1)

    if not json_format:
        console.print(f"Fetching quizzes in course [bold]{course_id}[/bold]...", err=True)

    content, error = course_service.get_course_content(course_id)
    if error:
        console.print(f"[red]Error: {error}[/red]", err=True)
        raise typer.Exit(code=1)

    matched_quizzes = []
    query_lower = query.lower()
    for section in content.sections:
        for activity in section.activities:
            if activity.type == "quiz":
                if query_lower in activity.name.lower():
                    # Extract quiz ID from url
                    quiz_id = None
                    if activity.url:
                        id_match = re.search(r"id=(\d+)", activity.url)
                        if id_match:
                            quiz_id = id_match.group(1)
                    if quiz_id:
                        matched_quizzes.append(
                            QuizSearchResult(id=quiz_id, name=activity.name, url=activity.url)
                        )

    if not matched_quizzes:
        if json_format:
            display_json([])
        else:
            console.print(f"[yellow]No quizzes found matching '{query}'.[/yellow]")
        return

    if json_format:
        display_json(matched_quizzes)
    else:
        display_quiz_search_results(matched_quizzes)
