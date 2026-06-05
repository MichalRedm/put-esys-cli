import re
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from put_esys.cli.display import display_quiz_attempt, display_quiz_info
from put_esys.services.ekursy import EKursyClient, QuizService

quiz_app = typer.Typer(help="Manage quizzes and attempts")
console = Console()


def _extract_id(id_or_url: str) -> str:
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            return match.group(1)
        else:
            console.print("[red]Could not parse quiz ID from URL.[/red]")
            raise typer.Exit(code=1)
    return id_or_url


@quiz_app.command("info")
def quiz_info(id_or_url: str = typer.Argument(..., help="Quiz ID or eKursy URL")):
    """Show status and attempts for a specific quiz."""
    quiz_id = _extract_id(id_or_url)
    console.print(f"Fetching info for quiz [bold]{quiz_id}[/bold]...")

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    service = QuizService(client.session)
    info, error = service.get_quiz_info(quiz_id)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    display_quiz_info(info, quiz_id)


@quiz_app.command("attempt")
def quiz_attempt(quiz_id: int, attempt_id: int = typer.Argument(None)):
    """View a particular quiz attempt (questions and answers)."""
    if attempt_id:
        console.print(
            f"Fetching attempt [bold]{attempt_id}[/bold] for quiz [bold]{quiz_id}[/bold]..."
        )
    else:
        console.print(f"Fetching current attempt for quiz [bold]{quiz_id}[/bold]...")

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    service = QuizService(client.session)
    info, error = service.get_quiz_attempt(str(quiz_id), str(attempt_id) if attempt_id else None)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        console.print(
            f"[yellow]Try running [bold]put-esys quiz start {quiz_id}[/bold] "
            "to start a new attempt, "
            f"or [bold]put-esys quiz info {quiz_id}[/bold] to see details.[/yellow]"
        )
        raise typer.Exit(code=1)

    display_quiz_attempt(info)


@quiz_app.command("edit")
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
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    if file:
        with open(file, "r", encoding="utf-8") as f:
            text = f.read()

    if text is None and attach is None and remove is None and rename is None:
        console.print(
            "[red]Error: You must provide --text/--file, --attach, --remove, or --rename.[/red]"
        )
        raise typer.Exit(1)

    if rename is not None and new_name is None:
        console.print(
            "[red]Error: You must provide --new-name when renaming a file via --rename.[/red]"
        )
        raise typer.Exit(1)

    service = QuizService(client.session)
    info, error = service.get_quiz_attempt(str(quiz_id), None)
    if error:
        console.print(f"[red]Error: {error}[/red]")
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
            console.print(f"[red]Error saving answer: {e}[/red]")
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
        console.print("[red]Failed to save answer.[/red]")


@quiz_app.command("start")
def quiz_start(quiz_id: int):
    """Start a new quiz attempt."""
    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    console.print(f"Starting new attempt for quiz [bold]{quiz_id}[/bold]...")

    with console.status("[bold green]Communicating with eKursy..."):
        service = QuizService(client.session)
        attempt_id, error = service.start_quiz_attempt(str(quiz_id))

    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[bold green]Successfully started/found attempt {attempt_id}.[/bold green]")
    console.print(f"Run [bold]put-esys quiz attempt {quiz_id} {attempt_id}[/bold] to view it.")


@quiz_app.command("download")
def quiz_download(
    quiz_id: int,
    q_no: int,
    filename: str,
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename/path"),
):
    """Download an attached file from a quiz question."""
    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    service = QuizService(client.session)
    info, error = service.get_quiz_attempt(str(quiz_id), None)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(1)

    target_q = None
    for q in info.questions:
        if q.number == str(q_no):
            target_q = q
            break

    if not target_q:
        console.print(f"[red]Error: Question {q_no} not found in attempt.[/red]")
        raise typer.Exit(1)

    target_att = None
    for att in target_q.attachments:
        if att.name == filename:
            target_att = att
            break

    if not target_att:
        console.print(f"[red]Error: Attachment '{filename}' not found on Question {q_no}.[/red]")
        if target_q.attachments:
            console.print("Available files:")
            for att in target_q.attachments:
                console.print(f" - {att.name}")
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
        console.print(f"[red]Error downloading file: {e}[/red]")
        raise typer.Exit(1)


@quiz_app.command("submit")
def quiz_submit(
    quiz_id: int,
    attempt_id: Optional[int] = typer.Argument(
        None, help="Specific attempt ID to submit. If omitted, the active attempt will be found."
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Submit without asking for confirmation."
    ),
):
    """Submit a quiz attempt to finalize and grade it. WARNING: This action is irreversible!"""
    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    service = QuizService(client.session)

    if not attempt_id:
        with console.status("[bold green]Checking quiz attempts..."):
            info, error = service.get_quiz_info(str(quiz_id))

        if error:
            console.print(f"[red]Error: {error}[/red]")
            raise typer.Exit(1)

        in_progress = [a for a in info.attempts if a.status in ["In progress", "W toku"]]
        if in_progress and in_progress[0].id:
            attempt_id = int(in_progress[0].id)
        else:
            console.print("[red]No active (in progress) attempt found for this quiz.[/red]")
            raise typer.Exit(1)

    if not force:
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
        console.print(f"[red]Failed to submit quiz: {error}[/red]")
        raise typer.Exit(1)
