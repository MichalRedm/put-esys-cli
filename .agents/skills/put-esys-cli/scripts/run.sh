#!/bin/bash

# Find the project root (4 levels up from this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../../../" && pwd )"

VENV_PATH="$PROJECT_ROOT/.venv"
PYTHON_EXE="$VENV_PATH/bin/python"

if [ ! -f "$PYTHON_EXE" ]; then
    # Try Windows path just in case we are in Git Bash
    PYTHON_EXE="$VENV_PATH/Scripts/python"
    if [ ! -f "$PYTHON_EXE" ]; then
        echo "Virtual environment not found at $VENV_PATH. Please run 'python -m venv .venv' in the project root."
        exit 1
    fi
fi

MAIN_PATH="$PROJECT_ROOT/put_esys/main.py"
"$PYTHON_EXE" "$MAIN_PATH" "$@"
