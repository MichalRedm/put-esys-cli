"""
CLI commands for managing eKursy Private Files (put-esys files).
"""

import json
import os
from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from put_esys.cli.helpers import catch_errors, check_authenticated
from put_esys.services.ekursy.client import EKursyClient
from put_esys.services.ekursy.private_files import PrivateFilesService

files_app = typer.Typer(help="Manage eKursy private files and folders.")
console = Console()


def _format_time(timestamp: Optional[int]) -> str:
    """Format unix timestamp to readable string."""
    if not timestamp:
        return "-"
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(timestamp)


def _output_json_or_text(
    content: str, output: Optional[str] = None, print_to_console: bool = True
):
    """Save content to file in UTF-8 or echo to stdout."""
    if output:
        dest_dir = os.path.dirname(output)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        with open(output, "w", encoding="utf-8") as f:
            f.write(content)
        if print_to_console:
            console.print(f"[green]Output saved to:[/green] {output}")
    elif print_to_console:
        typer.echo(content)


@files_app.command(name="list")
@catch_errors
def list_files(
    path: str = typer.Option("/", "-p", "--path", help="Directory path inside private files"),
    recursive: bool = typer.Option(
        False, "-r", "--recursive", help="List files recursively across all subfolders"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    output: Optional[str] = typer.Option(
        None, "-o", "--output", help="Write output directly to file (UTF-8)"
    ),
):
    """List private files and folders."""
    client = EKursyClient()
    check_authenticated(client)
    service = PrivateFilesService(client.session)

    result = service.list_files(path=path, recursive=recursive)

    if json_output:
        raw_json = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
        _output_json_or_text(raw_json, output=output, print_to_console=not bool(output))
        return

    title_text = (
        f"Private Files in {result.path} "
        f"({result.file_count} files, {result.folder_count} folders)"
    )
    table = Table(title=title_text)
    table.add_column("Type", style="cyan", width=8)
    table.add_column("Path", style="magenta")
    table.add_column("Name", style="bold")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Modified", style="dim")

    for item in result.items:
        icon_type = "📁 dir" if item.type == "folder" else f"📄 {item.type}"
        table.add_row(
            icon_type,
            item.filepath,
            item.filename,
            item.filesize if item.type != "folder" else "-",
            _format_time(item.datemodified),
        )

    if output:
        with open(output, "w", encoding="utf-8") as f:
            for item in result.items:
                f.write(f"{item.type:<8} {item.filepath:<20} {item.filename:<30} {item.filesize}\n")
        console.print(f"[green]Listing written to:[/green] {output}")
    else:
        console.print(table)


@files_app.command()
@catch_errors
def download(
    remote_file: str = typer.Argument(..., help="Remote file name or path (e.g. 'notes.pdf')"),
    path: str = typer.Option("/", "-p", "--path", help="Remote parent directory path"),
    output: Optional[str] = typer.Option(
        None, "-o", "--output", help="Local destination file path"
    ),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip overwrite confirmation"),
):
    """Download a file from private files to local storage."""
    client = EKursyClient()
    check_authenticated(client)
    service = PrivateFilesService(client.session)

    target_local = output if output else os.path.basename(remote_file)
    if os.path.exists(target_local) and not yes:
        if not typer.confirm(f"Local file '{target_local}' already exists. Overwrite?"):
            console.print("[yellow]Download aborted.[/yellow]")
            return

    console.print(f"Downloading [cyan]{remote_file}[/cyan] from [magenta]{path}[/magenta]...")
    saved_path = service.download_file(remote_file, path=path, output_path=target_local)
    console.print(f"[green]Successfully downloaded to:[/green] [bold]{saved_path}[/bold]")


@files_app.command()
@catch_errors
def upload(
    file_path: str = typer.Argument(..., help="Local file path to upload"),
    path: str = typer.Option("/", "-p", "--path", help="Target directory inside private files"),
    name: Optional[str] = typer.Option(
        None, "-n", "--name", help="Custom remote filename to save as"
    ),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Write output to file"),
):
    """Upload a file to private files storage."""
    client = EKursyClient()
    check_authenticated(client)
    if not os.path.exists(file_path):
        console.print(f"[red]Error: Local file not found: {file_path}[/red]")
        raise typer.Exit(code=1)

    dest_name = name if name else os.path.basename(file_path)
    if not yes:
        if not typer.confirm(f"Upload '{file_path}' as '{dest_name}' into '{path}'?"):
            console.print("[yellow]Upload aborted.[/yellow]")
            return

    client = EKursyClient()
    service = PrivateFilesService(client.session)

    console.print(f"Uploading [cyan]{file_path}[/cyan] to [magenta]{path}{dest_name}[/magenta]...")
    uploaded = service.upload_file(file_path, remote_path=path, new_name=dest_name)

    if json_output:
        raw_json = json.dumps(uploaded.model_dump(), indent=2, ensure_ascii=False)
        _output_json_or_text(raw_json, output=output, print_to_console=not bool(output))
        return

    msg = (
        f"[green]Successfully uploaded:[/green] "
        f"[bold]{uploaded.filename}[/bold] ({uploaded.filesize})"
    )
    console.print(msg)


@files_app.command()
@catch_errors
def mkdir(
    dir_name: str = typer.Argument(..., help="Name of the new folder to create"),
    path: str = typer.Option("/", "-p", "--path", help="Parent directory path"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Write output to file"),
):
    """Create a new folder in private files storage."""
    client = EKursyClient()
    check_authenticated(client)
    if not yes:
        if not typer.confirm(f"Create folder '{dir_name}' in '{path}'?"):
            console.print("[yellow]Action aborted.[/yellow]")
            return

    client = EKursyClient()
    service = PrivateFilesService(client.session)

    service.create_folder(dir_name, parent_path=path)

    res = {"status": "success", "action": "mkdir", "name": dir_name, "path": path}
    if json_output:
        raw_json = json.dumps(res, indent=2, ensure_ascii=False)
        _output_json_or_text(raw_json, output=output, print_to_console=not bool(output))
        return

    console.print(f"[green]Folder created successfully:[/green] [bold]{dir_name}[/bold]")


@files_app.command()
@catch_errors
def rename(
    filename: str = typer.Argument(..., help="Current filename or folder name"),
    new_name: str = typer.Argument(..., help="New filename or folder name"),
    path: str = typer.Option("/", "-p", "--path", help="Directory path where the file is located"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Write output to file"),
):
    """Rename a file or folder in private files storage."""
    client = EKursyClient()
    check_authenticated(client)
    if not yes:
        if not typer.confirm(f"Rename '{filename}' to '{new_name}' in '{path}'?"):
            console.print("[yellow]Action aborted.[/yellow]")
            return

    client = EKursyClient()
    service = PrivateFilesService(client.session)

    service.rename_file(filename, new_name=new_name, path=path)

    res = {
        "status": "success",
        "action": "rename",
        "old_name": filename,
        "new_name": new_name,
        "path": path,
    }
    if json_output:
        raw_json = json.dumps(res, indent=2, ensure_ascii=False)
        _output_json_or_text(raw_json, output=output, print_to_console=not bool(output))
        return

    console.print(
        f"[green]Renamed:[/green] [cyan]{filename}[/cyan] -> [bold green]{new_name}[/bold green]"
    )


@files_app.command()
@catch_errors
def move(
    filename: str = typer.Argument(..., help="File or folder name to move"),
    target_path: str = typer.Argument(
        ..., help="Target directory path to move into (e.g. '/archive/')"
    ),
    path: str = typer.Option(
        "/", "-p", "--path", help="Current directory path where file is located"
    ),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Write output to file"),
):
    """Move a file or folder to a different directory in private storage."""
    client = EKursyClient()
    check_authenticated(client)
    if not yes:
        if not typer.confirm(f"Move '{filename}' from '{path}' to '{target_path}'?"):
            console.print("[yellow]Action aborted.[/yellow]")
            return

    client = EKursyClient()
    service = PrivateFilesService(client.session)

    service.move_file(filename, target_path=target_path, source_path=path)

    res = {
        "status": "success",
        "action": "move",
        "filename": filename,
        "source_path": path,
        "target_path": target_path,
    }
    if json_output:
        raw_json = json.dumps(res, indent=2, ensure_ascii=False)
        _output_json_or_text(raw_json, output=output, print_to_console=not bool(output))
        return

    msg = (
        f"[green]Moved:[/green] [cyan]{filename}[/cyan] from "
        f"[magenta]{path}[/magenta] to [magenta]{target_path}[/magenta]"
    )
    console.print(msg)


@files_app.command()
@catch_errors
def delete(
    filename: str = typer.Argument(..., help="File or folder name to delete"),
    path: str = typer.Option("/", "-p", "--path", help="Directory path where file is located"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompt"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Write output to file"),
):
    """Delete a file or folder from private files storage."""
    client = EKursyClient()
    check_authenticated(client)
    if not yes:
        if not typer.confirm(
            f"Are you sure you want to permanently delete '{filename}' from '{path}'?"
        ):
            console.print("[yellow]Deletion aborted.[/yellow]")
            return

    client = EKursyClient()
    service = PrivateFilesService(client.session)

    service.delete_file(filename, path=path)

    res = {"status": "success", "action": "delete", "filename": filename, "path": path}
    if json_output:
        raw_json = json.dumps(res, indent=2, ensure_ascii=False)
        _output_json_or_text(raw_json, output=output, print_to_console=not bool(output))
        return

    console.print(f"[green]Deleted successfully:[/green] [bold red]{filename}[/bold red]")
