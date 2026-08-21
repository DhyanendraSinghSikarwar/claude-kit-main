---
name: css-review
description: Review stylesheets for token discipline, specificity creep, dead rules, and breakpoint coherence — the structural problems a screenshot cannot show. Use when a change touches CSS or styling, when styles have grown hard to change safely, or before a visual verification pass.
---

# Review CSS

Finds the problems in a stylesheet that looking at the page cannot: a value hardcoded instead
of drawn from a token, a selector that only wins by being more specific than the last one,
rules matching nothing, breakpoints that disagree with each other.

This is the structural half. The `visual-verify` skill judges the rendered result — alignment,
contrast, legibility. Run this first when a change touches styling: it is cheaper, and a
finding here usually explains a finding there.

## Delegation

Collecting declarations, selectors, and value frequencies is mechanical. Spawn a subagent with
the body of `../../agents/scoped-search.md` (tier `cheap`) bounded to the stylesheet
directory, and judge its output here. Without subagents, use the greps below directly.

## Step 1 — establish the system before judging anything

A stylesheet can only be reviewed against its own intent. Find what it declares:

- Custom properties in `:root`, or a theme file, or the design-token export.
- The framework's config, if one is in use — a Tailwind, SCSS variable, or CSS-in-JS theme.
- The breakpoints actually defined, and where.

If there is no token system at all, that is the first finding, and most of the others below
are symptoms of it. Say so once rather than reporting every hardcoded value separately.

## Step 2 — token discipline

Every colour, spacing, radius, and font size should trace to a token. A one-off value is how a
palette drifts: nobody chose `#3b82f7` deliberately, it was typed near `#3b82f6`, and now two
blues ship.

```bash
# hardcoded colours outside the token definition
grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(' --include='*.css' --include='*.scss' . \
  | grep -v ':root'

# the frequency table -- near-duplicates are the finding
grep -rhoE '#[0-9a-fA-F]{6}' --include='*.css' . | sort | uniq -c | sort -rn
```

Two colours differing by one or two hex digits are almost never intentional. Same for spacing:
a project with `8px`, `9px`, and `10px` in play has no spacing scale, whatever its tokens say.

## Step 3 — specificity

Specificity creep is the reason a stylesheet becomes unsafe to change. Each override wins by
being more specific than the last, so the next person must be more specific still, and the
only remaining move is `!important`.

```bash
grep -rn '!important' --include='*.css' --include='*.scss' .
grep -rnE '^[^{]*#[a-zA-Z]' --include='*.css' .          # ID selectors
grep -rnE '^[^{]*(\.[a-z-]+\s+){3,}' --include='*.css' . # deep descendant chains
```

| Finding | Why it matters |
| --- | --- |
| `!important` outside a utility class | It ends the cascade. The next override has no legal move |
| ID selectors for styling | Effectively unoverridable by any class |
| Chains of four or more descendants | Binds the style to a DOM shape, so markup changes silently break styling |
| A selector duplicated with higher specificity | Someone lost a cascade fight; the earlier rule is probably dead |

The fix is almost never more specificity. It is a single flatter class at the component
boundary.

## Step 4 — dead rules

Stylesheets accumulate. A class whose markup was deleted stays forever because nobody can
prove it is unused.

Check each candidate against the templates, components, and any string-built class names
before deleting. Dynamic construction — `` `btn-${variant}` `` — is invisible to a plain grep,
and that is exactly how a "dead" rule turns out to be load-bearing.

Anything you cannot prove unused, report rather than delete.

## Step 5 — breakpoint coherence

```bash
grep -rhoE '@media[^{]+' --include='*.css' . | sort | uniq -c | sort -rn
```

| Finding | Why |
| --- | --- |
| Breakpoints that nearly match — `768px` and `767px`, `48em` and `768px` | One pixel where nothing matches, or two rules both applying |
| Mixed `min-width` and `max-width` for the same boundary | Overlap or gap at the edge; pick one direction and hold it |
| A breakpoint used once | Usually a fix for one screen that will not survive the next layout change |
| Units mixed across the same set | `em` and `px` breakpoints respond differently to user font settings |

Check the dark theme has parity. A token redefined under `prefers-color-scheme: dark` but not
under an explicit `[data-theme]` attribute — or the reverse — gives one of the two theme paths
a half-applied palette, and it is invisible until someone toggles.

## Step 6 — report

Group by class, not by file, with the count and one example each. State the token system as
found, then the findings by severity, then what you verified as *not* a problem — a dynamic
class name that looked dead but is constructed at runtime is worth recording so the next
review does not re-investigate it.

## Do not

- Do not delete a rule you have not proved unused, especially where class names are built
  dynamically.
- Do not fix specificity by adding specificity.
- Do not introduce a token system as part of an unrelated change — propose it separately.
- Do not reformat a stylesheet while reviewing it. The diff then hides every real change.
- Do not judge rendered appearance here. That is `visual-verify`, and it needs screenshots.

## Verify

- [ ] The token system was identified before any value was called hardcoded.
- [ ] Hardcoded colours and spacing are reported with a frequency count, near-duplicates first.
- [ ] Every `!important` and ID selector is listed with what it is overriding.
- [ ] No rule was deleted without checking dynamically constructed class names.
- [ ] Breakpoints were listed and checked for near-misses and mixed directions.
- [ ] Both theme paths were checked for token parity.
- [ ] Findings are grouped by class with counts, not listed one per line.
