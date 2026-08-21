---
name: ai-disclosure
description: Create and maintain AI.md — the declaration of how much of a repository was written with AI assistance, at what level, and the commands that reproduce every number it states. Use whenever AI.md is written, refreshed, or checked for staleness, or when the user asks how much of a project was AI-written.
---

# Declare AI use, with the numbers to check it

Produces `AI.md`: one declared level, the measured figures behind it, and the exact commands
that reproduce those figures. The file lives at the repository root, or in `docs/` if the
repo already keeps its prose documentation there — see `../../skills/repo-doc-set/SKILL.md`
for the placement rule.

## Recomputable, or it is not a disclosure

A disclosure a third party cannot recompute is a marketing claim. "Mostly human-written",
"AI-assisted throughout", "written with AI help" are all unfalsifiable: nobody can check
them, so they carry no information and cost nothing to say.

So the rule for this file is absolute. **Every number in `AI.md` is printed next to the
command that produced it, and re-running that command reproduces it.** A figure that no
command can produce does not belong in the file — either find a way to measure it or delete
it. A sentence that sounds like a measurement but is not one ("the majority of the parser
was hand-written") is worse than saying nothing, because it borrows the credibility of the
figures beside it.

## Delegation

Counting is mechanical: run commands, sum columns, divide. If your runtime supports
subagents, spawn one with the body of `../../agents/git-runner.md` as its instructions
(ignore that file's YAML frontmatter), have it run the census below, and take back only the
numbers. Tier `cheap` — no judgement is involved, and the raw `git log --numstat` output for
a mature repo is thousands of lines you do not want in the main context.

Choosing the level and writing the prose stay here. They are short, and they are the only
part of this file where being wrong matters.

If your runtime has no subagents, run the commands yourself. Nothing here requires
delegation.

## The level scale

One level is declared per repository, in the first line of `AI.md`.

| Level | Name | What it asserts | Typical surviving AI share |
| --- | --- | --- | --- |
| `L0` | None | No AI involvement in authored content. | 0% |
| `L1` | Assisted | AI used for completion, search, or explanation. A human wrote the code. | 0% — see below |
| `L2` | Co-authored | AI drafted substantial parts; a human directed, reviewed, and edited. | roughly 20–60% |
| `L3` | AI-generated | AI produced most content; a human specified, reviewed, and accepted it. | roughly 60–90% |
| `L4` | Autonomous | AI planned and produced the change; review happened after the fact. | above 90% |

The share column is a sanity check, not the definition. The definition is **who drafted and
who directed**. Where the band and the process disagree — a repo where AI drafted almost
everything but a human rewrote most of it before commit — the process wins, and you say so
in the file with both numbers visible. Silently picking whichever of the two reads better is
the failure this whole document exists to prevent.

`L0` and `L1` are indistinguishable in the numbers, because completion, search, and
explanation produce no committed AI-drafted content and therefore leave no trailer. That is
precisely why the level is a stated claim and the figures are a check on it, rather than the
figures being the disclosure on their own.

**Per area.** Declare an area's own level only where it genuinely differs from the
repository — a full level apart, in an area large enough to matter. Compute its figures with
the same commands and a narrower pathspec. Do not split a repo into eight areas: an area
table is an excellent place to hide a headline, and a reader who has to average five rows
learns less than one who reads one number.

## Attribution is the commit trailer

One marker decides whether a commit counts as AI-assisted: a `Co-Authored-By:` trailer
naming a non-human author, in the standard git trailer block at the end of the message.

```text
fix(parser): reject timestamps without a timezone

Co-Authored-By: <the assistant identity your tooling writes> <address>
```

Why the trailer, and not commit-message prose or a subject prefix:

- **It is machine-readable.** One line, fixed position, exact string. `git log --grep` finds
  it without guessing at phrasing, so two people counting get the same answer.
- **It survives history rewriting.** The trailer is part of the commit message, so it
  travels through rebase, cherry-pick, and amend, and forges carry it into squashed merge
  messages. A convention that lives anywhere else — a branch name, a PR label, a notes ref —
  is gone the first time history is rewritten, and takes the disclosure with it.
- **It already exists.** Co-authorship trailers are understood by every forge, so nothing
  bespoke has to be built or maintained for the count to work.

Record the exact pattern you match on in `AI.md`. The figures are only reproducible if the
reader greps for the same string you did.

## The figures, and what produces them

`AI.md` carries these five. Nothing else is required, and a sixth figure needs a reason.

| Figure | Answers | Distorted by |
| --- | --- | --- |
| Total commits | The denominator. | Merge commits, which author nothing — excluded. |
| AI-assisted commits, and their share | How often AI was involved. | Commit size varies enormously; this counts events, not content. |
| Lines added and removed in AI-assisted commits | How much text those commits moved. | Generated files, reformatting, and churn — a line written then rewritten counts twice. |
| Lines added and removed across all commits | The denominator for the above. | The same. |
| **Surviving-blame share** | Of the lines in the tree right now, what fraction traces to an AI-assisted commit. | Move and copy detection, so the blame flags must be declared. |

**The surviving-blame share is the honest headline; lead with it.** Added-line counts reward
volume and cannot tell whether a line still exists: a generated file, a vendored dependency,
or a write-then-rewrite loop inflates them, and a commit that added 4,000 lines and deleted
3,900 looks identical to one that shipped 4,000. Blame measures what actually survives in
the tree someone is running today. Print the added and removed pair underneath it anyway, so
a reader can see the churn gap for themselves rather than taking your word that it is small.

## The commands

These need nothing installed beyond git and awk, so the disclosure is verifiable by anyone
who can clone the repo.

```bash
# The marker. Replace with the identity your tooling actually writes, and put the same
# string in AI.md — the count is only reproducible if the reader greps for what you grepped.
AI='Co-Authored-By: <the assistant identity your tooling writes>'

# The exclusions. Same list as AI.md states, in the same order.
EX=(':(exclude)package-lock.json' ':(exclude)*.lock' ':(exclude)vendor/**'
    ':(exclude)dist/**' ':(exclude)**/*.generated.*')

# 1. Total commits.
git rev-list --count --no-merges HEAD -- . "${EX[@]}"

# 2. AI-assisted commits. Add -F if the marker contains regex metacharacters.
git log --no-merges -i --grep="$AI" --format=%H -- . "${EX[@]}" | wc -l

# 3. Lines added and removed — AI-assisted commits, then all commits.
git log --no-merges -i --grep="$AI" --numstat --format='' -- . "${EX[@]}" \
  | awk '$1 ~ /^[0-9]+$/ { add += $1; del += $2 } END { print "+" add, "-" del }'

git log --no-merges --numstat --format='' -- . "${EX[@]}" \
  | awk '$1 ~ /^[0-9]+$/ { add += $1; del += $2 } END { print "+" add, "-" del }'

# 4. Surviving-blame share. Blame every tracked line, then look each line's commit up in
#    the set of AI-assisted commits.
shas=$(mktemp); lines=$(mktemp)

git log --no-merges -i --grep="$AI" --format=%H | sort -u > "$shas"

git ls-files -- . "${EX[@]}" | while IFS= read -r f; do
  git blame --line-porcelain --no-progress -- "$f" 2>/dev/null
done | awk '(length($1) == 40 || length($1) == 64) && $2 ~ /^[0-9]+$/ { print $1 }' > "$lines"

awk 'NR == FNR { ai[$1]; next }
     { total++ } $1 in ai { hit++ }
     END { printf "%d of %d surviving lines (%.1f%%)\n", hit, total, 100 * hit / total }' \
  "$shas" "$lines"
```

Notes on the choices above, because each of them changes the answer:

- `--no-merges` everywhere. A merge commit authors no content, and merges are usually made
  by a human pressing a button, so counting them quietly inflates the human side.
- The same pathspec on every command. Mixing an excluded line count with an unexcluded
  commit count produces a share of two different populations, which is not a share.
- `git blame` is run with no `-M` or `-C`. Move and copy detection reattributes moved lines
  to their original commit and can shift the surviving share by tens of points. Either flag
  set is defensible; an undeclared one is not, so state which you used.
- `length($1)` accepts 40 or 64 hex characters, so the roll-up works in both SHA-1 and
  SHA-256 repositories.
- Per-area figures are the same commands with the area's path in place of `.`.

## The counter script

`scripts/ai_census.py`, in this skill's directory, does all of the above in one pass. It is
stdlib-only Python 3 and needs no installation — run it with `python3`.

| Invocation | Does |
| --- | --- |
| `python3 scripts/ai_census.py` | Prints the measured block as Markdown, stamped with `HEAD`, ready to paste into `AI.md`. |
| `python3 scripts/ai_census.py --check` | Recounts, compares against the numbers in `AI.md`, prints any that differ, and exits non-zero if the file is stale. |

It reads the marker and the exclusion list out of `AI.md` itself, so the file being checked
is also the file that defines the check — the numbers and the disclosed method cannot drift
apart.

`--check` is the command to run every turn. It is the cheapest of all the documentation
checks and the only one that catches silent drift, since `AI.md` goes stale by doing nothing
at all while commits land around it.

If the script is not present — a vendored copy of this skill without its `scripts/`
directory — the block above is the whole procedure. Nothing here depends on the script.

## Exclusions

Generated files, vendored dependencies, and lockfiles distort every one of these figures,
usually by thousands of lines attributed to whoever ran a tool. Exclude them, state the list
in `AI.md`, and pass that same list to the counter: an undisclosed exclusion is a thumb on
the scale, and a reader who cannot see the exclusions cannot reproduce the number.

| Exclude | Why |
| --- | --- |
| Lockfiles — `package-lock.json`, `poetry.lock`, `Cargo.lock`, `go.sum` | Written by a resolver; the committer authored none of it |
| Vendored or bundled dependencies — `vendor/`, `third_party/` | Someone else's code, counted as yours either way |
| Build output and generated code — `dist/`, `build/`, protobuf and ORM output, minified bundles | The generator's authorship, and regenerated wholesale |
| Binary and media assets | Line counts and blame are both meaningless on them |
| Wholesale-regenerated snapshots and fixtures | Churn with no authorship in either direction |

Do **not** exclude tests, documentation, or configuration. They are authored content, and
dropping them is the most common way a share gets quietly flattering. Anything excluded that
is not in this table needs a one-line reason in `AI.md` beside it.

## Procedure

### Step 1 — establish the marker and the cutoff

Find what the history actually contains before deciding anything:

```bash
git log --format='%(trailers:key=Co-Authored-By,valueonly)' | sort | uniq -c | sort -rn
git log --diff-filter=A --format='%H %ad' --date=short -1 -- AI.md
```

Fix the marker string from what is really there. Then find the first commit that carries it
and treat that as the cutoff: everything before it is **unmeasured**, not human-written.

### Step 2 — agree the exclusion list

Start from the table above, then look at the repo: `git ls-files | wc -l` against
`git ls-files -- . "${EX[@]}" | wc -l` shows how much is being dropped. If exclusions remove
most of the tree, say so in `AI.md`; a share computed over 8% of the files is a fact about
8% of the files.

### Step 3 — measure

Run the census. Record the `HEAD` sha you ran it at, because that sha is part of every
figure.

### Step 4 — choose the level

Read the surviving-blame share against the band table, then check it against how the work
was actually done. Write the level the process supports. If the band disagrees with the
process, keep the level the process supports and add one sentence saying why the number
looks different — an explained mismatch is a disclosure, an unexplained one is a discrepancy
a reader will find on their own.

### Step 5 — write the file

Use the skeleton below. Fill in every placeholder; a template artefact left in a disclosure
undermines the numbers next to it.

### Step 6 — keep it current

Re-run `--check` at the start of any turn that will produce a commit, and refresh the block
when it reports drift. In a commit gate the figures are one commit behind by design: they
are computed from history, and the commit being made does not exist yet. Stamp them with the
sha of `HEAD` before the commit and move on — see `../../skills/pre-commit-gate/SKILL.md`.
Do not amend to insert statistics about the amended commit.

## The AI.md skeleton

````markdown
# AI use in this project

**Level: L2 — Co-authored.** AI drafted substantial parts of the code and documentation; a
human directed the work, reviewed every change, and edited before committing.

**Scope.** The whole repository, except as noted below.

| Area | Level | Why it differs |
| --- | --- | --- |
| `docs/reference/` | L3 | Generated from source annotations, then reviewed rather than written. |

## Measured as of `<sha>` (`<YYYY-MM-DD>`)

| Figure | Value |
| --- | --- |
| Commits, no merges, exclusions applied | 412 |
| AI-assisted commits | 208 — 50.5% |
| Lines added / removed, AI-assisted commits | +31,204 / −12,880 |
| Lines added / removed, all commits | +52,110 / −21,447 |
| **Surviving lines from AI-assisted commits** | **6,120 of 14,880 — 41.1%** |

These figures describe the tree at `<sha>` and change with every commit, which is why they
are stamped: an unstamped percentage cannot be checked against anything and is therefore
unfalsifiable.

## Verify these numbers

```bash
<the census commands, pasted verbatim, with this project's marker and exclusions filled in>
```

## What the count covers

- **Marker.** A commit counts as AI-assisted if its message carries the trailer
  `Co-Authored-By: <identity>`.
- **Unmeasured history.** The trailer convention starts at `<sha>` (`<date>`). The 96
  commits before it are unmeasured — some were AI-assisted and carry no trailer — and are
  excluded rather than counted as human-written.
- **Exclusions.** `package-lock.json`, `vendor/**`, `dist/**`, `**/*.generated.*` — all
  tool-written or third-party, and large enough to dominate any line count.
- **Blame flags.** `git blame` with no `-M` or `-C`; move and copy detection would
  reattribute moved lines and change the surviving share.
- **Floor, not measurement.** Untagged AI-assisted commits, if any exist, make every figure
  above a lower bound.

## Accountability

The committer is responsible for the content of every commit, whatever drafted it. Review,
testing, and this project's licence obligations are unaffected by the level declared above.

## Tooling

`<the kind of tool: an agentic coding assistant run from a terminal, editor completion, a
chat interface>`, used for `<drafting, refactoring, tests, documentation>`.
````

The verify section must contain the real, runnable commands, not a pointer to where they can
be found. A reader who has to go and look them up will not check, and an unchecked
disclosure is back to being a marketing claim.

## Honesty rules

- **Count what is true, not what flatters.** Under-claiming AI use is as dishonest as
  over-claiming it, and it is the more tempting error, because it is the direction that
  makes the author look better in most rooms.
- **Never retro-tag old commits to change the numbers.** Rewriting history to improve a
  disclosure destroys the thing the disclosure was evidence of, and a reader who sees a
  force-push near the figures has no reason to trust any of them.
- **Untagged AI-assisted commits make the figures a floor, not a measurement.** If the
  trailer convention started partway through, name the cutoff commit and label everything
  before it unmeasured. Counting untagged history as human-written is a specific false
  claim, not a neutral default.
- **Disclose the exclusions.** Generated files, vendored dependencies, and lockfiles distort
  every metric, so they come out — but the list goes in `AI.md` and into the counter
  unchanged, because an exclusion nobody can see is indistinguishable from a rigged count.
- **Human accountability is unaffected by the level.** The committer is responsible for the
  content regardless of what drafted it. State this in `AI.md`, so the file cannot be read
  as spreading the blame for a defect onto a tool.
- **Make no legal claims.** Do not assert anything about copyright, ownership, licensability,
  or training data in `AI.md`. State facts about process; the law is unsettled, varies by
  jurisdiction, and is not yours to summarise here.

## Do not do these

- Do not add the trailer to a commit that had no AI involvement, or strip it from one that
  did. The trailer is the entire measurement; corrupt it and every figure downstream is
  fiction.
- Do not amend, rebase, or force-push to make a number move.
- Do not state a percentage without both the command that produced it and the sha it was
  computed at.
- Do not round in the flattering direction, or replace a figure with a word. Give the counts
  and one decimal place.
- Do not include the commit being made in the figures. It does not exist yet, and chasing it
  produces an amend loop that never converges.
- Do not expand `AI.md` into a methodology essay or a tooling advertisement. It is a fact
  sheet: level, figures, commands, caveats, accountability. Everything else dilutes it.
- Do not compute the numbers on a shallow clone. A truncated history silently produces
  smaller, wrong denominators; check with `git rev-parse --is-shallow-repository` first.

## Verify

- [ ] Every figure in `AI.md` sits beside a command that produces it.
- [ ] Each printed command was actually run as printed and reproduced the stated figure —
      pasted and executed, not eyeballed.
- [ ] The figures carry an `as of <sha>` stamp, and that sha exists in the pushed history.
- [ ] The marker string in the file is the one the commands grep for.
- [ ] The exclusion list in the file is the list the commands pass.
- [ ] The declared level matches both the measured share and the described process, or the
      mismatch is explained in one sentence.
- [ ] History before the trailer convention is labelled unmeasured, with its cutoff commit.
- [ ] No commit was amended, retagged, or rewritten to change a figure.
- [ ] The accountability statement is present.
- [ ] No claim about copyright, licensing, or ownership appears anywhere in the file.
- [ ] `python3 scripts/ai_census.py --check` exits 0, or the raw commands agree with the
      file where the script is unavailable.
- [ ] The file lints clean under the `markdown-mermaid` skill's ruleset.
