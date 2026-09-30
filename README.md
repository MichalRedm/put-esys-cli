# PUT Electronic Systems CLI (put-esys)

[![CI](https://github.com/MichalRedm/put-esys-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/MichalRedm/put-esys-cli/actions/workflows/ci.yml)

A command-line interface for accessing various electronic systems of Poznań University of Technology (PUT).

Currently supports:
- **eKursy** (Moodle-based learning platform)

## Features

- **Automated Authentication**: Handles the complex PUT SSO (Single Sign-On) redirection chain.
- **Persistent Sessions**: Saves authentication cookies locally for seamless multi-session access.
- **eKursy Integration**: Scrapes and lists your enrolled courses with direct links.

## Installation

### For Users (Global Access)
The recommended way to install `put-esys` globally is using [pipx](https://pypa.github.io/pipx/), which handles virtual environments automatically:

```bash
# Install directly from GitHub
pipx install git+https://github.com/MichalRedm/put-esys-cli.git

# Or if you have the repo cloned locally
pipx install .
```

Alternatively, you can install via standard pip (not recommended for global use):
```bash
pip install .
```

### For Developers (Editable Mode)
1. Clone the repository.
2. Set up a virtual environment:
   ```powershell
   # Windows
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -e .
   ```
   ```bash
   # Linux/macOS
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

After installation, you can run the tool from anywhere using the `put-esys` command.

## Configuration

Instead of manually editing files, use the CLI to securely store your credentials:
```bash
put-esys config set
```
This will prompt you for your PUT email and password. Your credentials are stored locally in `~/.put-esys/config.json`.

You can also manage your configuration:
- **Show config**: `put-esys config show` (password is masked)
- **Delete config**: `put-esys config delete`

## Usage

The CLI handles authentication automatically. Once configured, you can directly run resource commands:

### Courses
List all your enrolled courses:
```bash
put-esys course list
```

Search enrolled courses (or all courses via `--all`):
```bash
put-esys course search "Machine Learning"
put-esys course search --all "Information Theory"
```

Browse course categories (faculties, degrees, semesters):
```bash
put-esys course categories
put-esys course categories 4      # WIiT
put-esys course categories 3160   # II Semestr [WIiT-SI-st-II] (Semestr 9)
```

Search global course catalog across all categories:
```bash
put-esys course find "Quantum"
```

Self-enrol into a course (with optional enrolment key):
```bash
put-esys course enrol 35839 --key "secret_key"
```

Show content of a specific course:
```bash
put-esys course show <course_id_or_url>
```


### Quizzes
View quiz information and status:
```bash
put-esys quiz info <quiz_id_or_url>
```

Start a new quiz attempt:
```bash
put-esys quiz start <quiz_id>
```

View an attempt (questions and answers):
```bash
put-esys quiz attempt <quiz_id> [attempt_id]
```

Edit an answer in an in-progress attempt:
```bash
put-esys quiz edit <quiz_id> <question_number> --text "Your new answer"
```

### Manual Login (Optional)
If you need to force a session refresh or test your credentials:
```bash
put-esys login
```

## Security

Authentication data (cookies) is stored in `~/.put-esys/session.json`. Your credentials are stored in `~/.put-esys/config.json`. These files are local to your user directory and are ignored by version control.
