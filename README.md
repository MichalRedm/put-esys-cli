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

Create a `.env` file in the root directory with your PUT credentials:
```env
ELOGIN_USERNAME=your.email@student.put.poznan.pl
ELOGIN_PASSWORD=your_password
```

## Usage

### Authentication
Login to the system (required once or when session expires):
```bash
put-esys login
```

### eKursy
List all your enrolled courses:
```bash
put-esys ekursy
```

## Security

Authentication data is stored locally in `~/.put-esys/session.json`. Your credentials in `.env` are only used by the `login` command and are never shared.
