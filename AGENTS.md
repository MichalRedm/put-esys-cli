# AGENTS.md - Master Instructions & Context for AI Assistants

Welcome to the **put-esys-cli** repository! This file serves as the primary entry point, high-level context map, and deterministic rule routing matrix for AI coding assistants.

---

## 🏛️ Project Architecture & Overview

`put-esys-cli` is a modular Python CLI utility and scraping client designed for electronic systems of Poznań University of Technology (PUT). Built with Typer, Requests, and BeautifulSoup4, it automates eLogin SSO authentication, interacts with eKursy (Moodle) for courses, assignments, and quizzes, and provides student email access over IMAP/SMTP.

---

## 🚦 Mandatory Rule Routing Matrix

Before writing or modifying any code, identify your target area and **read the corresponding rule file FIRST**:

| When working on / modifying... | Target Paths / Globs | Mandatory File to Read FIRST | Key Invariants & Pitfalls to Check |
| :--- | :--- | :--- | :--- |
| **CLI & Commands** | `put_esys/cli/**`, `put_esys/main.py` | [`.agents/rules/cli_standards.md`](.agents/rules/cli_standards.md) | • Non-interactive `-y/--yes` on mutative actions<br>• `--json` flag for untruncated structured output<br>• Direct `-o/--output` writing (UTF-8) over `>` redirection |
| **Scraping & Auth** | `put_esys/services/auth.py`, `put_esys/services/ekursy/**` | [`.agents/rules/scraping_and_auth_standards.md`](.agents/rules/scraping_and_auth_standards.md)<br>[`.agents/context/put_systems.md`](.agents/context/put_systems.md) | • Multi-hop SSO auto-redirect form submission<br>• `MoodleSession` cookie caching and reuse<br>• Moodle draft item upload protocol (`draftfiles.php`) |
| **Student Mail Client** | `put_esys/services/mail.py` | [`.agents/rules/scraping_and_auth_standards.md`](.agents/rules/scraping_and_auth_standards.md)<br>[`.agents/context/put_systems.md`](.agents/context/put_systems.md) | • IMAP SSL (993) / SMTP SSL (465) handling<br>• Proper MIME decoding and RFC-compliant folder paths |
| **Models & Architecture** | `put_esys/models/**`, `put_esys/services/**` | [`.agents/context/architecture.md`](.agents/context/architecture.md) | • Strict Pydantic v2 schemas<br>• Service layer separation from CLI presentation |
| **CI, Lint & Toolchains** | `pyproject.toml`, `.github/workflows/**` | [`.agents/rules/ci_standards.md`](.agents/rules/ci_standards.md) | • Zero Ruff violations (`ruff check .`)<br>• Support Python >= 3.9 (CI runs on 3.12) |
| **Agent Self-Maintenance** | `.agents/**` | [`.agents/rules/agent_maintenance_standards.md`](.agents/rules/agent_maintenance_standards.md) | • Synchronize context & rules on feature changes<br>• Follow [`.agents/skills/agent-maintenance/SKILL.md`](.agents/skills/agent-maintenance/SKILL.md) |

---

## 🔄 Operational Phase Gates

Every task must progress sequentially through these 5 lifecycle gates:

```
[ Gate 1: Rule & Contract Intake ] ➔ [ Gate 2: Implementation ] ➔ [ Gate 3: Local CI Verification ] ➔ [ Gate 4: Context Maintenance ] ➔ [ Gate 5: Git & PR Protocol ]
```

1. **Gate 1: Rule & Contract Intake (MANDATORY)**:
   - Identify target files; read required rule and context files from the *Rule Routing Matrix* using `view_file`.
   - Inspect data models in `put_esys/models/` and service interfaces before calling or altering methods.
2. **Gate 2: Implementation**:
   - Adhere strictly to golden patterns in `.agents/rules/` and avoid anti-pattern traps.
3. **Gate 3: Local CI Verification**:
   - Run local verification: `.venv\Scripts\ruff check .` (or `ruff check .`).
4. **Gate 4: Context Self-Maintenance**:
   - Follow [`.agents/skills/agent-maintenance/SKILL.md`](.agents/skills/agent-maintenance/SKILL.md) if commands, models, roadmap items, or rules evolved.
5. **Gate 5: Git & PR Protocol**:
   - Follow `git-commit-protocol` skill: atomic Conventional Commits (`feat:`, `fix:`, `docs:`, etc.) and pre-push verification.

---

## ⚙️ Core CLI Tools & Build Commands

Always run these commands from the repository root:

| Purpose | Working Directory | Command |
| :--- | :--- | :--- |
| **Lint & Style Check** | Repository root | `.venv\Scripts\ruff check .` (or `ruff check .`) |
| **Install in Editable Mode** | Repository root | `pip install -e .[dev]` |
| **Run CLI (Direct / Dev)** | Repository root | `python -m put_esys.main [command]` or `put-esys [command]` |
| **Run Helper Scripts** | Repository root | PowerShell: `.agents/skills/put-esys-cli/scripts/run.ps1 [command]`<br>Bash: `.agents/skills/put-esys-cli/scripts/run.sh [command]` |

---

## 🚨 Operational Boundaries & Escalation

- **Always**:
  - Consult the *Mandatory Rule Routing Matrix* before writing or modifying code.
  - Run full local verification commands (`ruff check .`) prior to submitting changes.
  - Keep commits atomic and adhere strictly to Conventional Commits.
- **Ask First (Human Escalation Gateways)**:
  - Adding new third-party dependencies to `pyproject.toml`.
  - Performing destructive actions or operations against remote university accounts.
  - Proposing architectural deviations departing from [`.agents/context/architecture.md`](.agents/context/architecture.md).
- **Never (Safety & Workflow Anti-Patterns)**:
  - Never commit credentials, passwords, session tokens, or local json cache files (`auth.json`, `session_cookies.json`, `ekursy_auth.json`).
  - Never use `# noqa` to suppress linter errors to force CI green.
  - Never pipe CLI output using `>` in PowerShell without UTF-8 awareness; prefer `-o/--output`.

---

## 📁 Repository Layout & Navigation Map

- `AGENTS.md`: Master entry point & rule routing matrix (this file)
- `README.md`: Public project documentation and quickstart
- `pyproject.toml`: Build configuration, dependencies, and Ruff settings
- `put_esys/`: Main Python package
  - `main.py`: CLI entry point with Windows UTF-8 console encoding setup
  - `cli/`: Typer sub-applications (`course.py`, `assignment.py`, `quiz.py`, `mail.py`, `config.py`)
  - `services/`: Core integration services (`auth.py`, `config.py`, `mail.py`, `ekursy/`)
  - `models/`: Pydantic data schemas (`course.py`, `assignment.py`, `quiz.py`, `mail.py`)
  - `utils/`: Utilities (Markdown conversion, helpers)
- `.agents/`: AI Assistant configuration, rules, context, and workspace skills
  - `acs.yaml`: Agent Configuration Schema with machine-readable path triggers
  - `project_context.md`: Living project status, architecture, and roadmap
  - `rules/`: Modular declarative rules (`cli_standards.md`, `scraping_and_auth_standards.md`, `ci_standards.md`, `agent_maintenance_standards.md`)
  - `context/`: Deep domain context (`architecture.md`, `put_systems.md`)
  - `skills/`: Project-specific workspace skills
    - `put-esys-cli/SKILL.md`: Detailed CLI usage and agent scripting guide
    - `agent-maintenance/SKILL.md`: Autonomous .agents/ context maintenance workflow
