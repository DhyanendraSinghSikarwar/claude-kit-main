---
name: test-summary
description: Use whenever a test suite is run and produces output, or when the user pastes failing test output. Compresses the run down to failures plus a count, so debugging works from a table instead of raw scrollback.
---

# Summarise a test run

Turns raw test output into a short failure table. The goal is to keep thousands of lines of
passing-test noise out of the working context and debug from structured facts instead.

## Delegation

If your runtime supports subagents, spawn one with the body of `../../agents/test-summarizer.md`
as its instructions (ignore that file's YAML frontmatter) and pass it the raw output. A cheap
model is sufficient — this is parsing, not reasoning. Then debug from its table rather than
the raw scrollback.

If you also need the suite *run*, use `../../agents/test-runner.md` instead: it detects the
toolchain, runs build and tests, and reports in this same shape.

If your runtime has no subagents, follow the procedure below inline.

## When to bother

Summarise if the output is longer than about 30 lines, or contains a stack trace. Below
that, just read it — summarising short output wastes a step.

## Procedure

### Step 1 — identify the runner

Match the output against this table:

| Looks like | Runner | Where the count is |
| --- | --- | --- |
| `FAILED tests/...::test_name`, `assert` lines | pytest | final line: `N failed, M passed` |
| `FAIL: test_name (module.Class)`, `Ran N tests` | unittest | `Ran N tests`, then `FAILED (failures=N)` |
| `● Suite › test name`, `Tests:` summary block | Jest / Vitest | the `Tests:` line |
| `--- FAIL: TestName`, `ok`/`FAIL` per package | Go | per-package `ok` / `FAIL` lines |
| `test name ... FAILED`, `test result:` | Cargo | the `test result:` line |
| `Failed! - Failed: N, Passed: N` | dotnet test | final `Failed!` / `Passed!` line |
| `Tests run: N, Failures: N` | Maven Surefire | the `Tests run:` line |

If none match, treat any line containing `FAIL`, `FAILED`, `ERROR`, or `✗` as a failure
marker, and say which convention you assumed.

### Step 2 — extract, per failure

For each failing test, pull out exactly these five fields. Quote the assertion text
verbatim — do not paraphrase it, because the exact values are the diagnostic content.

1. Test name (fully qualified if the runner gives it).
2. File and line where the assertion failed.
3. Expected value.
4. Actual value.
5. Exception type and message, if the failure was an error rather than an assertion.

If a field is genuinely absent from the output, write `—`. Do not infer it.

### Step 3 — group by root cause

Failures sharing the same exception type **and** the same failing line are one problem, not
N problems. Collapse them into a single row and note the count: `× 12`. This is usually
where the compression comes from — a single broken fixture can fail fifty tests.

### Step 4 — separate errors from failures

Keep these apart, because they mean different things:

- **Failure** — the test ran and an assertion was false. The code is wrong, or the test is.
- **Error** — the test could not run: import error, missing fixture, syntax error, missing
  dependency. Errors usually mask failures, so report them first and note that the failure
  count is not trustworthy until they are resolved.

### Step 5 — output

Use exactly this shape:

```markdown
**Result**: N passed, M failed, S skipped, E errors

| # | Test | File:line | Expected | Actual | Cause |
| --- | --- | --- | --- | --- | --- |
| 1 | test_parses_iso_date | parser.py:88 | `2024-01-01` | `None` | AssertionError |
| 2 | test_rejects_empty (× 12) | parser.py:104 | raises ValueError | no raise | AssertionError |

**Errors (blocking)**

- `tests/conftest.py` — `ModuleNotFoundError: no module named 'freezegun'`

**Verdict**: FAIL
```

Omit the errors block if there are none. End with `PASS` or `FAIL` on its own line.

### Step 6 — do not do these

- Do not propose fixes in the summary. Summarising and fixing are separate steps; mixing
  them makes it easy to fix a symptom of a masked error.
- Do not include passing test names. Ever. That is the noise being removed.
- Do not truncate an assertion message to make the table tidy. Put long values in a fenced
  block underneath the table instead.
