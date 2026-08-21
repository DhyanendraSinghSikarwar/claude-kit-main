---
name: pre-commit-gate
description: The ritual that runs before every commit — sync, run the full test suite, fix what it finds, re-test, refresh the documentation, write the changelog entry, then commit and push. Use whenever the user asks to commit, push, "ship this", or wrap up a piece of work, and before any commit that touches code.
---

# Run the pre-commit gate

Produces one commit that contains the code, the documentation that describes it, and the
changelog entry for it — or a named refusal to commit. The gate is what makes "it is
committed" mean "it was tested, and the docs match".

## Delegation

Each stage names the agent that owns it. If your runtime supports subagents, spawn each one
with the body of the named file as its instructions (ignore that file's YAML frontmatter —
it is packaging metadata, the prose below it is the prompt).

| Stage | Agent | Tier | Why that tier |
| --- | --- | --- | --- |
| Sync, commit, push | `../../agents/git-runner.md` | cheap | Fixed command sequences, fixed report shape, no judgement |
| Test | `../../agents/test-runner.md` | cheap | Toolchain detection and command running |
| Summarise | `../../agents/test-summarizer.md` | cheap | Parsing output into a table |
| Triage and fix | `../../agents/bug-fixer.md` | deep | Root-cause reasoning — where a wrong answer costs most |
| Capture | `../../agents/screenshot-runner.md` | cheap | Running a capture harness to a fixed recipe |
| Describe | `../../agents/ui-describer.md` | standard | Writing down what is on screen, precisely |
| Audit the interface | `../../agents/visual-auditor.md` | deep | Judging a design against what was promised |
| Document | `../../agents/doc-writer.md` | deep | Must judge what changed in meaning, not just in text |
| Changelog | `../../agents/changelog-scribe.md` | standard | Writing with judgement from an established diff |

If your runtime has no subagents, run every stage inline yourself, in the same order, to the
same rules. The procedure below is complete on its own; delegation keeps token-heavy work
out of the main context and changes nothing else.

### Cost discipline

Delegation is not only about capability, it is about what enters the main context and stays
there. The gate reads a lot and needs to keep almost none of it.

| Never pull into the main context | Keep instead |
| --- | --- |
| Raw test output, build logs, stack traces | The failure table from `test-summarizer` — counts plus one row per root cause |
| The full diff, when you only need to know what it touched | `git diff --name-only` and `--stat`; read hunks only for files you must judge |
| Screenshots and their descriptions | The audit's findings list |
| Whole source files read while diagnosing | The one mechanism sentence the fix rests on |

Two rules follow, and both are about the same failure. First, do not re-read what a subagent
already reduced — reading the raw log after receiving the summary spends the tokens the
delegation just saved, and leaves you reasoning from the noisier copy. Second, pass forward
only the reduced form: give `bug-fixer` the failure table and the classification, not the
scrollback it came from.

The stage tiers exist for the same reason. A cheap model running a test suite costs a
fraction of a deep model doing it, and the work is identical because there is no judgement in
it. Spend the deep tier only where a wrong answer is expensive — root cause, meaning, and
design.

## The pipeline

Run the stages in this order. The order is the point — each stage's output is the next
stage's input, and skipping one silently invalidates everything after it.

| # | Stage | Tier | Owner | Output |
| --- | --- | --- | --- | --- |
| 0 | Sync | cheap | `git-sync` skill via `git-runner` | Branch up to date with its remote |
| 1 | Test | cheap | `test-runner`, then `test-summarizer` | Failure table plus counts |
| 2 | Triage | deep | `bug-fixer` | Each failure classified by root cause |
| 3 | Countermeasures | deep | `bug-fixer` | One minimal correct fix per root cause |
| 4 | Re-test | cheap | `test-runner` | Full-suite result, not just the fixed subset |
| 5 | Verify the interface | mixed | `visual-verify` skill | Findings fixed, or none — skipped where there is no UI |
| 6 | Document | deep | `repo-doc-set` skill via `doc-writer` | The document canon refreshed |
| 7 | Changelog | standard | `changelog-scribe` | One entry under `Unreleased` |
| 8 | Commit and push | cheap | `git-sync` skill via `git-runner` | One commit, pushed |

## Terminal states

The gate ends in exactly one of three states, and you must name it on its own line. A run
that trails off without a verdict leaves the user unsure whether their work is committed,
which is the one thing this skill exists to make certain.

| State | Means | Ends with |
| --- | --- | --- |
| **GREEN** | Suite passes, docs and changelog updated, one commit made and pushed | The commit sha |
| **BLOCKED** | Something needs a human decision — a surviving failure, a merge conflict, a test that may itself be wrong | The question, stated so it can be answered yes or no |
| **DIRTY-STOP** | Work is deliberately left uncommitted — secrets in the diff, unrelated changes that should be split, the user said stop | What is uncommitted, and why |

BLOCKED and DIRTY-STOP are successful outcomes for this skill. Not committing is a decision
the gate is allowed to make; committing something broken is not.

## Scope — full form or short form

The full ritual is heavy. Decide which form to run from the **diff**, not from the commit
message or the user's description — a change described as "just docs" routinely carries a
code hunk, and the message is written after the fact by the same person who is wrong about
what they changed.

```bash
git diff --name-only HEAD
git diff --stat HEAD
git diff -U0 HEAD          # to judge whether a source file changed only in comments
git ls-files --others --exclude-standard   # new files, invisible to git diff until staged
```

Read both lists. `git diff HEAD` sees a new file only once it has been staged, so an unstaged
new file appears in none of the first three commands. A change made entirely of new source
files — a new module, a new test, a new CI workflow — would otherwise produce an empty
diff, match the prose-only row below, and skip the testing this gate exists to force.

| Diff or untracked set touches | Form | Stages |
| --- | --- | --- |
| Any source, config, dependency manifest, CI workflow, or test file | Full | 0-8 |
| Only Markdown, images, or other prose assets | Short | 0, 6, 7, 8 |
| Only comments, docstrings, or whitespace in source files | Short | 0, 6, 7, 8 |
| Nothing at all in either list | Stop | None — **DIRTY-STOP**, there is nothing to commit |

In the short form, mark stages 1-5 in the report as `skipped — docs-only diff` and name the
files that justified the call. An unexplained skip is indistinguishable from a forgotten
stage.

Anything mixed is a full run. A single behavioural line in a docs-heavy diff is exactly the
change most likely to slip through untested.

## Stage 0 — sync (cheap)

Bring the branch up to date before doing any work, following the `git-sync` skill. Testing
against a stale base wastes the whole run: you debug failures upstream already fixed, or you
miss a conflict that only appears once the merge lands.

Confirm before continuing:

- The working tree state is known (`git status --short`) and nothing unexpected is staged.
- The current branch is not the default branch, or the user has said they intend to commit
  directly to it.
- The fetch succeeded. If the repo has no remote, say so once and carry on — a local-only
  repo is normal; a fetch that failed silently is not.
- `AI.md`'s figures still match the pre-commit `HEAD` — run
  `python3 <kit>/skills/ai-disclosure/scripts/ai_census.py --check`. A non-zero exit means the
  block drifted while other commits landed; refresh it in stage 6, stamped with this `HEAD`.
  This is the only stage that recomputes it, so a check deferred here is a check never made.

If the sync produced conflicts, stop at **BLOCKED**. Resolving someone else's merge conflict
is a human decision, and guessing at it corrupts both sides of the merge.

## Stage 1 — test (cheap)

Run the **full** suite via `test-runner`, then compress the output via `test-summarizer` or
the `test-summary` skill. Run everything, not the tests you believe are relevant — at this
point you have not yet established what the change touched.

If the run produces a raw log rather than a structured report, reduce it with the
`log-triage` skill before reading it.

### Errors before failures

Separate infrastructure errors from real test failures, and clear the errors first.

| Symptom | Class | Do |
| --- | --- | --- |
| `ModuleNotFoundError`, `cannot find package`, missing binary | Missing dependency | Install it via the project's own manifest, then re-run |
| Connection refused, DNS failure, timeout to a host | No network or service | Report it; do not stub the service out to reach green |
| `KeyError` on an env var, missing credential | Unset environment | Report which variable; never invent a value |
| Collection or import error before any test ran | Broken test bootstrap | Fix it first; it masks everything behind it |

An error means tests did not run, so the failure count is a floor rather than a result.
Reporting "3 failures" when 200 tests never executed is worse than reporting nothing,
because the number reads as complete.

### If there is no test suite

Say so plainly in one line, and do not fabricate one. Writing tests is separate work with
its own review, and tests invented mid-commit assert whatever the code currently does, which
locks in the bug you have not found yet. Instead:

1. Run whatever verification does exist — linter, formatter check, type checker, a build.
   Take the commands from the CI config first, because those are the ones that actually have
   to pass.
2. Record the absence once in `ROADMAP.md` under `## Pending features` — one of the three
   headings `repo-doc-set` defines, and the one that owns what is not built yet. A project
   with no tests is a roadmap item in its own right, not a footnote in a commit message.
3. Continue at stage 5, and mark stages 1-4 as `n/a — no suite` in the report.

Offer the `test-authoring` skill as the follow-up, as its own piece of work with its own
review. That skill exists precisely so the suite is written when someone is thinking about
what should be true, rather than while a commit is waiting on it.

The same applies when the suite exists but the fix in stage 3 had no test covering it: a bug
that reached the code once can reach it again, and the regression test is the only artefact
that stops it. Note it for follow-up rather than writing it here — mid-gate is the one moment
the test is guaranteed to be written against the fixed code, where it cannot be seen failing
and so proves nothing.

## Stage 2 — triage (deep)

Classify every distinct failure by root cause before changing a single line. Failures that
share an exception type and a failing line are one problem, not N — one broken fixture can
fail fifty tests, and fixing them one at a time produces fifty wrong fixes.

### Caused by this change, or already red

Establish whether each failure was caused by this change or was already red on the base. Get
the answer by running the suite at the merge base, not by reasoning about the diff — the
whole reason the failure is confusing is that your model of the change is incomplete.

```bash
default=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD)   # e.g. origin/main
base=$(git merge-base HEAD "$default")
git worktree add ../gate-base "$base"
# run the same suite command with the same flags inside ../gate-base
git worktree remove ../gate-base
```

Detect the default branch rather than writing `main` into the first line. Plenty of
repositories are on `master`, `trunk`, or `develop`, and a merge base taken against a branch
that does not exist either errors or silently compares against the wrong history. If the
first command prints nothing the remote `HEAD` is not cached — repair it as `git-sync`
step 2 prescribes, and do not guess.

Use a worktree rather than `git stash` plus `git checkout`. Stashing and restoring around a
build is the step most likely to lose uncommitted work. The cost is that some toolchains
need their dependencies installed again in the new worktree; pay it, or say you could not.

| Result at the merge base | Classification | Do |
| --- | --- | --- |
| The test passes | Caused by this change | Fix it in this commit |
| The test fails identically | Pre-existing | Report it; do not fix it |
| The test errors, or the base does not build | Unknown | Report as unknown, and say the base could not be evaluated |

A pre-existing failure is reported, not fixed, unless the user asks for it. Folding an
unrelated fix into this commit makes the diff unreviewable — the reviewer can no longer tell
which hunk belongs to the feature and which was a drive-by, so they either approve both
unread or reject both.

### Flaky tests

A test that passes on a plain re-run with no code change in between is flaky. Re-run once,
never more: a test re-run until it goes green has been silenced by attrition rather than
fixed, and the next person inherits a suite whose result depends on how many times you ran
it.

Name the flake explicitly in the report — `flaky: passed on re-run, no code change` — so it
stays visible instead of being absorbed into the pass count, and record it in `ROADMAP.md`
as a known bug.

Never fix flakiness by adding a `sleep`, a retry wrapper, or a longer timeout to the test.
That converts an intermittent failure into a slower intermittent failure and hides the race
condition that is the actual defect.

## Stage 3 — countermeasures (deep)

One fix per root cause, at the root, minimal. Give `bug-fixer` the failure evidence and the
classification from stage 2, not a request to "make the tests pass" — the second phrasing
invites the forbidden countermeasures below.

Fix the cause, not the symptom. If the assertion is failing because a value arrives `None`,
the fix belongs where the `None` originates, not in a guard at the assertion site; a guard
at the call site leaves every other caller broken.

### Forbidden countermeasures

None of these is ever an acceptable way to reach green. Reaching green by lowering the bar
is worse than reporting red, because red is recoverable and a lowered bar is permanent —
nobody ever raises it back, and the signal the test was carrying is gone for good.

| Never | Because |
| --- | --- |
| Delete a failing test | It is the only record of a requirement, and deleting it deletes the requirement |
| Skip, `xfail`, `.skip`, or `#[ignore]` a failing test | Green with a skip reads identically to green without one in CI |
| Loosen an assertion until it passes | The assertion was the specification; loosening it rewrites the spec to match the bug |
| Widen a numeric tolerance | It swallows a real difference along with the noise, and the next drift is invisible |
| Catch and discard the exception the test was written to detect | The failure still happens; only the evidence is gone |
| Change the expected value to the observed value | This is the same act as deleting the test, with extra steps |
| Commit with `--no-verify` or another bypass flag | The hook exists because someone was burned by exactly this |
| Mock out the unit under test | The test now asserts that the mock works |

If a test is genuinely wrong — it encodes behaviour the project has deliberately changed —
editing it is legitimate, but it is a **user decision**, not yours. State the test, its old
expectation, the proposed new one, and the change that justifies it, then stop at
**BLOCKED**.

### Evidence per fix

A fix is not finished until both of these are true and stated in the report:

1. The test that failed now passes — named, with the command that proves it.
2. The rest of the suite still passes, from stage 4, not from a spot check.

Without the second you have traded one known failure for an unknown number of unknown ones,
which is a worse position than the one you started in.

## Stage 4 — re-test (cheap)

Run the **full** suite again, not just the failing subset. A fix that satisfies its own test
while breaking a neighbour is the most common way a gate like this ships a regression, and a
targeted re-run is structurally incapable of seeing it.

### The three-round cap

| Round | Do |
| --- | --- |
| 1 | Triage, fix, re-test |
| 2 | Triage, fix, re-test |
| 3 | Triage, fix, re-test |
| 4 | Stop. Report the surviving failures and hand back at **BLOCKED** |

Three is the cap because a bug that survives three considered fixes is a bug you have not
understood, and an unbounded repair loop burns budget while making the diff steadily worse.
By round four the change usually contains more speculative edits than the original defect was
worth, and unpicking them costs more than the fix would have.

On the fourth round, hand back with: the failures still red, every fix attempted and why each
was rejected by the suite, and the single question whose answer would unblock it.

### Loop detection

If the same test fails twice with a *different* fix each time, your model of the bug is
wrong. Stop generating fixes. Re-read the code path from its entry point — the actual call
sequence, not the file you assume is responsible — and only propose again once you can state
what the code does differently from what you thought. A third guess at the same test is no
more likely to be right than the second was, because nothing was learned between them.

Say in the report that this happened and what re-reading the path changed, because a wrong
model that was corrected is the most useful thing the gate can tell the next reader.

## Stage 5 — verify the interface (mixed tiers)

Only where the project has a user interface *and* this change touched it. Skip it otherwise
and say so; running a capture pass over an unchanged interface produces screenshots nobody
reads and a diff nobody trusts.

Regenerate `ui_glossary.html` first, via the `ui-glossary` skill. It is derived from source,
which is settled the moment stage 4 is green, and the audit's check 4 reads it as its element
inventory: audited against a glossary that still describes the old interface, every control
this change added reads as undocumented and every one it removed reads as missing from the
screen. Both findings are false. Do this even if the rest of the stage then reports
`n/a — no capture harness`, because stage 6 relies on the glossary being current.

Then follow the `visual-verify` skill. It splits by tier for the same reason the rest of the
gate does: capture is a fixed recipe (cheap), describing what is on screen is careful writing
(standard), and judging whether it is right is the expensive decision (deep).

| Touched | Run |
| --- | --- |
| Templates, components, stylesheets, design tokens, icons | Full visual pass |
| CLI flags, subcommands, help text, terminal output | Full visual pass, via the `tui-screenshots` skill for capture |
| Only logic behind an unchanged interface | Skip — record `skipped — interface unchanged` |
| No interface at all | Skip — record `n/a — no interface` |

The audit checks alignment, colour grading, icon and text legibility, whether the features
the documents promise are actually present and reachable, and whether this change is visible
at all. That last one closes a gap the test suite cannot: a change can pass every test and
still not reach the screen.

Stop at **BLOCKED** for any finding that needs a design or product decision. Fixing a
contrast failure by abandoning the project's palette is not a fix, it is a second bug.

## Stage 6 — document (deep)

Refresh the canonical documents through the `repo-doc-set` skill, delegating to `doc-writer`.
Update only the documents this change actually affects — a gate that rewrites all seven files
on every commit produces diffs nobody reads, which is the same as no documentation.

| The change | Update |
| --- | --- |
| A user-visible capability | `README.md` — `ui_glossary.html` was already refreshed in stage 5 |
| A decision worth remembering, and its rejected alternatives | `PLAN.md` |
| A new error code, message, or failure mode | `TROUBLESHOOTING.md` |
| Build steps, file structure, or local workflow | `DEVELOPMENT.md` |
| A pending item now shipped, or a newly known bug | `ROADMAP.md` |

### AI.md is one commit behind, by design

`AI.md` declares the level of AI involvement and carries the commands that verify its
figures — see the `ai-disclosure` skill. Those figures are computed from git history, so they
describe the repository as of the commit *before* this one. This commit does not exist yet
when they are computed, and cannot be counted in them.

Stamp them rather than chasing them: write the figures with `as of <sha>` beside them, using
the sha of `HEAD` before this commit, and refresh them from the `--check` run made in
stage 0 — that check is what makes "one commit behind" a stamp rather than an excuse for
never refreshing at all. Do not amend a commit to insert statistics about itself — an amend
after a push rewrites published history to correct a number that is stale again by the
following commit.

### Same commit as the code

Documentation and the changelog entry go in the **same** commit as the code they describe.
A documentation commit that trails the code leaves the docs wrong for the length of the gap,
and anyone who checks out a sha in between gets a repository that lies about itself. It also
keeps `git revert` honest: reverting the change reverts its documentation with it.

## Stage 7 — changelog (standard)

One entry under `## [Unreleased]`, drafted by `changelog-scribe` from two sources — the diff
for what changed, and `PLAN.md` for why it was done that way. Follow the `changelog-release`
skill for the file's format and section rules rather than restating or improvising them.

`changelog-scribe` has read access only. It returns the heading and the lines that belong
under it; **you** apply them to `CHANGELOG.md` under `## [Unreleased]` yourself, and stage
the file in stage 8. No other stage writes that file — `doc-writer` is forbidden from
touching it and `git-runner` only stages the paths it is given — so an entry left sitting in
the agent's reply never reaches the commit.

Skip the entry when the change is invisible to a user: a pure refactor, a formatting pass, a
test-only change. A changelog that lists every commit is a `git log` with extra steps. Say in
the report that you skipped it and why, so the omission reads as a decision rather than an
oversight.

Writing the entry is not cutting a release. Do not bump a version or tag anything here.

## Stage 8 — commit and push (cheap)

Follow the `git-sync` skill for the mechanics and the `commit-draft` skill for the message.
Delegate the plumbing to `git-runner`.

Before staging, read the diff once more for what must never be committed: credentials,
tokens, `.env` files, large binaries, generated output, and absolute paths from your machine.
Stop at **DIRTY-STOP** if you find any and say exactly which file — a secret that reaches a
remote must be rotated, not deleted, so catching it here is worth the interruption.

### Kit files are never committed here

Skills and agents copied from the kit belong in the working directory of this project and in
the kit's own history — never in this project's. Check before every commit, because the
mistake is made by someone acting reasonably: a skill was edited to fix something, and
committing an edited file is the obvious next move.

```bash
python3 <kit>/skills/git-sync/scripts/kit_guard.py --staged
```

A non-zero exit means kit files are staged. Unstage them and commit the rest — stop at
**DIRTY-STOP** if that leaves nothing to commit. Improvements to a skill go back to the kit
as their own commit there, which is also the only way anyone else ever receives them.

The temporary artefacts this gate produces — screenshots, their descriptions, census output —
are working files and are excluded alongside the kit, for the same reason: they describe one
run, and a repository that carries them accumulates a record nobody maintains.

Stage deliberately. `git add -A` sweeps in whatever else happened to be in the tree — build
output, a scratch file, an unrelated experiment — and those become part of your commit
whether you looked at them or not.

Push to the branch the user is on. If the push is rejected because the remote moved, run
stage 0 again and push once more. If that second push is also rejected, stop at **BLOCKED**
with the remote's message verbatim — the branch is moving faster than you are, and a third
attempt is a fetch-push loop. Never force-push to resolve it: a force-push discards whatever
the other side pushed in between, and that work is usually not recoverable from your clone.

## Report

End every run with this table, then the terminal state on its own line. Keep it compact — the
detail belongs in the stage output above, not repeated here.

```markdown
| Stage | Tier | Outcome |
| --- | --- | --- |
| 0 Sync | cheap | Up to date with `origin/main`, 3 commits pulled |
| 1 Test | cheap | 412 passed, 2 failed, 1 error |
| 2 Triage | deep | 1 root cause from this change, 1 pre-existing, 1 flaky |
| 3 Countermeasures | deep | 1 fix in `src/parser/date.py` |
| 4 Re-test | cheap | 414 passed, 0 failed — round 1 of 3 |
| 5 Interface | mixed | 6 states captured, 1 contrast finding fixed |
| 6 Document | deep | `README.md`, `TROUBLESHOOTING.md` updated |
| 7 Changelog | standard | 1 entry under Unreleased |
| 8 Commit | cheap | `a1b2c3d` pushed to `feature/date-parsing` |

**GREEN** — committed as `a1b2c3d`.

Carried forward:
- `test_timezone_dst` fails at the merge base too — pre-existing, not fixed.
- `test_upload_retry` passed on re-run with no code change — flaky, logged in ROADMAP.md.
```

Every stage gets a row, including the ones that did not run: write `skipped — docs-only diff`
or `n/a — no suite` with the reason. Anything a human still has to decide goes under
`Carried forward`, because a fact buried in stage output is a fact nobody acts on.

## Do not

- Do not commit first and run the gate afterwards. The gate exists to decide whether to
  commit, and run after the fact it is a report rather than a gate.
- Do not run the stages out of order or in parallel. Documenting before the fix is settled
  documents the wrong behaviour, and the changelog cannot describe a diff that is still moving.
- Do not fix a pre-existing failure, tidy nearby code, or rename anything you happened to read
  while fixing. "While I was in there" is how a two-line fix becomes an unreviewable diff.
- Do not amend or force-push to make the history tidier. Tidy history is worth less than
  history someone else can still pull.
- Do not cut a release, bump a version, or tag. That is the `changelog-release` skill's job,
  and `release-validator` runs before it.
- Do not report GREEN when a stage was skipped, a test was silenced, or a failure was left
  red. GREEN is a claim about the whole pipeline, and one false GREEN costs the gate all of
  its remaining credibility.

## Verify

- [ ] The full suite ran end to end at least once, and its counts appear in the report.
- [ ] Every failure is classified: caused by this change, pre-existing, flaky, or
      infrastructure.
- [ ] Infrastructure errors were cleared or reported before any failure count was trusted.
- [ ] Every fix names the test that now passes and the full-suite run confirming nothing else
      broke.
- [ ] No test was deleted, skipped, xfail-ed, or loosened, no tolerance widened, and no
      exception swallowed.
- [ ] The fix loop ran at most three rounds.
- [ ] The interface was captured and audited, or the skip is recorded with its reason.
- [ ] No kit file is staged — `kit_guard.py --staged` exits zero.
- [ ] No raw log, full diff, or screenshot was carried in the main context once a reduced
      form of it existed.
- [ ] Documentation and the changelog entry are in the same commit as the code.
- [ ] `AI.md`'s figures carry an `as of <sha>` stamp and no commit was amended to update them.
- [ ] The commit message traces to the diff, and no verification hook was bypassed.
- [ ] Nothing secret, generated, or unrelated was staged.
- [ ] The report ends with exactly one of GREEN, BLOCKED, or DIRTY-STOP.
