import io
import os
import re
import sys
from typing import Optional

import requests
import typer
from markdownify import markdownify
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from .auth import authenticate, ensure_authenticated_session
from .config import clear_credentials, load_credentials, save_credentials
from .mail import MailClient
from .scraper import (
    get_course_content,
    get_ekursy_courses,
    get_quiz_attempt,
    get_quiz_info,
    save_quiz_answer,
    start_quiz_attempt,
    submit_quiz_attempt,
)

# Fix UnicodeEncodeError on Windows by forcing UTF-8 if necessary
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        # Fallback for older python versions or specific environments
        pass

app = typer.Typer(help="PUT Electronic Systems CLI")
config_app = typer.Typer(help="Manage your PUT credentials")
course_app = typer.Typer(help="Manage courses and content")
quiz_app = typer.Typer(help="Manage quizzes and attempts")
mail_app = typer.Typer(help="Manage your PUT email")

app.add_typer(config_app, name="config")
app.add_typer(course_app, name="course")
app.add_typer(quiz_app, name="quiz")
app.add_typer(mail_app, name="mail")

console = Console()

@config_app.command("set")
def config_set():
    """Set your PUT credentials."""
    username = typer.prompt("PUT email (e.g. jan.kowalski@student.put.poznan.pl)")
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
    
    table.add_row("Username", creds['username'])
    table.add_row("Password", "*" * 8)
    
    console.print(table)

@config_app.command("delete")
def config_delete():
    """Remove stored credentials."""
    if typer.confirm("Are you sure you want to delete your stored credentials?"):
        clear_credentials()
        console.print("[red]Credentials deleted.[/red]")

@app.command()
def login(
    username: Optional[str] = typer.Option(None, help="PUT username"),
    password: Optional[str] = typer.Option(None, help="PUT password", hide_input=True),
):
    """Authenticate with PUT eLogin systems."""
    if not username or not password:
        creds = load_credentials()
        if creds:
            username = username or creds['username']
            password = password or creds['password']
        else:
            msg = (
                "[yellow]No credentials provided and none stored. "
                "Run 'put-esys config set' or provide options.[/yellow]"
            )
            console.print(msg)
            return

    console.print(f"Logging in as [bold]{username}[/bold]...")
    try:
        authenticate(username, password)
        console.print("[green]Successfully authenticated and session saved.[/green]")
    except Exception as e:
        console.print(f"[red]Login failed: {e}[/red]")
        raise typer.Exit(code=1)

@course_app.command("list")
def course_list():
    """List enrolled courses from eKursy."""
    console.print("Fetching courses from eKursy...")
    
    # Use lazy authentication
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        console.print("Please run [bold]put-esys config set[/bold] first to save your credentials.")
        raise typer.Exit(code=1)
        
    courses, error = get_ekursy_courses(session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    if not courses:
        console.print("[yellow]No courses found or could not parse course list.[/yellow]")
        return

    table = Table(title=f"Enrolled Courses ({len(courses)})")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Course Title", style="magenta")
    table.add_column("URL", style="blue")

    for i, course in enumerate(courses, 1):
        table.add_row(str(i), course['title'], course['url'])

    console.print(table)

@course_app.command("show")
def course_show(id_or_url: str = typer.Argument(..., help="Course ID or eKursy URL")):
    """Show content of a specific course."""
    # Extract ID if URL is provided
    course_id = id_or_url
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            course_id = match.group(1)
        else:
            console.print("[red]Could not parse course ID from URL.[/red]")
            raise typer.Exit(code=1)

    console.print(f"Fetching content for course [bold]{course_id}[/bold]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        console.print("Please run [bold]put-esys config set[/bold] first.")
        raise typer.Exit(code=1)
        
    content, error = get_course_content(course_id, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    tree = Tree(f"[bold white on blue] {content['title']} [/bold white on blue]")
    
    for section in content['sections']:
        section_tree = tree.add(f"[bold cyan]{section['name']}[/bold cyan]")
        for activity in section['activities']:
            icon = "[FILE]"
            if activity['type'] == 'folder':
                icon = "[DIR]"
            elif activity['type'] == 'assign':
                icon = "[ASSIGN]"
            elif activity['type'] == 'quiz':
                icon = "[QUIZ]"
            elif activity['type'] == 'forum':
                icon = "[FORUM]"
            elif activity['type'] == 'url':
                icon = "[URL]"
            
            section_tree.add(
                f"{icon} [magenta]{activity['name']}[/magenta] ([blue]{activity['url']}[/blue])"
            )
            
    console.print(tree)

@app.command()
def save(
    url: str = typer.Argument(..., help="URL to save as HTML"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
):
    """Save a web page as an HTML file."""
    import re
    
    if not output:
        # Create a simple filename from the URL
        slug = re.sub(r'[^a-zA-Z0-9]', '_', url.replace('https://', '').replace('http://', ''))
        output = f"{slug[:50]}.html"

    console.print(f"Fetching [blue]{url}[/blue]...")
    
    session = ensure_authenticated_session()
    if not session:
        msg = "[yellow]Warning: Not authenticated. Attempting to fetch without session.[/yellow]"
        console.print(msg)
        session = requests.Session()
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        session.headers.update({"User-Agent": ua})
    
    try:
        resp = session.get(url, stream=True)
        resp.raise_for_status()
        
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            console.print(f"[yellow]Warning: Content-Type is {content_type}.[/yellow]")
            console.print("[yellow]For binary files, use 'put-esys download' instead.[/yellow]")
            
        # Check if we were redirected to a login page
        if "elogin.put.poznan.pl" in resp.url and "elogin.put.poznan.pl" not in url:
             console.print("[yellow]Detected redirection to eLogin.[/yellow]")
        
        with open(output, "w", encoding="utf-8") as f:
            f.write(resp.text)
        
        console.print(f"[green]Successfully saved to [bold]{output}[/bold][/green]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@app.command()
def download(
    url: str = typer.Argument(..., help="URL of the resource to download"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output filename"),
):
    """Download a resource (file, document, etc.) from eKursy or other PUT systems."""
    console.print(f"Downloading [blue]{url}[/blue]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    try:
        resp = session.get(url, stream=True)
        resp.raise_for_status()
        
        # Try to get filename from Content-Disposition
        cd = resp.headers.get('Content-Disposition')
        if not output and cd:
            match = re.findall('filename=(.+)', cd)
            if match:
                output = match[0].strip(' "')
        
        # Fallback: get filename from URL
        if not output:
            output = os.path.basename(url.split('?')[0])
            if not output or output == 'pluginfile.php':
                 # If it's a generic Moodle file URL, try to find the filename in the path
                 parts = url.split('/')
                 if len(parts) > 1:
                      output = parts[-1].split('?')[0]
            
            if not output:
                 output = "downloaded_file"

        with open(output, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                
        console.print(f"[green]Successfully downloaded [bold]{output}[/bold][/green]")
        console.print(f"Size: [bold]{resp.headers.get('Content-Length', 'unknown')}[/bold] bytes")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1)

@quiz_app.command("info")
def quiz_info(id_or_url: str = typer.Argument(..., help="Quiz ID or eKursy URL")):
    """Show status and attempts for a specific quiz."""
    # Extract ID if URL is provided
    quiz_id = id_or_url
    if id_or_url.startswith("http"):
        match = re.search(r"id=(\d+)", id_or_url)
        if match:
            quiz_id = match.group(1)
        else:
            console.print("[red]Could not parse quiz ID from URL.[/red]")
            raise typer.Exit(code=1)

    console.print(f"Fetching info for quiz [bold]{quiz_id}[/bold]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    info, error = get_quiz_info(quiz_id, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold white on blue] {info['title']} [/bold white on blue]")
    
    # Display intro/description if present
    if info['intro']:
        from markdownify import markdownify
        from rich.markdown import Markdown
        intro_md = markdownify(info['intro'])
        console.print(Panel(Markdown(intro_md), title="Description", border_style="blue"))

    # Display quiz info (Time limit, Grading method, etc.)
    if info['info']:
        info_text = "\n".join([f"• {p}" for p in info['info']])
        console.print(Panel(info_text, title="Quiz Information", border_style="cyan"))
    else:
        console.print(f"[bold]Grading Method:[/bold] {info['grading_method']}\n")

    if not info['attempts']:
        console.print("[yellow]No attempts found for this quiz.[/yellow]")
    else:
        table = Table(title="Your Attempts")
        table.add_column("Attempt", style="cyan")
        table.add_column("ID", style="yellow")
        table.add_column("Status", style="magenta")
        table.add_column("Started", style="blue")
        table.add_column("Grade", style="green")

        for att in info['attempts']:
            table.add_row(
                att.get('number', '1'),
                att.get('id', 'N/A'),
                att.get('status', 'Unknown'),
                att.get('started', 'Unknown'),
                att.get('grade', 'N/A')
            )
        console.print(table)

    if info['buttons']:
        console.print("\n[bold]Available Actions:[/bold]")
        for btn in info['buttons']:
            label = btn['text'].lower()
            is_start = "start" in label or "kontynuuj" in label or "re-attempt" in label
            style = "bold green" if is_start else "blue"
            console.print(f" - [{style}]{btn['text']}[/{style}]: [blue]{btn['url']}[/blue]")
        
        # Suggest the 'start' command if a start button is present
        if any("start" in b['text'].lower() for b in info['buttons']):
             tip = (
                 f"\n[yellow]Tip: Run [bold]put-esys quiz start {quiz_id}[/bold] "
                 "to start a new attempt.[/yellow]"
             )
             console.print(tip)
        elif any(
            "kontynuuj" in b['text'].lower() or "continue" in b['text'].lower() 
            for b in info['buttons']
        ):
             tip = (
                 f"\n[yellow]Tip: Run [bold]put-esys quiz attempt {quiz_id}[/bold] "
                 "to continue your attempt.[/yellow]"
             )
             console.print(tip)

@quiz_app.command("attempt")
def quiz_attempt(quiz_id: int, attempt_id: int = typer.Argument(None)):
    """View a particular quiz attempt (questions and answers)."""
    if attempt_id:
        msg = f"Fetching attempt [bold]{attempt_id}[/bold] for quiz [bold]{quiz_id}[/bold]..."
        console.print(msg)
    else:
        console.print(f"Fetching current attempt for quiz [bold]{quiz_id}[/bold]...")
    
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    info, error = get_quiz_attempt(quiz_id, attempt_id, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        console.print(
            f"[yellow]Try running [bold]put-esys quiz start {quiz_id}[/bold] "
            "to start a new attempt, "
            f"or [bold]put-esys quiz info {quiz_id}[/bold] to see details.[/yellow]"
        )
        raise typer.Exit(code=1)

    for q in info['questions']:
        q_header = f"\n[bold cyan]Question {q['number']}[/bold cyan] ({q['type']}, {q['state']})"
        console.print(q_header)
        
        # Convert HTML to markdown
        q_md_raw = markdownify(q['text'])
        a_md_raw = markdownify(q['answer'])
        
        # Post-process to show URLs explicitly: [Text](URL) -> [Text] (URL)
        # Using a regex that handles basic markdown links
        link_pattern = r'\[([^\]]+)\]\((https?://[^\)]+)\)'
        q_md_text = re.sub(link_pattern, r'[\1] (\2)', q_md_raw)
        a_md_text = re.sub(link_pattern, r'[\1] (\2)', a_md_raw)

        q_md = Markdown(q_md_text)
        a_md = Markdown(a_md_text)
        
        console.print(Panel(q_md, title="Question Text", border_style="blue"))
        console.print(Panel(a_md, title="Your Answer", border_style="green"))
        
        # Display attachments if any
        if q['attachments']:
             att_list = "\n".join([f" - [{a['name']}] ({a['url']})" for a in q['attachments']])
             att_panel = Panel(Markdown(att_list), title="Submitted Files", border_style="yellow")
             console.print(att_panel)
        elif q['allows_attachments']:
             console.print("[italic yellow]No files submitted for this question.[/italic yellow]")

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
    )
):
    """Edit an answer for a specific question in an in-progress attempt."""
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
    
    if file:
        with open(file, 'r', encoding='utf-8') as f:
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
        
    # First, get the attempt ID
    info, error = get_quiz_attempt(quiz_id, None, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(1)
        
    attempt_id = info['attempt_id']
    
    with console.status(f"[bold green]Saving answer for Question {q_no}..."):
        success = save_quiz_answer(
            session, quiz_id, attempt_id, q_no, text, attach, remove, new_name, rename
        )
        
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
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
    
    console.print(f"Starting new attempt for quiz [bold]{quiz_id}[/bold]...")
    
    with console.status("[bold green]Communicating with eKursy..."):
        attempt_id, error = start_quiz_attempt(quiz_id, session)
        
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
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output filename/path"
    )
):
    """Download an attached file from a quiz question."""
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)
        
    # Get current attempt
    info, error = get_quiz_attempt(quiz_id, None, session)
    if error:
        console.print(f"[red]Error: {error}[/red]")
        raise typer.Exit(1)
        
    # Find target question and file
    target_q = None
    for q in info['questions']:
        if q['number'] == str(q_no):
            target_q = q
            break
            
    if not target_q:
        console.print(f"[red]Error: Question {q_no} not found in attempt.[/red]")
        raise typer.Exit(1)
        
    target_att = None
    for att in target_q['attachments']:
        if att['name'] == filename:
            target_att = att
            break
            
    if not target_att:
        msg = f"[red]Error: Attachment '{filename}' not found on Question {q_no}.[/red]"
        console.print(msg)
        if target_q['attachments']:
            console.print("Available files:")
            for att in target_q['attachments']:
                console.print(f" - {att['name']}")
        raise typer.Exit(1)
        
    if not output:
        output = filename
        
    console.print(f"Downloading [blue]{filename}[/blue] from Question {q_no}...")
    try:
        resp = session.get(target_att['url'], stream=True)
        resp.raise_for_status()
        
        with open(output, 'wb') as f:
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
    session = ensure_authenticated_session()
    if not session:
        console.print("[red]Not authenticated.[/red]")
        raise typer.Exit(code=1)

    # 1. Resolve attempt_id if not provided
    if not attempt_id:
        with console.status("[bold green]Checking quiz attempts..."):
            info, error = get_quiz_info(quiz_id, session)
            
        if error:
            console.print(f"[red]Error: {error}[/red]")
            raise typer.Exit(1)
            
        # Priority 1: In progress attempt
        in_progress = [a for a in info['attempts'] if a.get('status') in ['In progress', 'W toku']]
        if in_progress and in_progress[0].get('id'):
            attempt_id = int(in_progress[0]['id'])
        else:
            console.print("[red]No active (in progress) attempt found for this quiz.[/red]")
            raise typer.Exit(1)

    # 2. Safety confirmation prompt unless forced
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

    # 3. Submit attempt
    with console.status(f"[bold green]Submitting Attempt {attempt_id} for Quiz {quiz_id}..."):
        success, error = submit_quiz_attempt(session, quiz_id, attempt_id)
        
    if success:
        console.print(
            f"[bold green]Successfully submitted and finalized Quiz {quiz_id} "
            f"(Attempt {attempt_id})![/bold green]"
        )
        if error:  # If already submitted
            console.print(f"[yellow]{error}[/yellow]")
    else:
        console.print(f"[red]Failed to submit quiz: {error}[/red]")
        raise typer.Exit(1)


@mail_app.command("list")
def mail_list(
    limit: int = typer.Option(10, help="Number of emails to list"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search query (e.g., sender or subject)")
):
    """List recent emails from your INBOX, optionally filtered by a search query."""
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg)
        return

    client = MailClient(creds["username"], creds["password"])
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

    table = Table(title="Recent Emails")
    table.add_column("ID", style="cyan")
    table.add_column("From", style="magenta")
    table.add_column("Subject", style="green")
    table.add_column("Date", style="blue")

    for email in emails:
        table.add_row(email["id"], email["from"], email["subject"], email["date"])

    console.print(table)


@mail_app.command("read")
def mail_read(mail_id: str):
    """Read a specific email by its ID."""
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg)
        return

    client = MailClient(creds["username"], creds["password"])
    with console.status(f"[bold green]Fetching email {mail_id}..."):
        try:
            email_data = client.get_email_details(mail_id)
        except Exception as e:
            console.print(f"[red]Failed to fetch email: {e}[/red]")
            return

    if not email_data:
        console.print(f"[red]Email with ID {mail_id} not found.[/red]")
        return

    console.print(
        Panel(
            email_data["body"],
            title=f"Subject: {email_data['subject']}",
            subtitle=f"From: {email_data['from']} | Date: {email_data['date']}",
        )
    )
    
    if email_data.get("attachments"):
        console.print("\n[bold]Attachments:[/bold]")
        for att in email_data["attachments"]:
            console.print(f" - {att}")
        console.print(f"\n[yellow]Tip: Run [bold]put-esys mail download {mail_id} <filename>[/bold] to download an attachment.[/yellow]")


@mail_app.command("download")
def mail_download(
    mail_id: str = typer.Argument(..., help="ID of the email"),
    filename: str = typer.Argument(..., help="Name of the attachment to download"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output path for the downloaded attachment")
):
    """Download an attachment from a specific email."""
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg)
        return

    if not output:
        output = filename

    client = MailClient(creds["username"], creds["password"])
    with console.status(f"[bold green]Downloading attachment '{filename}' from email {mail_id}..."):
        try:
            success = client.download_attachment(mail_id, filename, output)
        except Exception as e:
            console.print(f"[red]Error downloading attachment: {e}[/red]")
            return

    if success:
        console.print(f"[green]Successfully downloaded attachment to [bold]{output}[/bold][/green]")
    else:
        console.print(f"[red]Failed to download attachment '{filename}'. Does it exist in the email?[/red]")


@mail_app.command("send")
def mail_send(
    to: str = typer.Option(..., prompt="To", help="Recipient email address"),
    subject: str = typer.Option(..., prompt="Subject", help="Email subject"),
    body: str = typer.Option(..., prompt="Body", help="Email body"),
    attach: Optional[List[str]] = typer.Option(None, "--attach", "-a", help="Path to file(s) to attach to the email")
):
    """Send an email."""
    creds = load_credentials()
    if not creds:
        msg = "[yellow]No credentials configured. Run 'put-esys config set' first.[/yellow]"
        console.print(msg)
        return

    client = MailClient(creds["username"], creds["password"])
    with console.status("[bold green]Sending email..."):
        try:
            client.send_email(to, subject, body, attachment_paths=attach)
            console.print("[green]Email sent successfully.[/green]")
        except Exception as e:
            console.print(f"[red]Failed to send email: {e}[/red]")


if __name__ == "__main__":
    app()

