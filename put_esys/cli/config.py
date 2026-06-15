import typer
from rich.console import Console
from rich.table import Table

from put_esys.services.config import clear_credentials, load_credentials, save_credentials

config_app = typer.Typer(help="Manage your PUT credentials")
console = Console()


@config_app.command("set")
def config_set(
    username: str = typer.Argument(
        None,
        help=(
            "PUT email (e.g. jan.kowalski@student.put.poznan.pl). "
            "If not provided, you will be prompted."
        ),
        show_default=False,
    ),
    password: str = typer.Argument(
        None,
        help="PUT password. If not provided, you will be prompted.",
        show_default=False,
    ),
):
    """Set your PUT credentials.

    If username or password are not provided, you will be prompted interactively.
    """
    if not username:
        username = typer.prompt("PUT email (e.g. jan.kowalski@student.put.poznan.pl)")
    if not password:
        password = typer.prompt("PUT password", hide_input=True)
    save_credentials(username, password)
    console.print("[green]Credentials saved successfully.[/green]")


@config_app.command("show")
def config_show():
    """Show current configuration (password masked)."""
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg)
        return

    table = Table(title="PUT CLI Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Username", creds["username"])
    table.add_row("Password", "*" * 8)

    console.print(table)


@config_app.command("delete")
def config_delete(
    yes: bool = typer.Option(
        False, "--yes", "-y", "--force", "-f", help="Delete without asking for confirmation."
    )
):
    """Remove stored credentials."""
    if yes or typer.confirm("Are you sure you want to delete your stored credentials?"):
        clear_credentials()
        console.print("[red]Credentials deleted.[/red]")
