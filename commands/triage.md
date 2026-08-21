---
description: Reduce a log dump or CI failure to a table of distinct error signatures.
argument-hint: "[log file path, or paste the log after the command]"
allowed-tools: Bash, Read, Grep, Glob
---

Use the `log-triage` skill on the input below.

Input: $ARGUMENTS

If that is a file path, read the file. If it is pasted text, use it directly. If it is
empty, ask which log to triage — do not guess, and do not go hunting through the repo for
log files.

Return the grouped signature table, name the group you believe is causal and why, and
include a representative record for the top three groups only. Never paste the whole log back.
