---
name: repo-doc-set
description: The seven canonical documents a repository carries — README.md, PLAN.md, TROUBLESHOOTING.md, DEVELOPMENT.md, ROADMAP.md, AI.md, and ui_glossary.html — what each one owns, what obliges an update, and how to tell it has gone stale. Use whenever documentation is written or refreshed, whenever a change is about to be committed, or when a repository has none of these files yet.
---

# Maintain the repository document set

Keeps seven documents true to the code. Each has one job and one owner; the whole point of
fixing the set is that a fact has exactly one home, so nobody has to decide where to look
and no two files can disagree.

## Delegation

Deciding which facts a diff invalidated, and where they belong, is judgement — use the
`deep` tier. If your runtime supports subagents, spawn one with the body of
`../../agents/doc-writer.md` as its instructions (ignore that file's YAML frontmatter).

Two mechanical pieces can be pushed down to a `cheap` subagent using
`../../agents/scoped-search.md`: enumerating error emission sites for `TROUBLESHOOTING.md`,
and listing tracked files for the `DEVELOPMENT.md` tree. Both are grep-and-report, not
reasoning.

If your runtime has no subagents, follow this skill inline. Nothing here requires
delegation.

## Placement

All seven live at the repository root — **except** when the repo already keeps prose
documentation in a `docs/` directory, in which case everything but `README.md` goes there.
`README.md` is always at the root, because that is the only place a forge renders it.

Decide once per repo by checking whether `docs/` already holds prose. Do not create a
`docs/` directory just to use it; splitting seven files across two conventions is worse than
either convention.

## What each file owns

Overlap is the failure mode. If two files can plausibly hold a fact, it ends up in neither,
or in both where they drift apart and a reader cannot tell which is current.

| Kind of fact | Lives only in |
| --- | --- |
| What the project is, and what a user can do with it | `README.md` |
| Why a shipped thing is built the way it is | `PLAN.md` |
| An error the project emits, and its fix | `TROUBLESHOOTING.md` |
| How to set up, build, test, and edit the project; the file tree | `DEVELOPMENT.md` |
| What is not built or not fixed yet | `ROADMAP.md` |
| How much of this was written by AI, and how to check | `AI.md` |
| What a specific UI element does | `ui_glossary.html` |
| What changed, and in which version | `CHANGELOG.md` (see `changelog-release`) |
| Instructions addressed to an agent | `CLAUDE.md` (not part of the canon) |

When a fact seems to fit two files, the more specific file wins and the other links to it in
one line. Cross-reference; never restate. Restated facts diverge on the first edit that
touches only one copy, and both copies then look authoritative.

## Procedure

1. Read the diff you are documenting — `git diff --staged`, or `git diff <tag>..HEAD` for a
   larger refresh. Work from the diff, not from commit subjects; subjects lie by omission.
2. Route each hunk through the per-file trigger tables below. Note which files are obliged.
3. Edit only those files. Leave the rest untouched.
4. Run the staleness checks for the files you touched, then the verification checklist at
   the end.

Documentation lands in the same commit as the change it describes. Split apart, it is
forgotten, and a doc-only catch-up commit weeks later cannot recover the reasoning.

---

## README.md

**Owns.** Convincing someone deciding whether to use this, then getting a first-time user to
one working result.

**Does not hold.** Architecture, contribution instructions, decision history, the file tree,
the error catalogue, or the roadmap — every one of those has its own file. A README that
tries to be the whole manual stops being read at all, and then the two sentences that
actually mattered go unread with it.

Lead with what it is and what it is for, in two sentences. Then capabilities in user terms —
what the user can now do, not what classes exist. Then install. Then the smallest complete
example that produces a real result, with its real output.

````markdown
# <name>

<One sentence: what it is.> <One sentence: what it is for, and who for.>

## Features

- <a capability, stated as something the user can do>
- <another>

## Install

```bash
<the exact commands, copy-pasteable>
```

## Usage

<The smallest complete example that produces a real result.>

```bash
<command>
```

```text
<its actual output>
```

## Documentation

- Development setup and file structure: `DEVELOPMENT.md`
- Design decisions: `PLAN.md`
- Errors and fixes: `TROUBLESHOOTING.md`
- Pending work: `ROADMAP.md`
- AI use: `AI.md`

## Licence

<licence name and file>
````

| If the diff contains | Then `README.md` must change |
| --- | --- |
| a new user-invocable command, flag, or entry point | the feature list; and the example, if the shortest path to a result moved |
| a renamed or removed capability | the feature list — replace the name, never leave both |
| a change to install steps, package name, or minimum runtime | the Install section |
| a change to what the documented example prints | the shown output |
| a change to a default a first-time user depends on | the usage or configuration text |
| refactors, tests, CI, internal renames | nothing |

**Stale when.** The install command fails on a clean machine; the example's shown output
does not match what the code prints today; a listed feature has no code path behind it; a
shipped capability is missing from the list; a version or badge points below the current tag.

---

## PLAN.md

**Owns.** Why each shipped change was done the way it was — newest first, one entry per
change that involved a real choice.

**Does not hold.** What the change does (that is `README.md` and `CHANGELOG.md`), how to run
anything, or anything not yet built (that is `ROADMAP.md`). It is not a commit log; a file
with an entry per commit is a `git log` that someone has to maintain by hand.

**The test for whether a change earns an entry:** would a competent newcomer reading the
code ask "why is it done this way?" If yes, write one. A typo fix, a formatting pass, a
mechanical rename, or a dependency bump with no behavioural consequence does not.

**Append-only for history.** When a decision is later reversed, never rewrite the old entry.
Add a new entry that supersedes it and links back, and mark the old one superseded. The
reversal reason is the most valuable thing in the file — it is the record that the other
option was tried and what it cost. An entry quietly edited to match current reality is
indistinguishable from an entry that was always right, so the lesson is destroyed.

````markdown
# Plan

Decision log, newest first. One entry per change that involved a real choice.

## YYYY-MM-DD — <the change, in a few words>

**Context.** What forced a decision here — the constraint, failure, or requirement.

**Decision.** What was done.

**Alternatives rejected.**

- <option> — <why not, concretely>

**Consequences.** What this makes harder, what cost was accepted, what to watch for.

**Supersedes.** <date> — <title of the entry this reverses>   <!-- only when reversing -->
````

| If the diff contains | Then `PLAN.md` must change |
| --- | --- |
| a new dependency, or one swapped for another | new entry: why this one, what was rejected |
| a schema, wire format, or on-disk layout change | new entry, including the migration decision |
| a public API, CLI, or config surface change | new entry |
| a fix where the obvious fix was rejected for a subtler one | new entry naming the obvious fix |
| a performance change that trades memory, complexity, or accuracy | new entry with the measured numbers |
| behaviour that reverses what an earlier entry decided | a **new** entry superseding it; the old entry is not edited |
| formatting, typos, test-only changes, mechanical renames | nothing |

**Stale when.** The code contradicts the newest entry covering it; a dependency in the
manifest appears in no entry; the surface has changed across several releases but the newest
entry predates them; or `git log -p -- PLAN.md` shows edits inside old sections rather than
additions at the top, which means a reversal was concealed instead of recorded.

---

## TROUBLESHOOTING.md

**Owns.** One entry per error the project can actually emit, keyed by a stable identifier.

**Does not hold.** General debugging advice, an FAQ, errors emitted by other tools the
project merely invokes (unless it surfaces them as its own), or bugs with no fix yet — an
unfixed bug is a `ROADMAP.md` known bug until there is a remedy to publish.

**Keying.** If the project has stable error codes, key on the code. If it does not, key on
the exact message text as emitted, and recommend introducing codes. The reason is concrete:
message text gets reworded for clarity sooner or later, and every issue link, search result,
and support answer keyed to the old wording rots silently — nobody sees the breakage, users
just stop finding the page.

**Derive the list from the code, not from memory.** Enumerate the emission sites, then check
each one has an entry:

```bash
git grep -nE "raise |throw |panic\(|fmt\.Errorf|log\.(Error|Fatal)|console\.error" -- src
git grep -nE "\b[A-Z]{1,3}[0-9]{3,4}\b" -- src        # only if the project uses codes
```

Adapt the patterns to the language in the repo; the point is to enumerate, not to recall.

````markdown
# Troubleshooting

Every error this project can emit, keyed by <error code | exact message>.

## E014 — configuration file not found

**Message.**

```text
E014: configuration file not found at <path>
```

**When.** The situation that produces it.

**Cause.** What is actually wrong, not what it looks like.

**Fix.** The steps that resolve it.

**Confirm.** The command to run and what a fixed system prints.
````

| If the diff contains | Then `TROUBLESHOOTING.md` must change |
| --- | --- |
| a new error path a user can reach | a new entry |
| reworded message text | the verbatim message block; the identifier stays fixed if codes exist, otherwise keep the old text as an alias line |
| a removed error path | remove the entry, or mark it removed-in-version if that message is already out in the wild |
| a change to the remedy | the Fix and Confirm sections |
| a newly allocated error code | a new entry, plus a check that the code is unique |
| an internal error no user can reach | nothing |

**Stale when.** The grep finds emission sites with no entry; an entry's quoted message does
not string-match any source line; a Fix references a flag, file, or command that no longer
exists; or two entries share an identifier.

---

## DEVELOPMENT.md

**Owns.** Taking someone who has never used this language or toolchain from a clone to a
passing test run and a working edit-run loop — plus the complete file structure.

**Does not hold.** User-facing usage (`README.md`), why things are built as they are
(`PLAN.md`), or user-facing errors (`TROUBLESHOOTING.md`). Conversely, this is the **only**
file that carries a full tree; put one anywhere else and the copies diverge within a week.

Every command must be copy-pasteable and must have been run. Assume no prior knowledge of
the ecosystem: give the version of each prerequisite and the command that proves it is
installed.

````markdown
# Development

## Prerequisites

| Tool | Version | Check |
| --- | --- | --- |
| <runtime> | >= X.Y | `<command> --version` |

## Get the source

```bash
git clone <url>
cd <dir>
```

## Install dependencies

```bash
<command>
```

## Run

```bash
<command>
```

## Test

```bash
<command>
```

## Lint and format

```bash
<commands>
```

## The edit-run loop

<Which files to edit for a typical change, and the one command to run after editing.>

## File structure

```text
<tree, one line of purpose per entry>
```

Regenerate with: `<the command below>`. Generated and vendored directories are collapsed.
````

The tree comes from tracked files, so build output can never leak into it:

```bash
git ls-files | tree --fromfile -F --dirsfirst        # or: git ls-files
```

Collapse generated and vendored directories to a single line with a count —
`node_modules/`, `target/`, `dist/`, `build/`, `.venv/`, `vendor/`. Expanding them buries
the few dozen files a human actually edits, and their contents change without anyone having
decided anything, so an expanded tree is stale on arrival.

| If the diff contains | Then `DEVELOPMENT.md` must change |
| --- | --- |
| a new dependency or a raised minimum version | the Prerequisites table |
| a changed build, test, lint, or run command, or a new task-runner target | the matching block — and re-run it |
| a file or directory added, removed, or renamed | the tree |
| a new environment variable needed for local development | Prerequisites and Run |
| a change to the CI workflow's commands | the local equivalents, because CI is the definition of what must pass |
| edits inside existing files only | nothing |

**Stale when.** Any listed command fails on a clean clone — the check is to run them; the
tree lists a path `git ls-files` does not return, or omits a tracked top-level entry; a
stated prerequisite version is below what the manifest requires; or CI runs a command this
file never mentions.

---

## ROADMAP.md

**Owns.** What is intended but not built, and what is known broken but not fixed.

**Does not hold.** Anything already shipped — that belongs to `CHANGELOG.md` — or the
reasoning behind shipped work, which belongs to `PLAN.md`.

Every item carries a status and a one-line rationale, because a bare list of wishes gives a
reader no way to tell an active commitment from a two-year-old thought.

| Status | Means |
| --- | --- |
| `planned` | agreed, not started |
| `next` | the next thing to be picked up |
| `in progress` | has commits behind it now |
| `blocked` | waiting on something — name it in the rationale |

Items leave only by being shipped or explicitly abandoned. An abandoned item moves to
**Dropped** with a date and a reason; a roadmap item that silently vanishes reads as an
oversight, and someone re-proposes it within the year.

````markdown
# Roadmap

## Pending features

| Item | Status | Why |
| --- | --- | --- |
| <feature> | planned | <one line: what it unlocks> |

## Known bugs

| Item | Status | Why it matters |
| --- | --- | --- |
| <symptom, as a user sees it> | blocked | <impact, and what blocks the fix> |

## Dropped

- <item> — dropped YYYY-MM-DD: <reason>
````

`ROADMAP.html`, if the project publishes one, is **generated** from `ROADMAP.md` and carries
a banner saying so — both an HTML comment and a line visible on the rendered page, since a
comment is invisible to whoever opens it in a browser and starts typing:

```html
<!-- Generated from ROADMAP.md on YYYY-MM-DD. Do not edit by hand. -->
```

Never hand-edit it. A hand-edited generated file is guaranteed to diverge at the next
regeneration, and the edit is lost with no trace of what it said.

| If the diff contains | Then `ROADMAP.md` must change |
| --- | --- |
| an implementation of a pending item | remove the row; the entry now belongs to `CHANGELOG.md` |
| a fix for a listed known bug | remove the row; add the error to `TROUBLESHOOTING.md` if a user can still hit it |
| a bug found but not fixed here | a new Known bugs row |
| a decision not to build a listed item | move it to Dropped, with a date and a reason |
| partial work on a listed item | a status change — not a removal |
| any edit to `ROADMAP.md` while `ROADMAP.html` exists | regenerate the HTML in the same commit |

**Stale when.** An item is pending but the code already implements it; the HTML's generated
date is older than the last commit touching the Markdown; `git log -p -- ROADMAP.md` shows
an item deleted with no Dropped entry and no shipping commit; or an `in progress` item has
had no commits behind it since before the last release.

---

## AI.md

**Owns.** The declaration of AI use in this project, its level, and the commands that verify
the numbers it states.

Do not write it from here and do not restate its rules here. Follow
`../../skills/ai-disclosure/SKILL.md`, which owns the format, the levels, and the
verification commands.

| If the diff contains | Then `AI.md` must change |
| --- | --- |
| work whose authorship split differs from what the file claims | the stated numbers, via the `ai-disclosure` skill |
| a change to which tools or agents produce code here | the declaration of how AI is used |
| no change in how the code was produced | nothing |

**Stale when.** Running the verification commands printed in the file returns numbers that
differ from the ones it states.

---

## ui_glossary.html

**Owns.** Every element of the user interface and what it does.

Do not write it from here. Follow `../../skills/ui-glossary/SKILL.md`, which owns the format
and the cataloguing procedure.

**The condition that decides whether the project needs one:** does a person operate an
interface directly — a GUI, a web page, a TUI screen, or an interactive CLI with panes,
menus, or prompts? If yes, the project needs one. A non-interactive CLI does not: its flags
are already discoverable from `--help` and documented in `README.md`, whereas the meaning of
a button or a pane is discoverable from neither.

---

## Bootstrapping a repository that has none of these

Create them in this order. Each step is derivable from what the previous ones settled, so
working in order means never guessing:

1. **`README.md`** — what the project is. Everything else refers back to it.
2. **`DEVELOPMENT.md`** — from the manifests, task runner, and CI workflow. Run every
   command as you write it; this also proves the README install steps.
3. **`TROUBLESHOOTING.md`** — from the grep over emission sites. Purely derived.
4. **`ROADMAP.md`** — from open issues, `TODO`/`FIXME` comments, and the user. Record only
   what someone actually intends; do not promote every `TODO` into a commitment.
5. **`PLAN.md`** — last of the prose, because it is the only file that cannot be derived
   from the current tree.
6. **`AI.md`** and **`ui_glossary.html`** — via their own skills, and the glossary only if
   the UI condition holds.

**Never fabricate history.** Do not reconstruct decisions from the diff, and do not infer why
a past author chose something. An invented `PLAN.md` entry is worse than an absent one: it is
indistinguishable from a real one later, and it will be cited to justify keeping a choice
nobody ever made. Seed the file and start from today instead:

```markdown
## 2026-03-14 — Decision log started

**Context.** The repository had no decision log.

**Decision.** Record decisions from this date forward. Earlier decisions are not
reconstructed; see the commit history.
```

Anything a past decision genuinely needs — a rejected alternative, a constraint — can be
added later by whoever actually knows it. Ask the user; do not supply it yourself.

## Relationship to `project-bootstrap` and `CLAUDE.md`

`project-bootstrap` runs once per repository and wires the kit in. This skill runs whenever a
change obliges a document. They do not overlap.

`CLAUDE.md` is instructions for an agent: terse, loaded into every session, and paying for
its length every time. The canon is documentation for humans, read on demand. **Do not merge
them**, and do not turn `CLAUDE.md` into a table of contents for the canon — that is length
in every session buying nothing.

Where they genuinely overlap — build and test commands appear in both, because an agent
needs them inline and a newcomer needs them explained — the strings must be identical. Check
them as a pair whenever either changes; a drifted pair is worse than either file alone,
because one of them is now confidently wrong.

`CHANGELOG.md` is not part of the canon either. It is maintained by `changelog-release`:
`CHANGELOG.md` says what changed and when, `PLAN.md` says why it was done that way.

## Do not

- Do not create a file because the canon lists it. `ui_glossary.html` only under its
  condition; `docs/` only if the repo already uses one.
- Do not write the same fact into two files. Link to the owner instead, in one line.
- Do not paste a file tree into anything except `DEVELOPMENT.md`.
- Do not hand-edit `ROADMAP.html` or any other generated file — regenerate it.
- Do not edit a past `PLAN.md` entry, even to correct it. Supersede it.
- Do not invent history, benchmark numbers, versions, or commands you have not run.
- Do not rewrite documentation the diff did not oblige. An unrelated rewrite buries the real
  change in the diff and makes review useless, so the real change goes unreviewed.
- Do not leave a `TODO` in a canon file. Unfinished work goes in `ROADMAP.md`, where it has a
  status and a rationale.
- Do not commit documentation separately from the change it describes.

## Verify

- [ ] Every file the diff obliged has been updated; every file it did not oblige is untouched.
- [ ] No fact appears in two files; each overlap is a one-line cross-reference to the owner.
- [ ] Every command in `README.md` and `DEVELOPMENT.md` was run in this session and succeeded.
- [ ] The `DEVELOPMENT.md` tree matches `git ls-files`, with generated directories collapsed.
- [ ] Every `TROUBLESHOOTING.md` entry quotes a message that string-matches a real emission
      site, and every emission site found by grep has an entry.
- [ ] Any new `PLAN.md` entry names a rejected alternative and an accepted consequence, and
      `git diff -- PLAN.md` shows additions at the top only.
- [ ] `ROADMAP.md` items were removed only because they shipped or moved to Dropped with a
      reason and a date.
- [ ] `ROADMAP.html` was regenerated if the Markdown changed, and carries its banner.
- [ ] Files are in the correct location: root, or `docs/` for everything but `README.md`.
- [ ] Nothing was fabricated — no invented history, numbers, or unverified commands.
- [ ] The Markdown lints clean under the `markdown-mermaid` skill's ruleset.
