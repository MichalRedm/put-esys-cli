import typer
from typing import Optional
from .auth import authenticate, AuthError
from .scraper import get_ekursy_courses
from dotenv import load_dotenv
import os

app = typer.Typer(help="PUT Electronic Systems CLI")

@app.command()
def login(
    username: Optional[str] = typer.Option(None, help="Your eLogin username"),
    password: Optional[str] = typer.Option(None, help="Your eLogin password", hide_input=True)
):
    """
    Authenticate with PUT eLogin and save the session.
    """
    # Load from .env if not provided
    load_dotenv()
    if not username:
        username = os.getenv("ELOGIN_USERNAME")
    if not password:
        password = os.getenv("ELOGIN_PASSWORD")
    
    if not username or not password:
        typer.echo("Error: Username and password are required.")
        raise typer.Exit(code=1)
    
    typer.echo(f"Logging in as {username}...")
    try:
        authenticate(username, password)
        typer.echo("Successfully authenticated and session saved.")
    except AuthError as e:
        typer.echo(f"Login failed: {e}")
        raise typer.Exit(code=1)

@app.command()
def ekursy():
    """
    List your courses from eKursy.
    """
    typer.echo("Fetching courses from eKursy...")
    courses, error = get_ekursy_courses()
    
    if error:
        typer.echo(f"Error: {error}")
        raise typer.Exit(code=1)
    
    if not courses:
        typer.echo("No courses found or could not parse course list.")
        return

    typer.echo(f"Found {len(courses)} courses:")
    for i, course in enumerate(courses, 1):
        typer.echo(f"{i}. {course['title']} ({course['url']})")

def main():
    app()

if __name__ == "__main__":
    main()
