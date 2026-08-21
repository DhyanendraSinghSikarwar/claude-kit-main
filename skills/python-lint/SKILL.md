---
name: python-lint
description: Run the linters, formatters, and type checkers a Python project actually configures, compress their output into a table grouped by rule, and fix what is safe to fix. Use before committing Python, when a lint or type-check run needs reading, or when CI fails on style or typing.
---

# Lint Python

Runs the project's own checkers and turns their output into a short table grouped by rule.
Lint output is long, repetitive, and mostly one rule firing many times — the compression is
the point, and it is the same trick the `log-triage` skill applies to logs.

The second point is narrower and matters more: **the project's configuration decides which
rules apply.** A linter run with its defaults against a codebase that never adopted them
emits thousands of findings, which reads as catastrophe and is actually noise.

## Delegation

Detection and running are mechanical. Spawn a subagent with the body of
`../../agents/lint-runner.md` (tier `cheap`) and work from the table it returns rather than
the raw output. Deciding what to do about a finding stays here — that is the judgement.

Without subagents, follow the procedure below inline and pipe the output through the grouping
in step 3 before reading it.

## Step 1 — find what the project configures

Never assume the toolchain. Read the config first.

| Config location | Tool |
| --- | --- |
| `[tool.ruff]` in `pyproject.toml`, `ruff.toml` | `ruff check .`, `ruff format --check .` |
| `.flake8`, `setup.cfg` `[flake8]`, `tox.ini` `[flake8]` | `flake8` |
| `[tool.black]` | `black --check .` |
| `[tool.isort]`, `.isort.cfg` | `isort --check-only .` |
| `[tool.mypy]`, `mypy.ini` | `mypy .` |
| `pyrightconfig.json`, `[tool.pyright]` | `pyright` |
| `.pylintrc`, `[tool.pylint]` | `pylint <package>` |
| `.pre-commit-config.yaml` | `pre-commit run --all-files` — prefer this |

`.pre-commit-config.yaml` wins when present: it is the exact set CI gates on, in the versions
it pins, so it is the only run whose result predicts CI.

Run the tools from the project's own environment. A globally installed linter may be a
different version enforcing different rules, and findings that do not reproduce in CI waste
everyone's time twice.

If the project configures nothing, say so and stop. Proposing a ruleset is a separate
decision that belongs to the project's owner — adopting one mid-commit produces a diff of
hundreds of unrelated files.

## Step 2 — clear the errors that hide the rest

A tool that fails to start reports nothing, and nothing reads exactly like clean.

| Symptom | Meaning |
| --- | --- |
| `SyntaxError` during collection | The file never parsed; every other rule was skipped for it |
| `ModuleNotFoundError` from mypy | Missing stubs or an unresolved import; type coverage is a floor, not a result |
| `command not found` | The tool is not in this environment — say so, do not substitute another |
| Zero findings on a large codebase | Suspect the file selection, not perfection. Check what was actually scanned |

That last row is the one to take seriously. A misconfigured `exclude` or a wrong path argument
silently produces a perfect score.

## Step 3 — group by rule, not by file

One rule firing 400 times is one decision, not 400. Report:

```markdown
**Tools**: ruff 0.6.9, mypy 1.11 — from `.pre-commit-config.yaml`

| Rule | Count | Meaning | Example |
| --- | --- | --- | --- |
| F401 | 23 | unused import | `src/api/views.py:4` |
| E501 | 8 | line too long | `src/parser.py:112` |
```

Keep formatting findings separate from correctness findings, because they carry different
risk and should be applied differently.

## Step 4 — fix by class, not one at a time

| Class | Examples | How |
| --- | --- | --- |
| **Mechanical** | formatting, import order, quote style, trailing whitespace | Apply the formatter wholesale. Commit it *separately* from behavioural changes — a formatting pass mixed into a feature diff makes the feature unreviewable |
| **Safe, local** | unused import, unused variable, redundant `pass` | Apply, then run the tests. An "unused" import may be doing registration work through its side effects |
| **Needs judgement** | mutable default argument, bare `except`, shadowed builtin, complexity limits | Fix the cause. These are usually real defects that the linter merely noticed |
| **Wrong for this project** | a rule that fights a deliberate convention | Do not silence it inline. Change the config, once, with a comment saying why |

Never apply a blanket `# noqa` or `# type: ignore` to reach a clean run. A file-wide silence
disables the rule for code not yet written, which is where it would have earned its keep. If a
single line genuinely warrants suppression, suppress that line with its specific code
(`# noqa: E501`) and a reason.

## Step 5 — type errors are not lint

Treat a type error as a possible bug rather than a style finding. `Argument 1 has incompatible
type "str"; expected "int"` is often a real defect that no test happens to reach.

Do not fix one by widening the annotation to `Any` or adding `# type: ignore`. That silences
the report while leaving the mismatch, and it removes the type's value everywhere it
propagates. Fix the value or fix the signature.

Where a checker is wrong because a third-party library lacks stubs, install the stubs or
declare the module in the config — a targeted, documented exception rather than a scattered
one.

## Do not

- Do not introduce a linter the project has not adopted.
- Do not reformat files the current change does not touch. It buries the real diff.
- Do not fix lint and behaviour in the same commit.
- Do not raise a complexity or line-length limit to make a finding disappear.
- Do not report `PASS` when a tool failed to run.

## Verify

- [ ] Every tool run is one the project configures, at the project's own version.
- [ ] No tool failed to start, and the file selection was checked if the run looked too clean.
- [ ] Findings are grouped by rule, with counts.
- [ ] Formatting changes are in their own commit, separate from behavioural changes.
- [ ] No blanket `noqa`, `type: ignore`, or config loosening was used to reach clean.
- [ ] The tests still pass after any automated fix.
- [ ] The result ends in `PASS` or `FAIL`.
