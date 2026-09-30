# Project Context - put-esys-cli

## Master Entry Point
See [AGENTS.md](../AGENTS.md) at the repository root for immediate orientation, rule routing, and command references.

## Current Goal
Maintain and extend `put-esys-cli` as a robust, agent-friendly command-line tool and automation suite for authenticating with Poznań University of Technology (PUT) systems, scraping course content, managing assignments, attempting quizzes, and interacting with student mail.

## Implementation Details
- **Architecture**: Modular layered Python architecture separating CLI commands (`put_esys/cli`), domain services (`put_esys/services`), Pydantic models (`put_esys/models`), and utilities (`put_esys/utils`).
- **Key Technologies**: Python >= 3.9, Typer, Requests, BeautifulSoup4, Pydantic v2, Rich, AppDirs, Markdownify, Ruff.
- **Authentication**: Session-persisted SSO against `elogin.put.poznan.pl` with automatic SAML/POST redirect-chain traversal and `MoodleSession` cookie caching.
- **Target Systems**:
  - **eKursy**: Moodle-based LMS (`ekursy.put.poznan.pl`) for course structure, assignment file submissions (`draftfiles.php`), and quiz attempts with offline Markdown dump/sync.
  - **Student Mail**: IMAP/SMTP (`poczta.put.poznan.pl` / `mail.put.poznan.pl`).
  - **PUT eLogin**: Central authentication service (`elogin.put.poznan.pl`).

## Repository Status
- [x] Modular CLI structure with Typer and Rich console formatting.
- [x] Robust request-based SSO authentication with session cookie reuse.
- [x] Credential storage in user config directory (`appdirs`).
- [x] eKursy course scraping (list courses, show course structure, search).
- [x] eKursy assignment management (view, upload files, edit, delete, non-interactive submit).
- [x] eKursy quiz engine (view status, dump to Markdown, offline edit, sync answers back, submit).
- [x] Student mail client (IMAP folder listing, search, read, download attachments, SMTP send).
- [x] General HTML capture (`put-esys save`) and binary resource download (`put-esys download`).
- [x] Modernized `.agents/` repository infrastructure and root `AGENTS.md`.
- [ ] Unit & integration test suite with mocked HTTP/SSO responses.
- [ ] Support for additional PUT systems (e.g. eDeanery/eDziekanat).

## Critical Requirements & Developer Guidelines
1. **Local Setup & Dependencies**:
   Install in editable mode with development dependencies:
   ```bash
   pip install -e .[dev]
   ```
2. **Quality & Verification**:
   Always run Ruff before committing or pushing:
   ```bash
   ruff check .
   ```
3. **Windows Encoding & Redirection**:
   On Windows PowerShell, standard `>` redirection produces UTF-16LE, which breaks Python UTF-8 decoders. Always use the `-o` / `--output` flag provided by CLI commands for file output.
4. **Agent-Friendly Non-Interactive Automation**:
   Always implement and pass `-y` / `--yes` for destructive/finalizing commands (`submit`, `delete`), and `--json` for unformatted structured data.
5. **Context Self-Maintenance**:
   Update `.agents/` docs, schemas, and rule files whenever commands, models, or dependencies change, following [`.agents/skills/agent-maintenance/SKILL.md`](skills/agent-maintenance/SKILL.md).
