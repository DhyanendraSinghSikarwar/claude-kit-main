---
description: Wire this kit into the current project and write a starter CLAUDE.md.
argument-hint: "[reference | working-copy]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

Use the `project-bootstrap` skill to set this project up.

- Repo root contents: !`ls -a`
- Toolchain markers: !`ls pyproject.toml go.mod package.json Cargo.toml pom.xml Makefile justfile 2>/dev/null || echo "(none found at root)"`
- CI workflows: !`ls .github/workflows 2>/dev/null || echo "(none)"`
- Existing agent config: !`ls -R .claude 2>/dev/null || echo "(none)"`
- Commit style sample: !`git log --oneline -20 2>/dev/null || echo "(no git history)"`

Integration mode, if the user specified one: $ARGUMENTS. If empty, ask — the choice between
reference and working-copy is theirs, and it is not reversible without effort.

Read the project before writing anything. Present the proposed agent and skill selection with
a reason for each, and let the user cut it down before you create files. Verify every command
you put in CLAUDE.md by actually running it.
