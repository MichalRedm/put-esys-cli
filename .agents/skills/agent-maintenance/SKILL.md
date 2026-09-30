---
name: agent-maintenance
description: Maintain and update the .agents/ directory structure and root AGENTS.md to reflect the current state of the repository after completing features, updating models, or altering dependencies.
---

# Agent Repo Maintenance Skill

Use this skill when you finish implementing a major feature, detect a shift in the tech stack or dependencies, modify models or service endpoints, or resolve significant architectural debts.

---

## Maintenance Procedure

1. **Update Project Context (`.agents/project_context.md`)**:
   - Check off `[x]` finished roadmap tasks.
   - Add upcoming `[ ]` roadmap items.
   - Update the current objective and milestone summary.

2. **Synchronize Data Models & Architecture (`.agents/context/`)**:
   - Update `architecture.md` if components, models, or service relationships evolved.
   - Update `put_systems.md` if endpoint URLs, form structures, or system behaviors changed.

3. **Refine Rules & Standards (`.agents/rules/`)**:
   - Add new conventions or patterns to `cli_standards.md` or `scraping_and_auth_standards.md`.
   - Record newly discovered edge cases or fixes in the **Anti-Pattern & Pitfall Traps** tables.
   - Update `ci_standards.md` if linter, build, or test commands change.

4. **Verify Master Entry Point (`AGENTS.md`)**:
   - Ensure newly added areas have corresponding rows in the **Mandatory Rule Routing Matrix**.
   - Verify that `AGENTS.md` remains concise (< 140 lines).

5. **Commit Updates**:
   - Stage and commit `.agents/` documentation alongside feature code following `git-commit-protocol`.
