from typing import List, Optional

import typer
from rich.console import Console
from rich.table import Table

from put_esys.cli.display import display_email_details, display_emails_list, display_json
from put_esys.cli.helpers import catch_errors
from put_esys.services.config import load_credentials
from put_esys.services.mail import MailClient

mail_app = typer.Typer(help="Manage your PUT email")
console = Console()


def _get_mail_client() -> Optional[MailClient]:
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg, err=True)
        return None
    return MailClient(creds["username"], creds["password"])


@mail_app.command("folders")
@catch_errors
def mail_folders(
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """List all available mail folders/mailboxes on the server."""
    client = _get_mail_client()
    if not client:
        raise typer.Exit(code=1)

    if not json_format:
        console.print("Fetching mail folders...", err=True)

    try:
        folders = client.list_folders()
    except Exception as e:
        console.print(f"[red]Failed to list folders: {e}[/red]", err=True)
        raise typer.Exit(code=1)

    if not folders:
        if json_format:
            display_json([])
        else:
            console.print("[yellow]No folders found.[/yellow]")
        return

    if json_format:
        display_json(folders)
    else:
        table = Table(title="Available Mail Folders")
        table.add_column("Folder Name", style="cyan")
        for folder in folders:
            table.add_row(folder)
        console.print(table)


@mail_app.command("list")
@catch_errors
def mail_list(
    limit: int = typer.Option(10, help="Number of emails to list"),
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Search query (e.g., sender or subject)"
    ),
    folder: str = typer.Option(
        "INBOX", "--folder", "-f", help="Mailbox folder to list from (e.g., INBOX, Sent)"
    ),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """List recent emails from a specific folder, optionally filtered by a search query."""
    client = _get_mail_client()
    if not client:
        raise typer.Exit(code=1)

    if not json_format:
        console.print(f"Fetching emails from {folder}...", err=True)

    try:
        emails = client.list_emails(folder=folder, limit=limit, search_query=search)
    except Exception as e:
        console.print(f"[red]Failed to list emails: {e}[/red]", err=True)
        raise typer.Exit(code=1)

    if not emails:
        if json_format:
            display_json([])
        else:
            if search:
                console.print(
                    f"[yellow]No emails found matching '{search}' in {folder}.[/yellow]"
                )
            else:
                console.print(f"[yellow]No emails found in {folder}.[/yellow]")
        return

    if json_format:
        display_json(emails)
    else:
        display_emails_list(emails, folder=folder)


@mail_app.command("read")
@catch_errors
def mail_read(
    mail_id: str,
    folder: str = typer.Option(
        "INBOX", "--folder", "-f", help="Mailbox folder where the email is located"
    ),
    json_format: bool = typer.Option(False, "--json", help="Output raw JSON data"),
):
    """Read a specific email by its ID."""
    client = _get_mail_client()
    if not client:
        raise typer.Exit(code=1)

    if not json_format:
        console.print(f"Fetching email {mail_id} from {folder}...", err=True)

    try:
        email_data = client.get_email_details(mail_id, folder=folder)
    except Exception as e:
        console.print(f"[red]Failed to fetch email: {e}[/red]", err=True)
        raise typer.Exit(code=1)

    if not email_data:
        console.print(f"[red]Email with ID {mail_id} not found in {folder}.[/red]", err=True)
        raise typer.Exit(code=1)

    if json_format:
        display_json(email_data)
    else:
        display_email_details(email_data, folder=folder)


@mail_app.command("download")
@catch_errors
def mail_download(
    mail_id: str = typer.Argument(..., help="ID of the email"),
    filename: str = typer.Argument(..., help="Name of the attachment to download"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output path for the downloaded attachment"
    ),
    folder: str = typer.Option(
        "INBOX", "--folder", "-f", help="Mailbox folder where the email is located"
    ),
):
    """Download an attachment from a specific email."""
    client = _get_mail_client()
    if not client:
        raise typer.Exit(code=1)

    if not output:
        output = filename

    console.print(f"Downloading attachment '{filename}' from email {mail_id} in {folder}...")
    try:
        success = client.download_attachment(mail_id, filename, output, folder=folder)
    except Exception as e:
        console.print(f"[red]Error downloading attachment: {e}[/red]", err=True)
        raise typer.Exit(code=1)

    if success:
        console.print(f"[green]Successfully downloaded attachment to [bold]{output}[/bold][/green]")
    else:
        msg = f"[red]Failed to download attachment '{filename}'. Does it exist in the email?[/red]"
        console.print(msg, err=True)
        raise typer.Exit(code=1)


@mail_app.command("send")
@catch_errors
def mail_send(
    to: str = typer.Option(..., prompt="To", help="Recipient email address"),
    subject: str = typer.Option(..., prompt="Subject", help="Email subject"),
    body: Optional[str] = typer.Option(None, "--body", "-b", help="Email body"),
    body_file: Optional[str] = typer.Option(
        None, "--body-file", "-f", help="Path to file containing email body"
    ),
    attach: Optional[List[str]] = typer.Option(
        None, "--attach", "-a", help="Path to file(s) to attach to the email"
    ),
):
    """Send an email."""
    import os

    client = _get_mail_client()
    if not client:
        raise typer.Exit(code=1)

    email_body = body
    if body_file:
        if body:
            console.print("[red]Error: Cannot specify both --body and --body-file.[/red]", err=True)
            raise typer.Exit(code=1)
        if not os.path.exists(body_file):
            console.print(f"[red]Error: Body file not found at '{body_file}'.[/red]", err=True)
            raise typer.Exit(code=1)
        try:
            with open(body_file, "r", encoding="utf-8") as f:
                email_body = f.read()
        except Exception as e:
            console.print(f"[red]Failed to read body file: {e}[/red]", err=True)
            raise typer.Exit(code=1)

    if email_body is None:
        email_body = typer.prompt("Body")

    console.print("Sending email...")
    try:
        client.send_email(to, subject, email_body, attachment_paths=attach)
        console.print("[green]Email sent successfully.[/green]")
    except Exception as e:
        console.print(f"[red]Failed to send email: {e}[/red]", err=True)
        raise typer.Exit(code=1)
