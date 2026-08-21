---
name: code-standards
description: Derive the conventions a codebase actually follows — naming, error handling, imports, structure, testing — and write code that matches them, rather than imposing generic best practice. Use before writing code in an unfamiliar repo, when reviewing for consistency, or when asked what a project's conventions are.
---

# Match the project's standards

Establishes how *this* codebase does things, and holds new code to that. The goal is code
that reads as though the person who wrote the surrounding file wrote it too.

This is not a style guide. A style guide says what is good in general; this skill answers what
is normal **here**, which is a question about evidence. Where the two disagree, the codebase
wins — consistency is worth more than any individual convention, because a reader who knows
one file then knows them all.

## Delegation

Collecting examples is mechanical searching. Spawn a subagent with the body of
`../../agents/scoped-search.md` (tier `cheap`) per question, bounded to a subtree, and read
back only its examples. Judging what the pattern *is*, and whether a deviation is deliberate,
stays here.

Without subagents, follow the procedure inline — but sample, do not read the whole tree.

## Step 1 — read the machine-enforced rules first

Anything a tool already enforces is settled, and re-deriving it from source wastes a pass:

`.editorconfig`, linter and formatter configs, `.pre-commit-config.yaml`, the CI workflow,
`CLAUDE.md` or equivalent, and `CONTRIBUTING.md`.

The CI workflow is the most reliable of these, because it is the set of rules that actually
has to pass. A convention documented in `CONTRIBUTING.md` but not enforced anywhere is
frequently aspirational — check it against the code before believing it.

Use the `python-lint` skill for the Python toolchain specifically; this skill covers what
linters cannot see.

## Step 2 — derive what tools cannot enforce

For each question, sample at least three files from different parts of the codebase, and
prefer recently changed ones — `git log` recency is the best available signal of what the
project currently considers normal, as opposed to what it has not got round to changing.

| Question | Look at |
| --- | --- |
| **Naming** | Functions, variables, classes, files, test names. Is it `get_user`, `fetch_user`, or `user()`? Are booleans `is_`/`has_` prefixed? |
| **Errors** | Raise, return an error value, or an option type? Custom exception hierarchy or built-ins? Is anything ever swallowed, and where? |
| **Boundaries** | Where does validation happen — at the edge, or in the core? Are inputs trusted internally? |
| **Imports** | Absolute or relative? Module-level or function-level? Grouped how? |
| **Structure** | Layered by type (`models/`, `views/`) or by feature (`billing/`, `auth/`)? |
| **State** | Dependencies injected, imported directly, or global? Any singletons? |
| **Async** | Sync and async mixed, or separated? What is the convention at the boundary? |
| **Config** | Environment, file, or constants? Where are defaults declared? |
| **Logging** | Structured or free text? What level for what? Any house prefix? |
| **Comments** | Docstring style and when one is expected. What is commented and what is left to read |
| **Tests** | Layout, naming, fixture style — the `test-authoring` skill covers writing them |

## Step 3 — tell a convention from an accident

Three files agreeing is a convention. One file differing is a question, not a licence.

| Signal | Read it as |
| --- | --- |
| The pattern holds across recently touched files | Current convention — follow it |
| Two patterns split cleanly by directory or era | A migration in progress. Find out which direction, then follow the newer one and say so |
| One file differs, and it is old | Legacy. Do not copy it, do not fix it in passing |
| One file differs, and it is new | Ask. It is either the new direction or an oversight, and guessing wrong entrenches the wrong one |
| The codebase is genuinely inconsistent | Match the file you are editing, not the repo average. Local consistency is what a reader actually experiences |

## Step 4 — write to the local pattern

Match the file you are in. Match its comment density: a file with no comments does not want
your explanations, and a heavily documented module expects a docstring.

Do not import a new library to do something the project already does another way. Do not
introduce a new abstraction — a base class, a decorator, a helper module — as part of an
unrelated change. Both are proposals; make them separately, where they can be argued with.

Do not reformat, rename, or restructure code you are only passing through. "While I was in
there" is how a two-line fix becomes an unreviewable diff, and it hides the change that
actually needs review.

## Step 5 — when the convention is genuinely bad

Sometimes the established pattern has a real defect — a bare `except` everywhere, secrets in
config files, a validation gap.

Follow it for the change in hand, and raise it separately. State the pattern, where it is, why
it is a problem, and what it should be. Record it in `ROADMAP.md` or as an issue.

Do not fix it silently in the middle of other work. A cross-cutting change buried in a feature
diff gets approved unread, which is the worst way for a real improvement to land — no one
reviews it, and no one knows it happened.

## Step 6 — record what you derived

If the project has a `CLAUDE.md` or equivalent, add what you established, in the terms of the
`project-bootstrap` skill. Deriving conventions costs a pass over the codebase; writing them
down means the next person, human or otherwise, does not pay it again.

Record only what you verified against code. An aspirational rule in an instructions file gets
the whole file distrusted once someone notices it is not true.

## Do not

- Do not apply a generic best practice over an established local pattern.
- Do not derive a convention from a single file.
- Do not treat documented rules as true without checking them against the code.
- Do not mix a convention fix into an unrelated change.
- Do not add a dependency, abstraction, or file-layout change as a side effect.

## Verify

- [ ] Machine-enforced config was read before anything was derived from source.
- [ ] Every claimed convention rests on at least three files, sampled from different areas.
- [ ] Recently changed files were preferred over old ones as evidence.
- [ ] Where two patterns exist, the direction of travel was established rather than guessed.
- [ ] New code matches the file it lives in, not a repo-wide average.
- [ ] Nothing was reformatted, renamed, or restructured in passing.
- [ ] Any bad convention found was reported separately, not silently fixed.
- [ ] Anything recorded in the instructions file was verified against real code.
