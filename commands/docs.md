---
description: Refresh the canonical repository documents against the current code, without running the rest of the gate.
argument-hint: "[documents to restrict to, optional]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

Use the `repo-doc-set` skill to bring the document canon back in line with the code. This is
for documentation that has drifted while no code changed — a change on its way to a commit
goes through `/precommit` instead, so its docs land in the same commit.

Current state, already gathered for you:

- Uncommitted changes: !`git diff HEAD --stat`
- Canon files present: !`ls -1d README.md PLAN.md TROUBLESHOOTING.md DEVELOPMENT.md ROADMAP.md AI.md ui_glossary.html docs/* 2>/dev/null`

Restrict the refresh to these documents if any are named, otherwise check the whole canon:
$ARGUMENTS

Update only what the code obliges and leave the rest untouched — an unrelated rewrite buries
the real change in the diff, so the real change goes unreviewed. Do not commit.
