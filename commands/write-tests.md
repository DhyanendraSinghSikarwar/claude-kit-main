---
description: Write tests that can actually fail — a regression test, coverage for an untested module, or a first suite.
argument-hint: "[module, behaviour, or bug to cover]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

Write tests by following the `test-authoring` skill. This writes tests; `/test` runs them.

Context, already gathered for you:

- Changed recently: !`git diff HEAD --stat`
- Existing test layout: !`git ls-files | grep -Ei '(^|/)(tests?|spec)/|_test\.|\.test\.|_spec\.|\.spec\.' | head -20`

Cover this, if named: $ARGUMENTS

Every new test must be observed failing before it is observed passing — against the unfixed
code for a regression, or against a deliberately broken behaviour otherwise. Report the
fail-first result for each test alongside the full-suite result.

Do not fix the code under test, weaken an existing test, or add anything purely to move a
coverage number.
