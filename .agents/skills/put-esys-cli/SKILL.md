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
- `put-esys assignment show <ID_OR_URL>`: Show content and status of a specific assignment.
- `put-esys assignment upload <ID_OR_URL> <FILE_PATH> [--name NEW_NAME]`: Upload a file to an assignment (optionally under a custom name via `--name`) and save the submission changes.
- `put-esys assignment submit <ID_OR_URL> [--force]`: Finalize and submit the assignment submission. WARNING: This action is irreversible!
- `put-esys assignment edit <ID_OR_URL> [--text TEXT] [--file FILE_PATH] [--attach ATTACH_PATH] [--remove FILENAME] [--rename OLD_NAME] [--new-name NEW_NAME]`: Edit an assignment submission (modify online text, attach new files, remove or rename files).
- `put-esys assignment delete <ID_OR_URL> [--force]`: Delete/remove the assignment submission draft.
- `put-esys quiz info <ID_OR_URL>`: Show status and attempts for a specific quiz.
- `put-esys quiz attempt <QUIZ_ID> [ATTEMPT_ID]`: View questions and answers for a specific quiz attempt.
- `put-esys quiz start <QUIZ_ID>`: Start a new quiz attempt.
- `put-esys quiz edit <QUIZ_ID> <Q_NO> [--text TEXT] [--file FILE_PATH] [--attach ATTACH_PATH] [--remove FILENAME] [--rename OLD_NAME] [--new-name NEW_NAME]`: Edit a quiz answer in an in-progress attempt by providing text, reading from a file, attaching a file (optionally under a custom name via `--new-name`), removing a file, or renaming a file.
- `put-esys quiz download <QUIZ_ID> <Q_NO> <FILENAME> [--output OUTPUT_PATH]`: Download an attached file from a specific quiz question.
- `put-esys quiz submit <QUIZ_ID> [ATTEMPT_ID] [--force]`: Submit a quiz attempt to finalize it for grading. WARNING: This action is irreversible!

### Mail
- `put-esys mail list [--limit N] [--search QUERY]`: List recent emails from your INBOX, optionally filtered by a search query (e.g. subject or sender).
- `put-esys mail read <MAIL_ID>`: Display the body and list of attachments of a specific email.
- `put-esys mail download <MAIL_ID> <FILENAME> [--output OUTPUT_PATH]`: Download an attachment from a specific email.
- `put-esys mail send [--attach FILE_PATH]`: Send an email (interactive prompts for recipient, subject, and body). Can attach files using multiple `--attach` flags.

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

### Viewing assignment details
```bash
put-esys assignment show 2841810
```

### Uploading an assignment file
```bash
put-esys assignment upload 2863790 "Homework_12.pdf"
```

### Uploading an assignment file with a custom name
```bash
put-esys assignment upload 2863790 "Homework_12.pdf" --name "English_Homework_12.pdf"
```

### Submitting an assignment (WARNING: IRREVERSIBLE!)
```bash
put-esys assignment submit 2863790
```

### Editing an assignment submission (online text and files)
```bash
put-esys assignment edit 2863790 --text "This is my updated submission text."
put-esys assignment edit 2863790 --attach additional_file.zip
put-esys assignment edit 2863790 --remove old_file.pdf
```

### Deleting/removing an assignment submission
```bash
put-esys assignment delete 2863790
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

### Searching emails
```bash
put-esys mail list --search "Project Update"
```

### Downloading an email attachment
```bash
put-esys mail download 123 "report.pdf" --output downloads/report.pdf
```

### Sending an email with attachments
```bash
put-esys mail send --attach document.pdf --attach image.png
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
