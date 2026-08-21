---
name: visual-verify
description: Screenshot-based verification of a user interface — capture every state deterministically, describe each capture in Markdown, then audit alignment, colour grading, legibility, promised features, and whether the change is actually visible. Use when a change touches a user interface and is about to be committed or released, or when the user asks how the interface looks.
---

# Verify a user interface visually

Proves that a change to an interface looks the way it is supposed to, in every state, before
it ships. Tests confirm the interface behaves; this confirms it is legible, aligned,
consistent with its own palette, and that what the documentation promises is actually on
screen and reachable.

## The pipeline

| # | Stage | Tier | Output |
| --- | --- | --- | --- |
| 1 | Capture | cheap | Deterministic screenshots of every relevant state |
| 2 | Describe | standard | One Markdown description per screenshot |
| 3 | Audit | deep | Findings against the five checks, with evidence |
| 4 | Rectify | deep | Minimal fixes, proved by a re-capture |
| 5 | Release | deep | The smallest version increment the repo's convention allows |

Run them in order. Each stage's output is the next stage's input, and the separation between
stages 2 and 3 is the point of the whole exercise.

## Why the Markdown intermediate exists

It separates observation from judgement. A model that looks and judges in one step
rationalises what it expects to see: it knows the button is meant to be there, so it sees the
button. Writing down literally what is on screen first, and only then judging that record,
makes the judgement auditable — a reviewer can check the finding against the description and
the description against the image. It also lets the audit reason across many screens at once,
which is where inconsistency lives; you cannot compare twelve images held one at a time, but
you can compare twelve descriptions.

The descriptions and the screenshots are temporary working artefacts. They live in
`.visual-verify/` at the repo root, they are regenerated on every run, and they are never
committed — see **Never committed** below.

```text
.visual-verify/
├── before/    screenshots taken before the fixes, by stage 1
├── after/     screenshots taken after them, by the stage 4 re-capture
└── desc/      one .md per before/ screenshot, same basename
```

Only the `before/` set is described. The `after/` set is compared image to image against its
`before/` counterpart, so describing it again would overwrite the description that comparison
is made against.

## Delegation

| Stage | Agent | Tier | Why that tier |
| --- | --- | --- | --- |
| Capture | `../../agents/screenshot-runner.md` | cheap | Driving a harness to fixed states — no judgement |
| Describe | `../../agents/ui-describer.md` | standard | Literal transcription, but it must decide what counts as a region |
| Audit | `../../agents/visual-auditor.md` | deep | Adversarial: finding what the person who built it stopped seeing |
| Rectify | `../../agents/visual-auditor.md` | deep | The agent that found the defect fixes it — it already holds the evidence, and a handoff loses which measurement the fix has to satisfy |

If your runtime supports subagents, spawn each with the body of the named file as its
instructions and ignore that file's YAML frontmatter — the frontmatter is packaging, the
prose below it is the prompt. If it has no subagents, run every stage inline yourself, in
the same order, to the same rules. The procedure below is complete on its own. One spawn of
the audit agent covers stages 3 and 4; do not spawn it twice, and do not re-run stage 4
inline after it returns — the fixes and the re-capture are already in its report.

Hand the capture agent four things explicitly, every time: the state list from **States to
capture** below, the determinism controls from the table above including the theme and the
viewport for each capture, the output directory (`.visual-verify/before/`, or
`.visual-verify/after/` on the stage 4 re-capture), and the
`<surface>-<state>-<theme>-<viewport>` naming scheme. Left unsaid, each falls back to that
agent's own default — its shorter state list, a surface-and-state name with no theme or
viewport segment, and the committed docs image directory. The name is the one that fails
silently: every capture that differs only by theme or viewport overwrites the last, so four
images become one and the before/after pairing has nothing to pair.

Related skills: `ui-glossary` produces the element inventory that check 4 audits against, so
take the inventory from there rather than re-deriving it. `tui-screenshots` owns terminal
capture. `changelog-release` owns the release mechanics. `pre-commit-gate` is the usual
caller — it runs this skill as part of stage 5 when the diff touches a UI.

## Stage 1 — capture (cheap)

Determinism is the whole game. A screenshot that varies between runs cannot show whether
anything changed: every comparison then contains the change you made plus the noise the
harness added, and there is no way to tell them apart after the fact.

Stage 1 writes into `.visual-verify/before/`. Only the stage 4 re-capture writes into
`.visual-verify/after/` — until a fix has been made and proved, that directory is empty, and
`before/` is the only set stages 2 and 3 have to work from.

### Determinism controls

| Control | Set it to | Because |
| --- | --- | --- |
| Viewport | A fixed width and height per named size, never inherited from the host | Reflow is a function of width; an inherited viewport re-lays out the page for a reason that is not your change |
| Device pixel ratio | Pinned to one value, stated in the filename | At DPR 1 and DPR 2 the same CSS renders different hinting, different rounding, and different apparent weight |
| Animations and transitions | Disabled — zero durations plus the platform's reduced-motion setting | A capture taken mid-transition catches an interpolated frame, so identical code yields a different image each run |
| Clock | Frozen at one fixed instant | Relative timestamps, expiry badges, and date pickers move pixels while the code stands still |
| Fixture data | Seeded or fixed, never live or production data | Random names change string widths, which changes wrapping, which changes everything below; live data also leaks into images |
| Fonts | A pinned set, loaded locally, awaited before capture | A fallback substituted for one frame changes every metric on screen, and smoothing has not settled until the real font is in |
| Network | Stubbed, or offline with fixed responses | A real request has unpredictable latency, and the screenshot lands on a spinner you did not mean to capture |
| Locale and timezone | Pinned explicitly | They change number, date, and currency formatting, and some of them change text direction |
| Theme | Set explicitly per capture, never inherited | Otherwise the host machine's setting decides which theme you audited |
| Wait condition | A settled condition: no pending requests, no running animations, target element present and unchanged across two frames | A fixed sleep is either too short, and flakes, or too long, and wastes the run — and it never actually knows the page is done |

### States to capture

The happy path is the state the person who built it has already looked at a hundred times.
Visual bugs live in the states nobody screenshots.

| State | Capture it because |
| --- | --- |
| Default, populated | It is the baseline the before/after pair compares against |
| Empty | First-run and zero-result layouts collapse; placeholder copy and centring fail here first |
| Loading | Skeletons and spinners are where layout shift shows up, and where sizes were guessed |
| Error | Error surfaces get the least design attention and the most user attention |
| Disabled or read-only | Contrast is deliberately reduced here, and routinely lands below any readable floor |
| Permission-gated | Almost nobody on the team has an account that sees it, so nobody has looked at it |
| Long-content overflow | Fill every field with the longest realistic value; truncation bugs exist only in this state |
| Narrow viewport | Reflow, stacking order, and anything that was positioned absolutely |
| Wide viewport | Stretched containers, orphaned controls, and line lengths nobody meant to allow |
| Dark theme and light theme | Token parity — a colour correct in one theme is regularly invisible in the other |

Not every surface has every state. Capture the ones it has, and say in the report which
states do not exist for this surface rather than silently omitting them.

### Naming

Name for the state, never for a number, so a before/after pair is mechanically comparable and
so inserting a screen does not renumber the set:

```text
<surface>-<state>-<theme>-<viewport>.<ext>

settings-default-light-wide.png
settings-empty-dark-narrow.png
settings-error-light-narrow.png
```

The extension is whatever the harness writes — a browser driver produces PNG, `tui-screenshots`
produces SVG. Only the basename carries meaning: the same basename appears in `before/`, in
`after/`, and in `desc/` for the `before/` set. That is what makes comparison a file operation
rather than a matching exercise.

### Surface kinds

| Surface | Capture with | Note |
| --- | --- | --- |
| Web front end | The headless browser driver the project already uses for its end-to-end tests | Reuse the existing driver; adding a second one gives you two harnesses to keep deterministic |
| Desktop app | The platform's own UI automation harness | Drive it through real interaction, not by constructing views directly |
| Mobile app | The platform simulator or emulator plus its UI test harness | Pin the device profile; it sets the viewport and the DPR at once |
| Terminal UI | Hand off to the `tui-screenshots` skill | It already solves the deterministic-terminal problem. Do not re-implement it here |

Drive the app to each state through its real interaction path, not by rendering a component in
isolation. A component rendered directly can show a state the application cannot actually
reach, and an unreachable state audits clean while the real one is broken.

### If there is no capture harness

Say so and stop. Do not half-instrument the application to get one screenshot: adding a
driver, a fixture server, and a wait strategy is a project in its own right, and one done in a
hurry produces captures that flake, which get ignored, which leaves the project worse off than
having none.

Record the absence in `ROADMAP.md` as a pending item, report this stage as
`n/a — no capture harness`, and do not proceed to stage 2. There is nothing to describe.

## Stage 2 — describe (standard)

### Read the project's claims first

Before looking at a single image, read what the project says about itself. Description is not
neutral: you cannot notice that something promised is missing unless you know what was
promised, and a missing element leaves no trace on screen to catch your eye.

| Read | Take from it |
| --- | --- |
| `ui_glossary.html` | The element inventory — every control the project claims to have, and its documented label |
| `ROADMAP.md` | What is shipped and what is pending. A pending item being absent is correct, not a finding |
| `TROUBLESHOOTING.md` | The error states that must be reachable, and the text each should show |
| `DEVELOPMENT.md` | How to build and run, and how to reach the states that need setup |
| `PLAN.md` | Why the interface is shaped this way. A deliberate asymmetry recorded here is a decision, not a defect |
| `CHANGELOG.md` | What shipped recently, which gives check 5 something to compare against |
| `README.md` | The user-facing feature list |
| `git log --oneline -5` | What this change claims to do, in the author's own words |

This reading tells you what to *look for*. It never tells you what to *record*. Keep those
apart — the next rule is the one that makes the difference.

### The description format

One Markdown file per screenshot, same basename, in `.visual-verify/desc/`. Two sections,
strictly separated:

```markdown
# settings-empty-dark-narrow

Capture: `before/settings-empty-dark-narrow.png` — 390×844, DPR 2, dark theme, empty state.

## Observed

- Top bar, full width, ~56px tall. Left: back chevron. Centre: "Settings" in white,
  centred within the bar. Right: nothing.
- Below the bar, a heading "No accounts yet", left-aligned, ~24px, starting ~16px from
  the left edge.
- Beneath it, body text reading "Add an account to sync your…" — the line is cut off at
  the right edge of the card; no ellipsis is drawn.
- A filled button labelled "Add account", horizontally centred, ~40px below the body text.
  Fill is a mid blue, label is white.
- Bottom-left, small grey text, unreadable — approximately 9px, low contrast against the
  background.

## Interpretation

- The bottom-left text is probably a version string, from its position. Not readable in
  this capture; flagged rather than transcribed.
- The "Add account" button appears to be the only interactive control in this state.
```

The **Observed** section is literal. Work top to bottom, region by region:

- Every visible control: its kind, its label quoted verbatim, and its position relative to its
  neighbours. Relative position, not absolute coordinates — the audit compares screens, and
  coordinates from different viewports do not compare.
- Text that is cut off, clipped, or overflowing, recorded exactly as it appears, including
  whether an ellipsis is drawn. "Cut off mid-word with no ellipsis" and "ends in `…`" are
  different findings.
- Colours as seen. Sample a value where the tool can sample one; otherwise describe it. Do
  not name the design token — naming the token is a claim about intent, and check 2 exists
  to test that claim independently.
- Anything unreadable recorded as `unreadable`, with the reason: too small, too low contrast,
  behind an overlay, cut off. Never guessed.

The hard rule: **nothing may be recorded as present because the documentation promised it.**
That is precisely the failure this pipeline exists to catch. A describer who fills in from the
docs makes the whole exercise circular — the audit then compares the documentation against a
description generated from the documentation, finds perfect agreement, and reports a clean run
on an interface it never actually looked at.

Everything uncertain goes in **Interpretation**, flagged as such. Purpose, state, intent, and
anything you inferred rather than read belong there. If you are unsure which section a line
belongs in, it belongs in Interpretation.

## Stage 3 — audit (deep)

Judge the descriptions *and* the images together against the five checks. The descriptions
carry the cross-screen comparison; the images carry the things description flattens.

### Check 1 — alignment

| Criterion | The finding looks like |
| --- | --- |
| Shared edges | Elements stacked in a column whose left edges differ by 1–3px |
| Shared baselines | Text set side by side sitting on two baselines a few pixels apart |
| Spacing rhythm | Gaps that are not multiples of the project's spacing unit — a 13px gap between two 12px gaps |
| Grid adherence | Content that starts or ends off the declared column grid |
| Optical versus mathematical centring | A glyph with asymmetric mass — a play triangle, an arrow — centred by its bounding box and therefore looking off-centre, or the reverse |
| Control-group axis | A group of buttons or fields where some are left-aligned and some centred |

Near-misses are the finding, not the obvious errors. A 40px misalignment is caught by whoever
opens the page. A 3px inconsistency reads as sloppiness that nobody can name, so it never gets
reported and never gets fixed.

### Check 2 — colour grading

| Criterion | The finding looks like |
| --- | --- |
| Palette source | A colour that traces to no project token. A one-off value is a finding even when it looks right, because the next change to the token will miss it |
| Semantic consistency | The colour that means error somewhere means something else elsewhere; a destructive action sharing the primary colour |
| Light and dark parity | A token with no counterpart in the other theme, or a pair that carries the same role at very different contrast |
| Measured contrast | A ratio below the threshold for that element's size and kind |

Contrast thresholds, measured against the recognised accessibility levels:

| Element | Minimum ratio |
| --- | --- |
| Body text — under 24px regular, or under 18.66px bold | 4.5:1 |
| Large text — 24px regular and above, or 18.66px bold and above | 3:1 |
| Non-text UI — control borders, focus rings, icons that carry meaning, chart segments | 3:1 |
| Disabled controls | Formally exempt — but the exemption is a licence, not an instruction |

Compute the ratio from the sampled foreground and background values. Do not eyeball it: a
dark-on-dark pair looks acceptable on a good panel at high brightness and disappears on a
laptop in daylight, and your judgement of it is a judgement about your screen. Where text sits
over an image or a gradient, measure against the lightest and the darkest pixel it covers, not
the average — the average passes while the word sitting on the highlight does not.

Colour must never be the only channel carrying meaning. A red border with no icon and no text,
or a chart whose series differ only in hue, is a finding: roughly one man in twelve has some
colour vision deficiency, and hue is flattened by greyscale printing and by cheap panels.
Pair colour with text, an icon, a shape, or a position.

### Check 3 — icon and text legibility

| Criterion | The finding looks like |
| --- | --- |
| Rendered size | Text below the floor at its *rendered* size — a 14px label inside a 0.8 scale renders at 11.2px |
| Truncation | An ellipsis with no way to recover the full value: no tooltip, no detail view, no wrap |
| Text over imagery | Type placed on a photo or gradient with no scrim, plate, or shadow to hold it |
| Icon-only controls | An icon-only control with no accessible name in the platform's accessibility layer |
| Icon meaning | An icon whose meaning is not recoverable once the label beside it is covered |
| Target size | An interactive target smaller than the platform's minimum, or crowded against its neighbour |

Take the floors from the project's own type and spacing scale where it has one — it is the
authority, and a finding against it is actionable. Where it has none, treat rendered body text
under 12px, interactive labels under 14px, and interactive targets under 24×24 as findings,
and say you applied a default because the project declares no scale.

Cover the label and ask what the icon means. If the answer requires the label, either the
label stays or the glyph is wrong. Novel iconography is legible to the person who drew it and
to nobody else.

### Check 4 — promised features present

| Source | Cross-check against the captures |
| --- | --- |
| `README.md` feature list | Every listed feature is visible and reachable |
| `ROADMAP.md` shipped items | Shipped means present. Pending means absent is correct |
| `CHANGELOG.md` released entries | Everything in a released section is on screen |
| `ui_glossary.html` element inventory | Every element present, with the label the glossary documents |

Take the inventory from the `ui-glossary` skill rather than re-deriving it, so the audit and
the documentation are checking the same list.

A promised feature that cannot be *reached* is a finding at the same severity as one that is
broken. From the user's side there is no difference between a feature that does not work and a
feature they cannot find.

The reverse is also a finding, filed against the documentation rather than the interface: an
element on screen that appears nowhere in the glossary means the glossary is stale, and a
stale inventory silently weakens every future run of this check.

### Check 5 — changes reflected

Every user-visible change in the diff must be visible in the screenshots. If one is not,
exactly one of three things is true. Establish which, and report that — never report it as
ambiguous, because "the change may not be visible" is an unfinished check handed to a reader
who has less information than you do.

| Possibility | Confirm it by | Then |
| --- | --- | --- |
| The capture is stale | Checking the built asset, not the source, for the change; then rebuilding | Re-run stage 1 and audit again |
| The change did not land | Exercising the path in the running app by hand, and checking for a feature flag, a cache, or the wrong build target | It is a defect — take it to stage 4 |
| It is not user-visible after all | Tracing the changed code to the render path and showing it cannot reach one | Record the conclusion and move on |

### Finding shape

Every finding carries a severity, the evidence, and what correct would look like. A finding
without the third is a complaint.

```markdown
| # | Severity | Check | Evidence | Wrong | Correct would be |
| --- | --- | --- | --- | --- | --- |
| 1 | Blocker | Legibility | settings-empty-dark-narrow.png, bottom-left | Version string ~9px, contrast 1.9:1 | Body token at 12px minimum, 4.5:1 against the surface |
| 2 | Should fix | Alignment | settings-default-light-wide.png, form column | Field left edges differ by 3px | One shared left edge, on the 8px grid |
| 3 | Consider | Colour | Both themes, primary button | Dark-theme fill is a one-off hex | The existing primary token, which already has a dark counterpart |
```

| Severity | Means |
| --- | --- |
| **Blocker** | Something is unreadable, unreachable, or communicates the wrong thing |
| **Should fix** | A rule is broken with a visible consequence — measured misalignment, contrast under threshold, truncation with no recovery |
| **Consider** | Consistent with the rules but weaker than it could be. Never fixed in the same pass without asking |

## Stage 4 — rectify (deep)

One fix per finding, at the cause, as small as the cause allows.

### Forbidden repairs

| Never | Because |
| --- | --- |
| A hardcoded pixel nudge to make one screen line up | It fixes the viewport you looked at and breaks the ones you did not. The cause is a missing shared token or layout rule, and the nudge hides it |
| A contrast fix that invents a colour outside the palette | It passes the ratio and fails the palette check, and the token that was actually wrong is still wrong everywhere else it is used |
| Suppressing a state rather than fixing it — hiding the empty state, removing the error banner, dropping a theme | The state still happens to the user. Only the evidence is gone |
| Editing a screenshot or its description instead of the interface | This is changing the expected value to the observed value, with extra steps. The record now agrees with the defect |
| Widening a container until the overflow stops | The overflow returns with the next longer string. The fix is truncation with a way to recover the value, or wrapping |

A **Consider** finding is not fixed in the same pass unless the user asks. Restyling something
that was merely weaker than it could be buries the findings that mattered in a diff nobody can
review.

### Re-capture and compare

Re-run stage 1 for the affected states with the identical controls and the identical names,
writing into `after/`. Then compare each pair against `before/`.

A fix is not done until the before/after pair shows it. State, in one line per fix, what
changed between the two images. If the pair is byte-identical, the fix did not land — that is
the same three possibilities as check 5, so resolve it there rather than assuming.

Re-capture the neighbouring states too, not only the one that was wrong. A change to a shared
spacing or colour token moves every screen that uses it, and a fix that repairs one screen
while breaking three is the most common way this stage does net harm.

### The round cap

| Round | Do |
| --- | --- |
| 1 | Fix, re-capture the affected and neighbouring states, re-audit them |
| 2 | Fix, re-capture, re-audit |
| 3 | Fix, re-capture, re-audit |
| 4 | Stop. Report `OPEN` with the surviving findings |

Three is the cap, for the same reason the gate caps repair at three: a visual defect that
survives three considered fixes is one you have not understood, and an unbounded loop makes
the diff steadily less reviewable while the finding that mattered gets buried under
speculative edits. On the fourth round report every fix attempted and why each was rejected
by the re-capture.

A finding the re-capture raises against a state no earlier finding covered is reported, not
fixed in this pass — the same rule as **Consider**, and for the same reason.

## Stage 5 — release (deep)

Only cut a release if releasing is what was asked. When `pre-commit-gate` is the caller, stop
after stage 4 and hand the findings back — the gate commits, it does not release.

### Detect the convention

Read the evidence before choosing a number. Do not assume semantic versioning; plenty of
projects use something else deliberately, and a bump in the wrong scheme is hard to undo.

```bash
git tag --list | tail -10
```

Then read every place a version is declared — `changelog-release` lists the manifests and the
search that catches the rest.

| Evidence | Convention | Smallest increment |
| --- | --- | --- |
| Tags like `v1.4.2`; SemVer named in the README or changelog | Semantic versioning | Patch: `1.4.2` → `1.4.3` |
| Current version is `0.y.z` | Pre-1.0 semantic versioning | Still a patch: `0.7.1` → `0.7.2`. Pre-1.0 loosens what a breaking change costs, not what a fix costs |
| Tags like `2026.08.3` or `24.11` | Calendar versioning | The trailing serial segment for the current period. Never back-date to reuse an earlier period |
| A monotonic integer build or version code | Build number | Plus one |
| No tags and no version field anywhere | Unversioned | None. Do not invent a scheme for someone else's project |

A visual fix never justifies a larger segment than the smallest one the scheme has. Version
numbers are a compatibility signal: a consumer who sees a minor bump budgets time to read the
release notes. Once minor bumps also mean "a button moved 3px", they stop reading, and the
signal is gone for the change that genuinely needed it.

Hand the mechanics — the changelog entry, the version fields, the tag, the notes — to the
`changelog-release` skill, from its Step 2 onward. Its Step 1 picks a SemVer bump from the
diff and is superseded by the convention you detected above; so are its "adheres to Semantic
Versioning" line and its `v` tag prefix wherever the repo's own tags say otherwise. Do not
restate or improvise the rest here.

## Never committed

Skills and agents from this kit are **copied** into a consuming repository's working directory
so that repo's tooling can find them. They are **never committed** to that repository. They
are committed in one place only: this kit. A consuming repository's git history must contain
zero kit files, at any path, forever.

Three reasons, each failing differently:

- A committed copy forks silently. The moment it is in another repo's history someone edits it
  there, and the two versions diverge with nothing to reconcile them.
- Updates stop arriving. A copy under version control looks authoritative, so nobody
  re-copies it, and every improvement made here stops at the repo boundary.
- It re-creates the exact duplication this kit exists to remove. The whole purpose is one
  source and many consumers; a committed copy makes it many sources.

Enforcement is local and requires committing nothing: add the kit paths to `.git/info/exclude`
in the consuming repo, which is per-clone, untracked, and needs no commit of its own. Use
`.gitignore` only when a whole team copies the kit and genuinely wants a shared ignore rule —
and note that this is the one line about the kit that does get committed there, so it is a
deliberate trade rather than the default.

The same applies to this skill's own output. `.visual-verify/` — every screenshot, every
description, both the `before/` and `after/` sets — is a temporary working artefact and is
never committed. It is regenerated on the next run, it is large, and a committed set goes
stale immediately while still looking authoritative. Put it in `.git/info/exclude` alongside
the kit paths.

Documentation screenshots are a different thing with a different lifecycle: those are produced
deliberately, live in the docs image directory, and are committed. Do not confuse the two, and
do not promote a verification capture into the docs — it was framed to expose defects, not to
show the product.

## Do not

- Do not judge straight from the images without writing the descriptions. That is the one step
  the pipeline exists to force, and skipping it returns you to confirming what you expected.
- Do not capture only the happy path. The states nobody screenshots are the states nobody
  fixed.
- Do not compare screenshots taken under different controls — a different viewport, theme,
  seed, or fixture set. The diff then shows the harness rather than the change.
- Do not redesign. This skill finds defects against rules the project already holds. Improving
  something that was not a finding makes the diff unreviewable and buries the real ones.
- Do not accept "looks fine" for contrast, size, or alignment. Measure, and put the measured
  value in the finding.
- Do not report a check as ambiguous. Check 5 has exactly three answers; establish which.
- Do not commit the captures, the descriptions, or any kit file into the consuming repository.
- Do not cut a release when the caller was the gate, and do not bump a version for a fix that
  is not yet proved by a re-capture.

## Report

```markdown
| Stage | Tier | Outcome |
| --- | --- | --- |
| 1 Capture | cheap | 14 states across 2 themes, 2 viewports — 1 state n/a (no permission gate) |
| 2 Describe | standard | 14 descriptions in `.visual-verify/desc/` |
| 3 Audit | deep | 1 blocker, 3 should-fix, 2 consider |
| 4 Rectify | deep | 4 fixed, proved by re-capture; 2 consider left open |
| 5 Release | deep | CalVer detected — `2026.08.3` → `2026.08.4` |

**Findings**

| # | Severity | Check | Evidence | Wrong | Correct would be |
| --- | --- | --- | --- | --- | --- |
| 1 | Blocker | Legibility | settings-empty-dark-narrow.png, bottom-left | 9px at 1.9:1 | Body token, 12px, 4.5:1 |

**Verdict**: VERIFIED — every blocker and should-fix is fixed and shown in a before/after
pair. 2 `Consider` findings left open and listed above.
```

End with `VERIFIED` or `OPEN` on its own line. `OPEN` names what remains and what each item
needs. A run that trails off without one leaves the reader unable to tell a clean interface
from an unfinished audit.

## Verify

- [ ] Every capture ran under the determinism controls, and re-running produces identical
      files.
- [ ] Every state the surface actually has was captured, in both themes and both viewports;
      any missing state is named with a reason.
- [ ] Filenames follow the state-based scheme, and every `after/` image has a `before/`
      counterpart with the same basename.
- [ ] The project's own claims were read before any description was written.
- [ ] Every description separates Observed from Interpretation, and nothing in Observed came
      from the documentation rather than the image.
- [ ] Anything unreadable is recorded as unreadable, not guessed.
- [ ] All five checks ran against every capture, and each finding carries a severity, its
      evidence, and what correct would look like.
- [ ] Every contrast figure was computed from sampled values, not judged by eye.
- [ ] No fix used a hardcoded nudge, an off-palette colour, a suppressed state, or an edited
      screenshot or description.
- [ ] Every fix is shown by a before/after pair, and the neighbouring states were re-captured
      too.
- [ ] The version increment matches the convention detected from the repo, and is the smallest
      that convention allows.
- [ ] `.visual-verify/` and the kit paths are in `.git/info/exclude`, and `git status` shows
      neither.
- [ ] The report ends with exactly one of VERIFIED or OPEN.
