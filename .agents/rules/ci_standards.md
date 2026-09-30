# CI Standards & Local Verification Rules

> [!IMPORTANT]
> **Trigger Paths**: `.github/workflows/**`, `pyproject.toml`, `Makefile`
> **When to Read**: MUST be read before committing code, pushing commits, or creating pull requests.

To maintain high code quality and prevent CI failures, all changes must be verified locally before pushing to the repository.

---

## 1. Core Principles & Stack

- **Automated Pipeline**: GitHub Actions runs on Ubuntu with Python 3.12 (`.github/workflows/ci.yml`).
- **Python Compatibility**: The package targets Python `>= 3.9`. Avoid language features introduced exclusively in Python 3.10+ without compatibility considerations unless supported across the target matrix.
- **Linter & Formatter**: Ruff is configured in `pyproject.toml` with line length 100 and rules `E` (Pyflakes/Error), `F` (Pyflakes), and `I` (isort).
- **Zero Suppression Policy**: Never introduce `# noqa` or `# type: ignore` comments to silence legitimate lint or type violations.

---

## 2. Declarative Code Standards (Golden Patterns)

### Mandatory Local Verification Command
Run Ruff before staging or committing any code:
```bash
ruff check .
```

If using a virtual environment on Windows:
```powershell
.venv\Scripts\ruff check .
```

### Auto-fixing Import and Formatting Issues
Where applicable, use Ruff's automatic fixes:
```bash
ruff check --fix .
```

---

## 3. Anti-Pattern & Pitfall Traps

| Anti-Pattern Trap | Why It Fails | Golden Pattern |
| :--- | :--- | :--- |
| **Using `# noqa` to hide errors** | Masks underlying logic bugs, missing imports, or unused variables; fails CI hygiene. | Resolve the underlying error directly (remove unused imports, correct syntax). |
| **Pushing without local `ruff check`** | Triggers avoidable CI run failures and pollutes Git commit history. | Always execute `ruff check .` locally as part of Gate 3 before any commit. |
| **Introducing Python 3.10+ syntax** (e.g. `int \| str` union without `from __future__ import annotations`) | Crashes environments running Python 3.9, which is the declared minimum supported runtime. | Use `from typing import Optional, Union` or add `from __future__ import annotations`. |
| **Hardcoding OS-specific python paths** | Scripts become non-portable across Windows PowerShell, Linux, and macOS. | Reference `python -m <module>` or activate virtual environments via standard shell wrappers. |
