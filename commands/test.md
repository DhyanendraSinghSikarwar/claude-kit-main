---
description: Detect the toolchain, run build and tests, and report failures as a table.
argument-hint: "[path or test filter, optional]"
allowed-tools: Bash, Read, Glob, Grep
---

Run the project's build and test suite and report the result.

Delegate to the `test-runner` agent if your runtime supports subagents — it detects the
toolchain and reports in the required shape. Otherwise follow the `test-summary` skill
inline, running the suite yourself first.

Scope the run to this path or filter if one is given: $ARGUMENTS

Report only: toolchain detected and commands run, build result, the pass/fail/skip counts,
a table of failures with expected and actual values quoted verbatim, and a final `PASS` or
`FAIL` on its own line. Do not propose fixes unless asked — report first.
