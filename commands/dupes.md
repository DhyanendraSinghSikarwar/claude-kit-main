---
description: Find near-duplicate and copy-pasted code, and judge which are worth merging.
argument-hint: "[directory to scan, defaults to the source root]"
allowed-tools: Bash, Read, Grep, Glob
---

Use the `dupe-check` skill.

Scan this directory: $ARGUMENTS. If empty, infer the source root from the project layout
(`src/`, `lib/`, `cmd/`, or the package directory) and say which you chose. Do not scan the
whole repository by default.

Report the candidate table sorted by lines duplicated times occurrences, then apply the
judgement step: for each group say whether it is worth consolidating and why, or why not.
A scan that flags twelve groups and recommends two is a good result.
