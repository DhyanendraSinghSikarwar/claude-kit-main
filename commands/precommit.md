---
description: Run the pre-commit gate — test, fix, document, changelog, commit, push.
argument-hint: "[scope or extra context, optional]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

Use the `pre-commit-gate` skill to take the current working tree to a tested, documented,
committed, pushed state.

Current state, already gathered for you:

- Status: !`git status --short`
- Staged diff stat: !`git diff --staged --stat`
- Branch: !`git rev-parse --abbrev-ref HEAD`
- Recent subjects: !`git log --oneline -15`

Scope or extra context from the user (may be empty): $ARGUMENTS

End in exactly one of the skill's three terminal states — `GREEN`, `BLOCKED`, or
`DIRTY-STOP` — named on its own line. Do not reach green by deleting, skipping, or loosening
a test: that retires the detector and leaves the defect, which is worse than a red suite.
