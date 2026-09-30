# CLI Standards & Guidelines

> [!IMPORTANT]
> **Trigger Paths**: `put_esys/cli/**`, `put_esys/main.py`
> **When to Read**: MUST be read before adding or modifying CLI commands, arguments, options, or output formatters.

This document establishes development standards for all command-line interfaces within `put-esys-cli`, ensuring compatibility with interactive users, automated scripts, and AI coding agents.

---

## 1. Core Principles & Stack

- **Framework**: `typer` is used for command routing and CLI argument parsing; `rich` is used for terminal presentation (tables, colors, panels).
- **Dual-Mode Output**:
  - Human mode: formatted Rich tables, panels, and colored status messages.
  - Machine / Scripting mode: unformatted, untruncated JSON emitted directly to stdout or to file when `--json` is supplied.
- **Non-Interactive Execution**: Every command that performs a destructive, modifying, or irreversible operation (e.g. `submit`, `delete`) must provide `-y` / `--yes` to bypass interactive confirmation prompts.
- **Windows UTF-8 Encoding**: Windows console defaults to legacy codepages. All entry points must reconfigure stdout/stderr to UTF-8.
- **File Output Over Shell Redirection**: Standard PowerShell redirection (`>`) writes UTF-16LE, which corrupts subsequent Python/UTF-8 reads. All data-retrieving commands must provide `-o` / `--output` to write directly in UTF-8.

---

## 2. Declarative Code Standards (Golden Patterns)

### Command Definition with Output and Automation Flags
```python
import json
import typer
from typing import Optional
from put_esys.cli.helpers import catch_errors

app = typer.Typer()

@app.command()
@catch_errors
def show(
    item_id: str = typer.Argument(..., help="Item identifier"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Write output to file"),
    yes: bool = typer.Option(False, "-y", "--yes", help="Skip confirmation prompts"),
):
    """Retrieve and display item details."""
    data = fetch_item(item_id)
    if json_output:
        content = json.dumps(data.model_dump(), indent=2, ensure_ascii=False)
        if output:
            with open(output, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            typer.echo(content)
        return
```

### Windows Console UTF-8 Reconfiguration
```python
import sys

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
```

---

## 3. Anti-Pattern & Pitfall Traps

| Anti-Pattern Trap | Why It Fails | Golden Pattern |
| :--- | :--- | :--- |
| **Interactive prompts without `-y/--yes` bypass** | Background agents and automated scripts hang indefinitely waiting for stdin. | Add `yes: bool = typer.Option(False, "-y", "--yes")` and skip `typer.confirm()` when true. |
| **Only providing Rich formatted tables** | Rich truncates URLs and long text with ellipsis `…` based on terminal width, breaking parsers. | Implement `--json` flag returning raw untruncated structured Pydantic models. |
| **Relying on shell `>` redirection on Windows** | PowerShell creates UTF-16LE files by default, causing UTF-8 decoders to crash on subsequent steps. | Implement `-o` / `--output` options that write directly via `open(path, "w", encoding="utf-8")`. |
| **Calling `sys.exit()` directly in Typer commands** | Bypasses Typer cleanup, exception formatting, and testing harness execution. | Raise `typer.Exit(code=1)` or wrap commands with `@catch_errors`. |
| **Writing status messages to stdout during JSON mode** | Pollutes JSON output stream with human log messages, causing JSON deserialization errors. | Write status messages to `stderr` or suppress them when `--json` is active. |
