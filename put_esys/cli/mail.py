from typing import List, Optional

import typer
from rich.console import Console

from put_esys.cli.display import display_email_details, display_emails_list
from put_esys.services.config import load_credentials
from put_esys.services.mail import MailClient

mail_app = typer.Typer(help="Manage your PUT email")
console = Console()


def _get_mail_client() -> Optional[MailClient]:
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg)
        return None
    return MailClient(creds["username"], creds["password"])


@mail_app.command("list")
def mail_list(
    limit: int = typer.Option(10, help="Number of emails to list"),
    search: Optional[str] = typer.Option(
        None, "--search", "-s", help="Search query (e.g., sender or subject)"
    ),
):
    """List recent emails from your INBOX, optionally filtered by a search query."""
    client = _get_mail_client()
    if not client:
        return

    with console.status("[bold green]Fetching emails..."):
        try:
            emails = client.list_emails(limit=limit, search_query=search)
        except Exception as e:
            console.print(f"[red]Failed to list emails: {e}[/red]")
            return

    if not emails:
        if search:
            console.print(f"[yellow]No emails found matching '{search}'.[/yellow]")
        else:
            console.print("[yellow]No emails found.[/yellow]")
        return

    display_emails_list(emails)


@mail_app.command("read")
def mail_read(mail_id: str):
    """Read a specific email by its ID."""
    client = _get_mail_client()
    if not client:
        return

    with console.status(f"[bold green]Fetching email {mail_id}..."):
        try:
            email_data = client.get_email_details(mail_id)
        except Exception as e:
            console.print(f"[red]Failed to fetch email: {e}[/red]")
            return

    if not email_data:
        console.print(f"[red]Email with ID {mail_id} not found.[/red]")
        return

    display_email_details(email_data)


@mail_app.command("download")
def mail_download(
    mail_id: str = typer.Argument(..., help="ID of the email"),
    filename: str = typer.Argument(..., help="Name of the attachment to download"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output path for the downloaded attachment"
    ),
):
    """Download an attachment from a specific email."""
    client = _get_mail_client()
    if not client:
        return

    if not output:
        output = filename

    with console.status(f"Downloading attachment '{filename}' from email {mail_id}..."):
        try:
            success = client.download_attachment(mail_id, filename, output)
        except Exception as e:
            console.print(f"[red]Error downloading attachment: {e}[/red]")
            return

    if success:
        console.print(f"[green]Successfully downloaded attachment to [bold]{output}[/bold][/green]")
    else:
        msg = f"[red]Failed to download attachment '{filename}'. Does it exist in the email?[/red]"
        console.print(msg)


@mail_app.command("send")
def mail_send(
    to: str = typer.Option(..., prompt="To", help="Recipient email address"),
    subject: str = typer.Option(..., prompt="Subject", help="Email subject"),
    body: str = typer.Option(..., prompt="Body", help="Email body"),
    attach: Optional[List[str]] = typer.Option(
        None, "--attach", "-a", help="Path to file(s) to attach to the email"
    ),
):
    """Send an email."""
    client = _get_mail_client()
    if not client:
        return

    with console.status("[bold green]Sending email..."):
        try:
            client.send_email(to, subject, body, attachment_paths=attach)
            console.print("[green]Email sent successfully.[/green]")
        except Exception as e:
            console.print(f"[red]Failed to send email: {e}[/red]")
