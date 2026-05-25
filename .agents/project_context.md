# Project Context - put-esys-cli

## Current Goal
Develop a command-line tool to authenticate with Poznań University of Technology (PUT) systems and scrape data from them.

## Implementation Details
- **Architecture**: Modular Python CLI.
- **Key Technologies**: Python, Typer, Requests, BeautifulSoup4.
- **Authentication**: Request-based SSO (elogin.put.poznan.pl).
- **Target Systems**: eKursy (Moodle-based), and others in the future.

## Repository Status
- [x] Initialized setup.
- [x] Modular CLI structure.
- [x] Robust request-based SSO authentication.
- [x] eKursy scraper (course list & content).
- [x] Integrated credential management and lazy authentication.
- [x] General `save` command for system research.
- [x] Mail client (IMAP/SMTP) for student email.

## Development Workflow
1. **Research**: Use `put-esys save [URL]` to capture HTML from any PUT system.
2. **Analysis**: Identify selectors and data structure in the captured HTML.
3. **Implementation**: Extend `scraper.py`, `mail.py` and `cli.py` with new system support.

## Critical Requirements
- Secure credential storage (`~/.put-esys/config.json`).
- Efficient session reuse via local storage.
- Robust recursive handling of SSO redirects.
