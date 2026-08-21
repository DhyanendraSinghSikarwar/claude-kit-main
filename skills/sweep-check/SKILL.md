---
name: sweep-check
description: Use when adding a condition, filter, column, status, kind, or vocabulary value that more than one site in the codebase has to learn. Finds the sites that were missed, and turns the rule into an invariant test rather than a single case.
---

# Sweep for every site a rule has to reach

A rule that several places must share gets added to some of them. Nothing throws, nothing
goes red, and the symptom is a number that disagrees with a list or a control that offers
the wrong things. This is the defect class that survives code review, because every file
you look at is individually correct.

`dupe-check` finds the same code in several places. This finds the *opposite*: a change
that should have been in several places and is only in one.

## When it applies

Reach for this whenever a change adds a value or a condition rather than a behaviour:

- a new enum member, status, kind, media type, role, or category
- a new column an existing write path should populate
- a new filter clause, permission check, or scoping predicate
- a new format, locale, or unit that display code has to branch on

If the answer to "how many places have to know about this?" is more than one, sweep.

## Procedure

### Step 1 — say the rule in one sentence

Write it down before searching. "A game is played, not watched." "Archived rows are
excluded from every count." "A draft never appears in a public feed." The sentence is what
you will test each candidate site against, and a rule you cannot state in one sentence is
usually two rules.

### Step 2 — grep for the shared thing, not for the bug

The useful pattern is whatever the sites have in common — the table, the column, the
constant, the helper — not the symptom:

```bash
rg -n "FROM <table>" --glob '!*_test.*' .
rg -n "<sharedConstant>|<sharedHelper>" .
rg -n "kind === '<value>'|status == \"<value>\"" .
```

Count the hits before reading them. If a plan or an issue told you how many sites there
are, **recount rather than trust it** — a stale count is how a sweep stops one file short.

### Step 3 — look for the `default:` arm

A `switch` ending in a bare `default: return X` will silently hand a new value the wrong
answer. So will `if (a) … else …` where a third case now exists, and a lookup table read
with `map[key]` that returns a zero value for an unknown key.

Every new value needs an arm that was **decided**. If a fallback is genuinely right, log or
warn in it, so the fallthrough is visible rather than silent.

### Step 4 — check both halves of every hand-maintained pair

Anything kept in step by hand is a site the compiler will not sweep for you:

- an enum and the list that renders it
- a schema and the fixtures, mocks, or API stubs that imitate it
- an index and the triggers that maintain it
- a registry of codes and the document that explains them
- a nav list and the router that reads it

A fake that is close but not identical is worse than one that is obviously wrong, because
it fails only where nobody looks.

### Step 5 — write the invariant, not the case

If the sweep found five sites, the test asserts over all five — ideally by **enumerating the
vocabulary itself** rather than a hand-written copy of it:

```text
BAD    for kind in ["a", "b", "c"]:        # a copy that goes stale silently
GOOD   for kind in ALL_KINDS:              # ranges over the thing under test
```

A test whose coverage is a hand-written copy of the thing it tests agrees with it forever.
This is the single highest-value line in this skill: check whether the invariant test you
are about to trust enumerates the real list, or a snapshot of it taken months ago.

Include a guard that the sweep still matches something. A predicate scan that quietly
starts matching zero files reports success forever.

### Step 6 — break it on purpose

Neuter the new condition and confirm the tests go red. A test written after the code, by
whoever wrote the code, is worth exactly what its failure proves. On a change that touches
many queries, a suite that passes on the first run is not reassurance — it is the thing to
check next.

Do this once per site the sweep found, not once overall. One breakage going red while four
others stay green is the exact outcome this skill exists to catch.

## Output

```markdown
| Site | Learned the rule? | Note |
| --- | --- | --- |
| `store/query.go:88` | yes | filter added |
| `api/handlers.go:210` | yes | the arm was a bare default |
| `ui/filters.tsx:44` | no — deliberate | display-only, never filters |
| `demo/fixtures.js:12` | yes | fake mirrored the real shape |
```

State the sites you deliberately left alone and why. A sweep that names four sites and
changes three is a finished sweep; one that silently changed three is not.

## The shapes this keeps finding

Worth reading before a sweep, because recognising the shape is faster than searching for it:

- **A default plus overrides.** `q := <the common case>` followed by a switch that replaces
  `q` for the others. Correct for exactly as long as the set does not grow, and the new
  member silently inherits the common case.
- **A rule spliced into N queries.** If a condition is repeated in five places it belongs in
  the one string they share. Written into four of the five, the failure is a count that
  disagrees with the list it counts — which reads as the feature being broken rather than as
  a filter being inconsistent.
- **A bug of omission.** Where nobody considered the concern at all, one reported instance is
  never the only one. The fix is an invariant over the whole surface plus a named exemption
  list, not a patch to the case that got reported.
- **A structural walk that misses the unstructured rows.** "Follow the foreign keys" cannot
  go stale and needs no list — and finds nothing in tables joined polymorphically or cleaned
  up by triggers. The safest-looking traversal is the one to check by hand.
- **A presence flag in a slot typed as something else.** A bare `true` passed where a
  callback is expected reads fine until something actually calls it.
