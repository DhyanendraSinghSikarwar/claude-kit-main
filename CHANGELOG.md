# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `sweep-check` skill — the inverse of `dupe-check`. Where that one finds the same code in
  several places, this finds a rule that should be in several places and is only in one: a
  new enum member, status, kind or predicate added to some of the sites that have to know
  about it. Nothing throws and nothing goes red, because every file read on its own is
  correct. Carries the five shapes it keeps finding — a default plus overrides, a rule
  spliced into N queries, a bug of omission patched at the one reported case, a foreign-key
  walk that misses polymorphic rows, and a presence flag in a slot typed as a callback —
  and insists the invariant test **enumerate the vocabulary** rather than a hand-written
  copy of it, because a test whose coverage is a copy of the thing it tests agrees with it
  forever.
- `js-test-harness` skill — the front-end testing that is not about what to assert: the two
  projects (`node` for pure logic, `jsdom` only where a component is genuinely under test),
  and the environment pins without which a suite passes locally and fails on CI. Names the
  jsdom APIs that answer *uselessly* rather than throwing — `getBoundingClientRect`
  returning zeros, absent `IntersectionObserver`/`ResizeObserver`/`matchMedia` — because
  silence is what makes a working component look broken. Includes the timeout failure that
  reads exactly like a hung `await` and is worker parallelism, and the locale pin that is
  ignored on Windows when set as an env var, which is how date assertions ship depending on
  the author's machine.
- `doc-oracle` agent — answers a question from a project's oversized documents (a decision
  log, a design history, a generated glossary or roadmap) with citations, without loading
  them into the caller's context. Reports reversals as well as decisions, since an entry
  recording that a decision was wrong stays true forever, and treats the prose as a hint
  about the tree while the code stays the truth.
- `pre-commit-gate` skill — the ritual that runs before every commit: sync, run the full
  suite, triage and fix, re-test, verify the interface, refresh the documents, write the
  changelog entry, then commit and push. Ends in exactly one of GREEN, BLOCKED, or
  DIRTY-STOP, so a run can never trail off leaving it unclear whether the work is committed.
- `repo-doc-set` skill — the seven documents every repository carries (`README.md`,
  `PLAN.md`, `TROUBLESHOOTING.md`, `DEVELOPMENT.md`, `ROADMAP.md`, `AI.md`, and
  `ui_glossary.html` where there is an interface), each with what does *not* belong in it.
- `visual-verify` skill — deterministic screenshots, described into a temporary Markdown
  record, then audited against what the project's own documents promise: alignment, colour
  grading, icon and text legibility, promised features present, and changes reflected.
- `ai-disclosure` skill and `ai_census.py` — `AI.md` plus the commands that reproduce every
  figure in it, so the declaration can be checked rather than believed.
- `ui-glossary` skill — a self-contained `ui_glossary.html` naming every UI element,
  derived from the source rather than from screenshots.
- `test-authoring` skill, `test-author` agent, and `/write-tests` — writing tests, as work
  separate from running them. Every test must be observed failing before it is observed
  passing, because a test never seen to fail has not been shown to assert anything.
- `jupyter-hygiene` skill and `notebook-cleaner` agent — notebook outputs stripped before
  they reach a diff, scanned for captured secrets first, because stripping destroys the
  evidence that a credential needs rotating.
- `python-lint` skill, `lint-runner` agent, and `/lint` — runs only what a project
  configures, grouped by rule rather than by file.
- `code-standards` skill — derives the conventions a codebase actually follows from at least
  three files each, rather than imposing generic best practice over an established pattern.
- `css-review` skill — token discipline, specificity creep, dead rules, and breakpoint
  coherence: the structural problems a screenshot cannot show.
- `image-to-md` skill and `doc-structurer` agent — images to Markdown, extraction on the
  cheap tier and structuring on the deep tier.
- `git-sync` skill and `kit_guard.py` — pull, stage, commit, and push mechanics, with the
  commands that are never run and the reason for each.
- Agents `git-runner`, `ui-cataloguer`, `screenshot-runner` (cheap), `changelog-scribe`,
  `ui-describer`, `test-author` (standard), `bug-fixer`, `doc-writer`, `visual-auditor` (deep).
- Commands `/precommit`, `/docs`, `/visual`, and `/write-tests`.

### Changed

- `project-bootstrap` now states and enforces the non-commit rule: kit files are copied into
  a consuming repository's working directory and never committed there. Exclusion goes in
  `.git/info/exclude`, which is per-clone and untracked, so honouring the rule costs that
  repository no commit of its own.
- `tui-screenshots` hardened for determinism and generalised away from any one terminal,
  capture tool, or operating system; it is now the terminal capture path for `visual-verify`.
- `pdf-to-md` and `office-to-md` now split extraction from structuring across two tiers. The
  halves fail differently: a garbled character is visible, whereas a flattened table or an
  interleaved two-column page reads as plausible text and is noticed only when a quote turns
  out to be wrong.

## [0.1.0] - 2026-07-31

### Added

- Initial extraction of the agents and skills previously duplicated across projects.
- 11 agents, each declaring a vendor-neutral `tier` alongside its runtime binding.
- 12 skills, each self-contained enough to run without subagent support.
- 9 slash commands as thin entry points over the skills.
- Notification and activity-log hooks (`hooks/notify.py`), dependency-free and cross-platform.
- `project-bootstrap` skill for wiring the kit into a new project.
- `changelog-release` skill for changelog maintenance and cutting releases.
- `PORTABILITY.md` documenting what runs outside Claude Code and what has to be adapted.
