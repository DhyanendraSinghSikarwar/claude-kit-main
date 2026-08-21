---
description: Deep correctness review of pending changes before a release — invariants, API usage, and data safety.
argument-hint: "[area to focus on, optional]"
allowed-tools: Bash, Read, Glob, Grep
---

Run a pre-release correctness review using the `release-validator` agent if your runtime
supports subagents; otherwise follow that agent's instructions inline.

- Uncommitted changes: !`git status --short`
- Diff since last tag: !`git diff $(git describe --tags --abbrev=0 2>/dev/null)..HEAD --stat 2>/dev/null || git diff --stat HEAD~10..HEAD`

Focus area, if the user named one: $ARGUMENTS

Establish the project's intended behaviour from its own docs before judging anything. Group
findings as Blocker, Should fix, or Consider, with file and line. Distinguish what you
verified by reading or running code from what you are inferring. Do not invent findings to
appear thorough, and do not soften a real blocker.
