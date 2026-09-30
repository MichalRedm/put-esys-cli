import json
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from put_esys.models.assignment import AssignmentInfo
from put_esys.models.course import (
    CategoryBrowseResult,
    Course,
    CourseContent,
    DiscoveredCourse,
)
from put_esys.models.mail import EmailDetails, EmailSummary
from put_esys.models.quiz import QuizAttemptDetails, QuizInfo, QuizSearchResult
from put_esys.utils.markdown import html_to_markdown

console = Console()


def display_json(data) -> None:
    """Prints raw, untruncated JSON to stdout."""
    if hasattr(data, "model_dump_json"):
        sys.stdout.write(data.model_dump_json(indent=2) + "\n")
    elif isinstance(data, list):
        serialized = [
            item.model_dump() if hasattr(item, "model_dump") else item for item in data
        ]
        sys.stdout.write(json.dumps(serialized, indent=2) + "\n")
    elif hasattr(data, "model_dump"):
        sys.stdout.write(json.dumps(data.model_dump(), indent=2) + "\n")
    else:
        sys.stdout.write(json.dumps(data, indent=2) + "\n")


def get_activity_icon(activity_type: str) -> str:
    """Get a display icon/prefix for an activity type."""
    icons = {
        "folder": "[DIR]",
        "resource": "[FILE]",
        "assign": "[ASSIGN]",
        "quiz": "[QUIZ]",
        "forum": "[FORUM]",
        "url": "[URL]",
    }
    return icons.get(activity_type, "[FILE]")


def display_courses_list(courses: list[Course]) -> None:
    """Renders the enrolled courses table."""
    table = Table(title=f"Enrolled Courses ({len(courses)})")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Course Title", style="magenta")
    table.add_column("URL", style="blue")

    for i, course in enumerate(courses, 1):
        table.add_row(str(i), course.title, course.url)

    console.print(table)


def display_course_content(content: CourseContent) -> None:
    """Renders the course structure tree."""
    tree = Tree(f"[bold white on blue] {content.title} [/bold white on blue]")

    for section in content.sections:
        section_tree = tree.add(f"[bold cyan]{section.name}[/bold cyan]")
        for activity in section.activities:
            if activity.type == "label":
                raw_content = activity.content or activity.name or ""
                label_md_text = html_to_markdown(raw_content)
                if label_md_text:
                    section_tree.add(Markdown(label_md_text))
                continue

            icon = get_activity_icon(activity.type)
            label = f"{icon} [magenta]{activity.name}[/magenta]"
            if activity.url:
                label += f" ([blue]{activity.url}[/blue])"

            activity_node = section_tree.add(label)

            # Additional description/content
            if activity.content:
                desc_md_text = html_to_markdown(activity.content)
                if desc_md_text:
                    activity_node.add(Markdown(desc_md_text))

            # Render children
            if activity.children:
                for child in activity.children:
                    child_icon = get_activity_icon(child.type)
                    child_label = f"{child_icon} [magenta]{child.name}[/magenta]"
                    if child.url:
                        child_label += f" ([blue]{child.url}[/blue])"
                    activity_node.add(child_label)

    console.print(tree)


def display_assignment(info: AssignmentInfo) -> None:
    """Renders the assignment details and submission tables."""
    console.print(f"\n[bold white on blue] {info.title} [/bold white on blue]")

    # Display description/intro if present
    if info.intro:
        intro_md = html_to_markdown(info.intro)
        console.print(Panel(Markdown(intro_md), title="Instructions", border_style="blue"))

    # Display tables (submission status, feedback, etc.)
    if not info.tables:
        console.print("[yellow]No tables or status found for this assignment.[/yellow]")
    else:
        for idx, table_rows in enumerate(info.tables, 1):
            title = (
                f"Assignment Details (Table {idx})" if len(info.tables) > 1 else "Assignment Status"
            )
            table = Table(title=title, show_header=True)
            table.add_column("Property", style="cyan", no_wrap=True)
            table.add_column("Value", style="magenta", overflow="fold")

            for row in table_rows:
                val_text = row.value
                if row.files:
                    files_str = "\n".join([f"• {f.name} ({f.url})" for f in row.files])
                    val_text += f"\n\n[bold yellow]Submitted Files:[/bold yellow]\n{files_str}"

                table.add_row(row.key, val_text)

            console.print(table)


def display_quiz_info(info: QuizInfo, quiz_id: str) -> None:
    """Renders the quiz summary information and attempts."""
    console.print(f"\n[bold white on blue] {info.title} [/bold white on blue]")

    if info.intro:
        intro_md = html_to_markdown(info.intro, strip_images=False, format_links=False)
        console.print(Panel(Markdown(intro_md), title="Description", border_style="blue"))

    if info.info:
        info_text = "\n".join([f"• {p}" for p in info.info])
        console.print(Panel(info_text, title="Quiz Information", border_style="cyan"))
    else:
        console.print(f"[bold]Grading Method:[/bold] {info.grading_method}\n")

    if not info.attempts:
        console.print("[yellow]No attempts found for this quiz.[/yellow]")
    else:
        table = Table(title="Your Attempts")
        table.add_column("Attempt", style="cyan")
        table.add_column("ID", style="yellow")
        table.add_column("Status", style="magenta")
        table.add_column("Started", style="blue")
        table.add_column("Grade", style="green")

        for att in info.attempts:
            table.add_row(
                att.number or "1",
                att.id or "N/A",
                att.status or "Unknown",
                att.started or "Unknown",
                att.grade or "N/A",
            )
        console.print(table)

    if info.buttons:
        console.print("\n[bold]Available Actions:[/bold]")
        for btn in info.buttons:
            label = btn.text.lower()
            is_start = "start" in label or "kontynuuj" in label or "re-attempt" in label
            style = "bold green" if is_start else "blue"
            console.print(f" - [{style}]{btn.text}[/{style}]: [blue]{btn.url}[/blue]")

        if any("start" in b.text.lower() for b in info.buttons):
            console.print(
                f"\n[yellow]Tip: Run [bold]put-esys quiz start {quiz_id}[/bold] "
                "to start a new attempt.[/yellow]"
            )
        elif any(
            "kontynuuj" in b.text.lower() or "continue" in b.text.lower() for b in info.buttons
        ):
            console.print(
                f"\n[yellow]Tip: Run [bold]put-esys quiz attempt {quiz_id}[/bold] "
                "to continue your attempt.[/yellow]"
            )


def display_quiz_attempt(info: QuizAttemptDetails) -> None:
    """Renders details of a quiz attempt including all questions and answers."""
    for q in info.questions:
        q_header = f"\n[bold cyan]Question {q.number}[/bold cyan] ({q.type}, {q.state})"
        console.print(q_header)

        q_md_text = html_to_markdown(q.text)
        a_md_text = html_to_markdown(q.answer)

        console.print(Panel(Markdown(q_md_text), title="Question Text", border_style="blue"))
        console.print(Panel(Markdown(a_md_text), title="Your Answer", border_style="green"))

        if q.attachments:
            att_list = "\n".join([f" - [{a.name}] ({a.url})" for a in q.attachments])
            console.print(Panel(Markdown(att_list), title="Submitted Files", border_style="yellow"))
        elif q.allows_attachments:
            console.print("[italic yellow]No files submitted for this question.[/italic yellow]")

        if q.comment:
            c_md_text = html_to_markdown(q.comment)
            console.print(Panel(Markdown(c_md_text), title="Teacher's Comment", border_style="red"))


def display_emails_list(emails: list[EmailSummary], folder: str = "INBOX") -> None:
    """Renders the list of email messages."""
    title = f"Recent Emails ({folder})"
    table = Table(title=title)
    table.add_column("ID", style="cyan")
    if "sent" in folder.lower():
        table.add_column("To", style="magenta")
    else:
        table.add_column("From", style="magenta")
    table.add_column("Subject", style="green")
    table.add_column("Date", style="blue")

    for email in emails:
        recipient_or_sender = email.to if ("sent" in folder.lower() and email.to) else email.from_
        table.add_row(email.id, recipient_or_sender, email.subject, email.date)

    console.print(table)


def display_email_details(email_data: EmailDetails, folder: str = "INBOX") -> None:
    """Renders the content panel of a single email."""
    subtitle = f"From: {email_data.from_}"
    if email_data.to:
        subtitle += f" | To: {email_data.to}"
    subtitle += f" | Date: {email_data.date}"

    console.print(
        Panel(
            email_data.body,
            title=f"Subject: {email_data.subject}",
            subtitle=subtitle,
        )
    )

    if email_data.attachments:
        console.print("\n[bold]Attachments:[/bold]")
        for att in email_data.attachments:
            console.print(f" - {att}")
        
        folder_option = f" --folder {folder}" if folder != "INBOX" else ""
        console.print(
            f"\n[yellow]Tip: Run [bold]put-esys mail download {email_data.id} "
            f"<filename>{folder_option}[/bold] to download an attachment.[/yellow]"
        )


def display_quiz_search_results(quizzes: list[QuizSearchResult]) -> None:
    """Renders the quiz search results table."""
    table = Table(title=f"Matched Quizzes ({len(quizzes)})")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Quiz Name", style="magenta")
    table.add_column("ID", style="yellow")
    table.add_column("URL", style="blue")

    for i, quiz in enumerate(quizzes, 1):
        table.add_row(str(i), quiz.name, quiz.id, quiz.url)

    console.print(table)


def display_categories(result: CategoryBrowseResult) -> None:
    """Renders the course category hierarchy and contained courses."""
    if result.current_category:
        cat_text = (
            f"[bold cyan]{result.current_category.name}[/bold cyan] "
            f"(ID: {result.current_category.id})"
        )
        console.print(
            Panel(
                cat_text,
                title="Current Category",
                border_style="cyan",
            )
        )


    if result.subcategories:
        table = Table(title=f"Subcategories ({len(result.subcategories)})")
        table.add_column("#", justify="right", style="cyan", no_wrap=True)
        table.add_column("Category Name", style="magenta")
        table.add_column("ID", style="yellow")
        table.add_column("Browse Command", style="blue")

        for i, cat in enumerate(result.subcategories, 1):
            cmd = f"put-esys course categories {cat.id}"
            table.add_row(str(i), cat.name, cat.id, cmd)

        console.print(table)

    if result.courses:
        table = Table(title=f"Courses in Category ({len(result.courses)})")
        table.add_column("#", justify="right", style="cyan", no_wrap=True)
        table.add_column("Course Title", style="magenta")
        table.add_column("ID", style="yellow")
        table.add_column("Key?", justify="center")
        table.add_column("Action", style="blue")

        for i, course in enumerate(result.courses, 1):
            key_badge = (
                "[bold yellow]Yes (Key)[/bold yellow]"
                if course.requires_key
                else "[green]No (Open)[/green]"
            )
            action = f"put-esys course enrol {course.id}"
            table.add_row(str(i), course.title, course.id, key_badge, action)

        console.print(table)

    if not result.subcategories and not result.courses:
        console.print("[yellow]No subcategories or courses found in this category.[/yellow]")


def display_discovered_courses(courses: list[DiscoveredCourse]) -> None:
    """Renders the global course search results table."""
    table = Table(title=f"Discovered Courses ({len(courses)})")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Course Title", style="magenta")
    table.add_column("ID", style="yellow")
    table.add_column("Category", style="cyan")
    table.add_column("Key?", justify="center")
    table.add_column("Action", style="blue")

    for i, course in enumerate(courses, 1):
        key_badge = (
            "[bold yellow]Yes (Key)[/bold yellow]"
            if course.requires_key
            else "[green]No (Open)[/green]"
        )
        cat = course.category_name or "-"
        action = f"put-esys course enrol {course.id}"
        table.add_row(str(i), course.title, course.id, cat, key_badge, action)

    console.print(table)


def display_enrolment_result(course_id: str, success: bool, message: str) -> None:
    """Renders the course enrolment result panel."""
    if success:
        console.print(
            Panel(
                f"[bold green]{message}[/bold green]\nCourse ID: {course_id}\n"
                f"Course URL: [blue]https://ekursy.put.poznan.pl/course/view.php?id={course_id}[/blue]",
                title="Course Enrolment",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]{message}[/bold red]\nCourse ID: {course_id}",
                title="Course Enrolment Failed",
                border_style="red",
            )
        )

