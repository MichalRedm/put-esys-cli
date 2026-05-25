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
- `put-esys config delete`: Remove stored credentials.

### Authentication
- `put-esys login`: Manually trigger authentication and refresh the session.

### eKursy
- `put-esys course <ID_OR_URL>`: Display the content (sections and activities) of a specific course.
- `put-esys quiz info <ID_OR_URL>`: Show status and attempts for a specific quiz.
- `put-esys quiz attempt <QUIZ_ID> [ATTEMPT_ID]`: View questions and answers for a specific quiz attempt.
- `put-esys quiz start <QUIZ_ID>`: Start a new quiz attempt.
- `put-esys quiz edit <QUIZ_ID> <Q_NO> [--text TEXT] [--file FILE_PATH] [--attach ATTACH_PATH] [--remove FILENAME] [--rename OLD_NAME] [--new-name NEW_NAME]`: Edit a quiz answer in an in-progress attempt by providing text, reading from a file, attaching a file (optionally under a custom name via `--new-name`), removing a file, or renaming a file.
- `put-esys quiz download <QUIZ_ID> <Q_NO> <FILENAME> [--output OUTPUT_PATH]`: Download an attached file from a specific quiz question.
- `put-esys quiz submit <QUIZ_ID> [ATTEMPT_ID] [--force]`: Submit a quiz attempt to finalize it for grading. WARNING: This action is irreversible!

### Mail
- `put-esys mail list [--limit N]`: List recent emails from your INBOX.
- `put-esys mail read <MAIL_ID>`: Display the body of a specific email.
- `put-esys mail send`: Send an email (interactive prompts for recipient, subject, and body).

### General
- `put-esys save <URL> [--output FILENAME]`: Save a web page as an HTML file.
- `put-esys download <URL> [--output FILENAME]`: Download a binary resource (PDF, ZIP, etc.) and automatically detect the filename.

## Examples

### Listing courses
```bash
put-esys course list
```

### Viewing course content
```bash
put-esys course show 12345
```

### Checking quiz status
```bash
put-esys quiz info 2129129
```

### Viewing a quiz attempt
```bash
put-esys quiz attempt 2089015 1178826
```

### Starting a quiz attempt
```bash
put-esys quiz start 2129129
```

### Editing a quiz answer (Markdown to HTML)
```bash
put-esys quiz edit 2129129 2 --file my_answer.md
```

### Attaching a file to a quiz answer
```bash
put-esys quiz edit 2129129 2 --attach my_document.pdf
```

### Attaching a file with a custom filename setting
```bash
put-esys quiz edit 2129129 2 --attach my_document.pdf --new-name custom_filename.pdf
```

### Renaming an uploaded attachment
```bash
put-esys quiz edit 2129129 2 --rename old_filename.png --new-name new_filename.png
```

### Removing an attachment from a quiz answer
```bash
put-esys quiz edit 2129129 2 --remove redundant_file.png
```

### Downloading an uploaded file from a quiz question
```bash
put-esys quiz download 2129129 2 my_document.pdf -o downloaded_document.pdf
```

### Submitting a quiz attempt (WARNING: IRREVERSIBLE!)
```bash
put-esys quiz submit 2129129
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
