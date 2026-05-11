# PUT Electronic Systems CLI (put-esys)

A command-line interface for accessing various electronic systems of Poznań University of Technology (PUT).

Currently supports:
- **eKursy** (Moodle-based learning platform)

## Features

- **Automated Authentication**: Handles the complex PUT SSO (Single Sign-On) redirection chain.
- **Persistent Sessions**: Saves authentication cookies locally for seamless multi-session access.
- **eKursy Integration**: Scrapes and lists your enrolled courses with direct links.

## Installation

1. Clone the repository.
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows
   pip install -e .
   ```

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

### eKursy
List all your enrolled courses:
```bash
put-esys ekursy
```

### Manual Login (Optional)
If you need to force a session refresh or test your credentials:
```bash
put-esys login
```

## Security

Authentication data (cookies) is stored in `~/.put-esys/session.json`. Your credentials are stored in `~/.put-esys/config.json`. These files are local to your user directory and are ignored by version control.
