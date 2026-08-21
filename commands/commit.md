---
description: Draft a Conventional Commits message from the staged diff. Does not commit.
argument-hint: "[extra context, optional]"
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git log:*), Read, Glob, Grep
---

Use the `commit-draft` skill to produce a commit message for the change currently in the
working tree.

Current state, already gathered for you:

- Status: !`git status --short`
- Staged diff stat: !`git diff --staged --stat`
- Recent subjects, to match the repo's style: !`git log --oneline -15`

If nothing is staged, say so in one line and describe the unstaged changes instead.

Additional context from the user (may be empty): $ARGUMENTS

Output the message only — no preamble, no fences, nothing after it. Do not run `git commit`.
