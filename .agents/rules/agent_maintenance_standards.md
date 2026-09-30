# Agent Context Self-Maintenance Standards

> [!IMPORTANT]
> **Trigger Paths**: `.agents/**`
> **When to Read**: MUST be read upon completing features, changing tech stack dependencies, evolving models or services, or resolving recurring pitfalls.

To maintain `.agents/` as the single authoritative Source of Truth, all AI assistants must proactively maintain and refine documentation, schema context, and rules whenever changes occur.

---

## 1. Core Principles & Stack

- **Progressive Disclosure**: High-level guidance resides in `AGENTS.md`; detailed schemas and specifications live in `.agents/context/`; operational guidelines live in `.agents/rules/`.
- **Machine-Readable Triggers**: Every rule and context layer must be cataloged in `.agents/acs.yaml` with accurate `trigger_paths`.
- **Zero Drift**: Documentation and context files must be updated in the same commit as the code changes that altered the behavior.

---

## 2. Declarative Code Standards (Golden Patterns)

### Mandatory Maintenance Triggers

| Trigger Event | Action Required | Target File(s) |
| :--- | :--- | :--- |
| **New CLI Command / Sub-app** | Document command in `put-esys-cli/SKILL.md`, update navigation map in `AGENTS.md`. | `.agents/skills/put-esys-cli/SKILL.md`<br>`AGENTS.md` |
| **Model / Service Schema Change** | Update architectural contracts and specifications. | `.agents/context/architecture.md`<br>`.agents/context/put_systems.md` |
| **Dependency / Tooling Change** | Update `pyproject.toml` references, CI verification commands, and environment setup. | `.agents/rules/ci_standards.md`<br>`.agents/project_context.md` |
| **Recurring Pitfall Resolved** | Add declarative guardrails and an anti-pattern table row. | Relevant rule in `.agents/rules/` |
| **Roadmap Milestone Reached** | Mark task as `[x]`, add upcoming roadmap items, update objective. | `.agents/project_context.md`<br>`.agents/acs.yaml` |

### Standard Maintenance Procedure
1. Review modified files (`git status`, `git diff --stat`).
2. Update corresponding `.agents/context/` or `.agents/rules/` files.
3. Update `Repository Status` in `.agents/project_context.md`.
4. Stage and commit `.agents/` updates alongside feature code following `git-commit-protocol`.

---

## 3. Anti-Pattern & Pitfall Traps

| Anti-Pattern Trap | Why It Fails | Golden Pattern |
| :--- | :--- | :--- |
| **Deferring context updates to "later"** | Documentation rapidly drifts from code; subsequent AI agents make false assumptions. | Update `.agents/` in the same commit or immediately after code implementation. |
| **Adding files without updating `acs.yaml`** | Machine-readable trigger routing fails; automated rule loading misses new files. | Register any new rule, context, or skill in `.agents/acs.yaml` with explicit `trigger_paths`. |
| **Bloating `AGENTS.md` over 140 lines** | Overloads agent context window upon initial orientation; leads to instruction blindness. | Keep `AGENTS.md` dense and push deep technical details into `.agents/context/` or `.agents/rules/`. |
| **Committing transient session memory** | Pollutes repository history with machine-specific logs and ephemeral notes. | Keep ephemeral scratch files in `scratch/` or `.agents/archive/` (both ignored in `.gitignore`). |
