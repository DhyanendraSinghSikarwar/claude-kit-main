---
description: Draft a PR description for the current branch against its base.
argument-hint: "[base branch, defaults to main]"
allowed-tools: Bash(git:*), Read, Glob, Grep
---

Use the `commit-draft` skill's PR description section to draft a pull request description for
the current branch.

- Current branch: !`git rev-parse --abbrev-ref HEAD`
- Commits on this branch: !`git log --oneline main..HEAD 2>/dev/null || git log --oneline -20`
- Changed files: !`git diff --stat main...HEAD 2>/dev/null || git diff --stat HEAD~5..HEAD`

Base branch, if the user named one: $ARGUMENTS. If empty, use `main`, falling back to
`master` if `main` does not exist.

Read the actual diff before writing — the commit subjects alone are not enough. Output the
description as Markdown, and nothing else.
