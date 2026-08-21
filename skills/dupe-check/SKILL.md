---
name: dupe-check
description: Use before a refactor pass, when reviewing a large diff, or when asked to find repeated or copy-pasted code. Flags near-duplicate and boilerplate blocks across a repository.
---

# Find duplicate code

Flags near-duplicate and copy-pasted blocks so a refactor can target the ones worth
consolidating. Flagging and judging are separate: the scan finds candidates, you decide
which are real.

## Delegation

If your runtime supports subagents, spawn one with the body of `../../agents/dupe-detector.md`
as its instructions (ignore that file's YAML frontmatter), scoped to the target directory.
Tier `cheap` is sufficient. Then apply step 5 below yourself — the subagent only flags, it
does not judge intent.

If your runtime has no subagents, follow the procedure below inline.

## Procedure

### Step 1 — scope the scan

Ask for, or infer, a target directory. Never scan the whole repo by default on a large
codebase — it is slow and mostly returns vendored code.

Always exclude: `node_modules`, `vendor`, `.venv`, `venv`, `dist`, `build`, `target`,
`__pycache__`, `.git`, generated files (anything with a `DO NOT EDIT` or `@generated`
header), lockfiles, and minified assets.

Include source extensions only: `.py .go .js .ts .jsx .tsx .rs .java .cs .rb .php .sql .css
.scss .html`.

### Step 2 — prefer a real tool if one is installed

A purpose-built detector beats hand-rolled matching. Try, in order, and use the first
available:

```bash
jscpd --min-lines 8 --min-tokens 60 --reporters consoleFull <dir>   # any language
pmd cpd --minimum-tokens 60 --dir <dir> --language <lang>            # JVM-family, C, others
```

If neither is installed, do **not** install anything. Fall back to step 3.

### Step 3 — manual scan

Normalise before comparing, otherwise trivial differences hide real duplicates. For each
candidate block, strip comments, collapse all runs of whitespace to a single space, and
replace every identifier, string literal, and number with a placeholder token. Compare the
normalised forms.

A block is a candidate when it is **8 or more consecutive non-blank, non-comment lines**.
Report a pair when the normalised forms are identical, or differ only in identifier names.

Practical shortcuts that find most real duplication quickly:

- Function and method bodies of similar length in the same package.
- Repeated literal blocks: the same `switch`/`if-elif` ladder, the same error-handling
  wrapper, the same three-line validation preamble.
- Files whose names suggest parallel implementations (`v1.py`/`v2.py`, `handler_a`/`handler_b`).

### Step 4 — output

```markdown
| # | Lines | Locations | Kind |
| --- | --- | --- | --- |
| 1 | 24 | `api/users.go:40-64`, `api/orders.go:88-112` | identical but for the model type |
| 2 | 9 | `etl/load.py:12-20`, `etl/backfill.py:55-63`, `etl/repair.py:31-39` | identical |
```

Sort by lines duplicated × number of occurrences, descending. That is the quantity a
refactor actually removes.

### Step 5 — judge before recommending

This step is mandatory and is where the value is. Duplication is not automatically a defect.
Do not recommend consolidating a group when any of these apply:

- **Test fixtures and table-driven test cases.** Deliberate parallel structure is a feature;
  merging it makes tests harder to read and couples unrelated cases.
- **The copies are diverging on purpose.** Two handlers that look alike today but belong to
  independently versioned APIs should stay separate — merging them creates a coupling that
  the next change has to undo.
- **The shared abstraction would need more parameters than the duplication has lines.** A
  helper with six flags is worse than three explicit copies.
- **Generated or vendored code**, which should have been excluded in step 1 anyway.

For each group you *do* recommend, state what the extracted unit would be and where it
should live. For each you reject, state the reason in one clause. A scan that flags twelve
groups and recommends two is a good result, not a weak one.
