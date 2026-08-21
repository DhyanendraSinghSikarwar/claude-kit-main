---
description: Run the linters and type checkers this project configures, grouped by rule.
argument-hint: "[path to restrict to, optional]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

Lint this project by following the `python-lint` skill.

Configuration already found for you:

- Tool config: !`ls -1 pyproject.toml ruff.toml .ruff.toml .flake8 setup.cfg mypy.ini pyrightconfig.json .pylintrc .pre-commit-config.yaml 2>/dev/null`
- Pre-commit hooks, if any: !`grep -E '^\s+- id:' .pre-commit-config.yaml 2>/dev/null | head -12`

Restrict the run to this path if one is given: $ARGUMENTS

Run only what this project configures — a linter it has not adopted reports thousands of
findings against rules nobody chose. Group findings by rule with counts, keep formatting
separate from correctness, and end with `PASS` or `FAIL`.

Do not silence a finding with a blanket `noqa`, `type: ignore`, or a loosened limit.
