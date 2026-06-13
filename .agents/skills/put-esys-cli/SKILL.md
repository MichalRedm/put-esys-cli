---
name: put-esys-cli
description: CLI tool for Poznań University of Technology (PUT) electronic systems
---

# PUT Electronic Systems CLI Skill

This skill provides instructions and examples for using the `put-esys` CLI tool to interact with PUT systems like eKursy.

## Prerequisites
- Python 3.9+
- Virtual environment: `.venv` (recommended)
- Installed dependencies: `pip install -e .`
- Configured credentials: `put-esys config set`

## Commands

### Configuration
- `put-esys config set`: Interactive prompt to save PUT email and password.
- `put-esys config show`: Display current configuration (username only).
- `put-esys config delete [-y/--yes]`: Remove stored credentials.

### Authentication
- `put-esys login`: Manually trigger authentication and refresh the session.

### eKursy
- `put-esys course list [--json]`: List enrolled courses from eKursy.
- `put-esys course show <ID_OR_URL_OR_NAME> [--json]`: Display the content (sections and activities) of a specific course. Supports course title substring resolution.
- `put-esys course search <QUERY> [--json]`: Search enrolled courses by name substring or ID.
- `put-esys assignment show <ID_OR_URL> [--json]`: Show content and status of a specific assignment.
- `put-esys assignment upload <ID_OR_URL> <FILE_PATH> [--name NEW_NAME]`: Upload a file to an assignment (optionally under a custom name via `--name`) and save the submission changes.
- `put-esys assignment submit <ID_OR_URL> [-y/--yes]`: Finalize and submit the assignment submission. WARNING: This action is irreversible!
- `put-esys assignment edit <ID_OR_URL> [--text TEXT] [--file FILE_PATH] [--attach ATTACH_PATH] [--remove FILENAME] [--rename OLD_NAME] [--new-name NEW_NAME]`: Edit an assignment submission (modify online text, attach new files, remove or rename files).
- `put-esys assignment delete <ID_OR_URL> [-y/--yes]`: Delete/remove the assignment submission draft.
- `put-esys quiz info <ID_OR_URL> [--json]`: Show status and attempts for a specific quiz.
- `put-esys quiz attempt <QUIZ_ID> [ATTEMPT_ID] [--json]`: View questions and answers for a specific quiz attempt.
- `put-esys quiz start <QUIZ_ID>`: Start a new quiz attempt.
- `put-esys quiz edit <QUIZ_ID> <Q_NO> [--text TEXT] [--file FILE_PATH] [--attach ATTACH_PATH] [--remove FILENAME] [--rename OLD_NAME] [--new-name NEW_NAME]`: Edit a quiz answer in an in-progress attempt.
- `put-esys quiz download <QUIZ_ID> <Q_NO> <FILENAME> [--output OUTPUT_PATH]`: Download an attached file from a specific quiz question.
- `put-esys quiz submit <QUIZ_ID> [ATTEMPT_ID] [-y/--yes]`: Submit a quiz attempt to finalize it for grading. WARNING: This action is irreversible!
- `put-esys quiz search <QUERY> --course <COURSE_ID_OR_URL_OR_NAME> [--json]`: Search for quizzes in a course by name substring.

### Mail
- `put-esys mail folders [--json]`: List all available mail folders on the server.
- `put-esys mail list [--limit N] [--search QUERY] [--folder FOLDER] [--json]`: List recent emails from a specific folder (defaults to INBOX), optionally filtered by a search query.
- `put-esys mail read <MAIL_ID> [--folder FOLDER] [--json]`: Display the body and list of attachments of a specific email.
- `put-esys mail download <MAIL_ID> <FILENAME> [--output OUTPUT_PATH] [--folder FOLDER]`: Download an attachment from a specific email.
- `put-esys mail send [--body TEXT] [--body-file FILE_PATH] [--attach FILE_PATH]`: Send an email.

### General
- `put-esys save <URL> [--output FILENAME]`: Save a web page as an HTML file.
- `put-esys download <URL> [--output FILENAME]`: Download a binary resource (PDF, ZIP, etc.) and automatically detect the filename.

---

## Best Practices for AI Agents and Scripting

> [!IMPORTANT]
> To ensure robust background execution, prevent interactive prompt hangs, and avoid formatting/parsing issues, future AI agents and scripts **MUST** follow these practices:
>
> 1. **Always use the `--json` flag** when querying lists or details. Standard table outputs are formatted with `rich` and will truncate long URLs or fields using `…` depending on terminal width, making them unreadable. The `--json` flag bypasses all formatting, terminal width restrictions, and color codes, printing raw, untruncated structured data to `stdout`.
> 2. **Always specify `-y` or `--yes`** for destructive or finalizing commands (such as `assignment submit`, `assignment delete`, `quiz submit`, or `config delete`). This bypasses interactive confirmation prompts that would otherwise cause background tasks to hang indefinitely.
> 3. **Prefer name resolution over manual IDs** when looking up courses. Instead of listing courses and parsing IDs first, you can pass a unique substring of the course title (e.g. `put-esys course show "Biologically-inspired"`) and the CLI will auto-resolve it. If multiple courses match, it returns a list of matched options on `stderr` to help you narrow down the query.

---

## Examples

### Listing courses (JSON output - ENCOURAGED)
```bash
put-esys course list --json
```

### Viewing course content by Name Resolution (ENCOURAGED)
```bash
put-esys course show "Biologically-inspired"
```

### Searching for a quiz by Name Substring (ENCOURAGED)
```bash
put-esys quiz search "Quiz 2" --course "Biologically-inspired" --json
```

### Submitting an assignment non-interactively (ENCOURAGED)
```bash
put-esys assignment submit 2863790 --yes
```

### Submitting a quiz attempt non-interactively (ENCOURAGED)
```bash
put-esys quiz submit 2129129 --yes
```

### Reading emails in JSON (ENCOURAGED)
```bash
put-esys mail list --folder INBOX --json
```

## Usage with Helper Scripts

If you haven't installed the `put-esys` command globally or want to ensure it runs within the project's virtual environment, you can use the provided helper scripts:

- **Windows (PowerShell)**:
  ```powershell
  .agents/skills/put-esys-cli/scripts/run.ps1 ekursy
  ```
- **Linux/macOS/Git Bash**:
  ```bash
  .agents/skills/put-esys-cli/scripts/run.sh ekursy
  ```

## Troubleshooting
- If commands fail with authentication errors, try running `put-esys login` to refresh the session.
- Ensure your credentials are correct by running `put-esys config show`.
- If the `put-esys` command is not found, use the helper scripts mentioned above or `python -m put_esys.main` after activating the virtual environment.
