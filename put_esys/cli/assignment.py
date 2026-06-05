import re
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

from put_esys.cli.display import display_assignment
from put_esys.services.ekursy import AssignmentService, EKursyClient

assignment_app = typer.Typer(help="Manage assignments")
console = Console()


def _extract_id(id_or_url: str) -> str:
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            return match.group(1)
        else:
            console.print("[red]Could not parse assignment ID from URL.[/red]")
            raise typer.Exit(code=1)
    return id_or_url


@assignment_app.command("show")
def assignment_show(id_or_url: str = typer.Argument(..., help="Assignment ID or eKursy URL")):
    """Show content and status of a specific assignment."""
    assign_id = _extract_id(id_or_url)
    console.print(f"Fetching assignment [bold]{assign_id}[/bold]...")

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        console.print("Please run [bold]put-esys config set[/bold] first.")
        raise typer.Exit(code=1)

    service = AssignmentService(client.session)
    info, error = service.get_assignment_info(assign_id)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    display_assignment(info)


@assignment_app.command("upload")
def assignment_upload(
    id_or_url: str = typer.Argument(..., help="Assignment ID or eKursy URL"),
    file_path: str = typer.Argument(..., help="Path to the file to upload"),
    name: Optional[str] = typer.Option(None, "--name", help="New filename on upload"),
):
    """Upload a file to an assignment and save the submission changes."""
    assign_id = _extract_id(id_or_url)

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    console.print(f"Uploading [bold]{file_path}[/bold] to assignment [bold]{assign_id}[/bold]...")
    with console.status("[bold green]Saving assignment submission..."):
        try:
            service = AssignmentService(client.session)
            service.save_assignment_submission(assign_id, file_path=file_path, new_name=name)
            console.print("[bold green]Successfully saved assignment submission.[/bold green]")
        except Exception as e:
            console.print(f"[red]Failed to upload file: {e}[/red]")
            raise typer.Exit(code=1)


@assignment_app.command("edit")
def assignment_edit(
    id_or_url: str = typer.Argument(..., help="Assignment ID or eKursy URL"),
    text: Optional[str] = typer.Option(None, "--text", "-t", help="New online text content"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Read online text from file"),
    attach: Optional[str] = typer.Option(None, "--attach", "-a", help="Path to file to attach"),
    remove: Optional[str] = typer.Option(None, "--remove", "-r", help="Attachment to remove"),
    rename: Optional[str] = typer.Option(None, "--rename", help="Name of attachment to rename"),
    new_name: Optional[str] = typer.Option(
        None, "--new-name", help="New filename for uploaded/renamed file"
    ),
):
    """Edit an assignment submission (modify online text or files)."""
    assign_id = _extract_id(id_or_url)

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    if text is None and file is None and attach is None and remove is None and rename is None:
        console.print("[red]Error: You must provide at least one option to edit.[/red]")
        raise typer.Exit(1)

    if rename is not None and new_name is None:
        console.print("[red]Error: You must provide --new-name when renaming a file.[/red]")
        raise typer.Exit(1)

    with console.status(f"[bold green]Editing submission for Assignment {assign_id}..."):
        try:
            service = AssignmentService(client.session)
            service.save_assignment_submission(
                assign_id,
                file_path=attach,
                new_name=new_name,
                new_text=text,
                text_file=file,
                remove_attachment=remove,
                rename_attachment=rename,
            )
            console.print(
                f"[bold green]Successfully saved changes to Assignment {assign_id} "
                f"submission.[/bold green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to edit assignment: {e}[/red]")
            raise typer.Exit(code=1)


@assignment_app.command("delete")
def assignment_delete(
    id_or_url: str = typer.Argument(..., help="Assignment ID or eKursy URL"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Delete without asking for confirmation."
    ),
):
    """Delete/remove the assignment submission."""
    assign_id = _extract_id(id_or_url)

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    if not force:
        msg = (
            f"[bold red]WARNING:[/bold red] You are about to DELETE/REMOVE the submission "
            f"for [bold]Assignment {assign_id}[/bold].\n"
            f"[bold yellow]THIS ACTION WILL RESET YOUR SUBMISSION "
            f"AND REMOVE ALL FILES/TEXT![/bold yellow]"
        )
        console.print(Panel(msg, border_style="red", title="Confirm Submission Deletion"))

        confirm = typer.confirm("Are you absolutely sure you want to delete your submission?")
        if not confirm:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    with console.status(f"[bold green]Deleting submission for Assignment {assign_id}..."):
        try:
            service = AssignmentService(client.session)
            service.delete_assignment_submission(assign_id)
            console.print(
                f"[bold green]Successfully deleted/removed Assignment {assign_id} "
                f"submission.[/bold green]"
            )
        except Exception as e:
            console.print(f"[red]Failed to delete assignment submission: {e}[/red]")
            raise typer.Exit(1)


@assignment_app.command("submit")
def assignment_submit(
    id_or_url: str = typer.Argument(..., help="Assignment ID or eKursy URL"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Submit without asking for confirmation."
    ),
):
    """Finalize and submit the assignment submission. WARNING: This action is irreversible!"""
    assign_id = _extract_id(id_or_url)

    client = EKursyClient()
    if not client.is_authenticated:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    if not force:
        msg = (
            f"[bold red]WARNING:[/bold red] You are about to submit "
            f"[bold]Assignment {assign_id}[/bold].\n"
            f"[bold yellow]THIS ACTION IS IRREVERSIBLE![/bold yellow] "
            "Your answers/files will be submitted for grading."
        )
        console.print(Panel(msg, border_style="red", title="Confirm Assignment Submission"))

        confirm = typer.confirm("Are you absolutely sure you want to submit and finish?")
        if not confirm:
            console.print("[yellow]Submission cancelled.[/yellow]")
            return

    with console.status(f"[bold green]Submitting Assignment {assign_id}..."):
        try:
            service = AssignmentService(client.session)
            success, error = service.submit_assignment_submission(assign_id)
            if success:
                console.print(
                    f"[bold green]Successfully submitted and finalized "
                    f"Assignment {assign_id}![/bold green]"
                )
                if error:
                    console.print(f"[yellow]{error}[/yellow]")
            else:
                console.print(f"[red]Failed to submit assignment: {error}[/red]")
                raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error submitting assignment: {e}[/red]")
            raise typer.Exit(1)
