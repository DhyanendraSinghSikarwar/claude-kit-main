---
name: tui-screenshots
description: Capture deterministic screenshots of a terminal UI or CLI — SVG, plain text, or a rendered image — driven headlessly against throw-away dummy data, with every source of terminal non-determinism pinned. Use when docs need fresh terminal screenshots, after any change to a TUI's layout, styling, or screens, or when a visual audit needs the terminal surface captured.
---

# Terminal UI screenshots

Captures crisp, deterministic screenshots of a terminal application without a real terminal
and without manual clicking. Re-running regenerates byte-identical output, so the docs can be
regenerated in CI and the diff stays empty when nothing visual changed.

Byte-identity is the whole point, not a nicety. A capture that varies between runs cannot
show whether anything changed: every comparison then contains your change plus whatever the
harness added, and nothing separates them after the fact. Showing what the interface looks
like now, and whether that differs from before, is the only job a screenshot has. A capture
that churns does neither, and once the images churn nobody reviews them again.

`capture.example.py` in this directory is a complete working script driven through one
framework's headless pilot. Adapt it; do not run it as-is against a different project. It is
a reference for the *shape* — seeding, a fixed terminal size, pilot-driven navigation, and
the `--out` / `--only` flags — not for its imports or its dataset.

## Delegation

Capture is mechanical: drive to a known state, write a file, confirm it is not blank. Tier
`cheap`. If your runtime supports subagents, spawn one with the body of
`../../agents/screenshot-runner.md` as its instructions (ignore that file's YAML
frontmatter) and give it the state list, the terminal size, and the output directory. If your
runtime has no subagents, follow the procedure below inline — it is complete on its own.

Judging the captures is a different job at a different tier, and it belongs to
`visual-verify`. Keep them apart: a run that captures and judges at once produces opinions
mixed into evidence, and neither can then be checked.

## Where this sits relative to `visual-verify`

`visual-verify` owns the wider audit — it captures, describes, audits against its five
checks, rectifies, and releases. It hands the terminal surface here rather than solving the
deterministic-terminal problem a second time. Do not restate its audit criteria in this skill
and do not apply them while capturing; read them there when you need them.

| Called by | Output goes to | Naming | Committed? |
| --- | --- | --- | --- |
| A docs refresh — the usual case | the docs image directory | `tui-<screen>.svg` | Yes. Docs images are deliberate artefacts with a review lifecycle |
| `visual-verify` stage 1 | `.visual-verify/before/`, then `.visual-verify/after/` | that skill's `<surface>-<state>-<theme>-<viewport>` scheme | No. Regenerated every run |

Under `visual-verify` the terminal's *theme* is the colour scheme name and its *viewport* is
the terminal size, so a capture lands as `tui-report-empty-dark-80x24.svg`. Keep the two
output sets apart, and never promote a verification capture into the docs — it was framed to
expose defects, not to show the product.

## Step 1 — choose the capture approach

### Framework-native exporters, checked first

If the application is built on something that can export a rendered frame itself, use that.
It runs in-process with no pseudo-terminal, no emulator, and no timing, which removes most of
step 3's problems instead of controlling them.

| Marker in the dependency manifest | Capture with | Output |
| --- | --- | --- |
| A TUI framework with a headless test pilot (e.g. `textual`) | its screenshot export, driven by the framework's own test pilot | SVG |
| A rich-text console library with a record mode (e.g. `rich`) | a recording console, then its SVG, HTML, or text export | SVG / HTML / text |
| An argument parser or plain stdout (e.g. `click`, `argparse`, `cobra`) | replay the captured output through a recording console | SVG / text |
| A console or TUI library in any other language | check it for a record mode or headless renderer before reaching for a pseudo-terminal | varies |

Detect this from the dependency manifest, not from how the application looks on screen. Two
libraries that produce the same picture have entirely different capture stories.

### Generic approaches, when no exporter exists

| Approach | Produces | Diffable | Choose when |
| --- | --- | --- | --- |
| Direct ANSI capture to text | `.txt` (escapes stripped) or `.ansi` (escapes kept) | Yes, line by line | Content is the subject — wording, column widths, alignment, what got truncated. The default for CLI docs |
| Console or framework SVG export | `.svg`, which is a text file | Structurally, though noisily | Colour and box drawing belong in the docs and the app can render them without an emulator |
| Recorded session | a cast file (e.g. from `asciinema`), optionally rendered to GIF or animated SVG by a headless renderer such as `agg` | The cast, yes; the GIF, no | Motion is the subject — a bar filling, a screen transition, a whole interactive flow |
| Image render of a terminal | `.png` | No | Exact rendering is the subject: font, ligatures, true colour, inline images, emulator glyph handling |

Text captures diff cleanly and are searchable, but they lose exact rendering — nothing in a
text capture tells you that a ligature broke a box border or that a foreground and background
pair is unreadable together. Image captures show what a user truly sees but cannot be diffed
usefully: a one-pixel shift and a completely rewritten screen both report the same thing, that
the bytes differ. Pick per question rather than per project. Most docs want text or SVG; a
complaint about rendering wants a PNG; a workflow wants a recording.

Prefer SVG where an exporter offers it. It is text, so it diffs meaningfully in git, it stays
sharp at any zoom, and it renders in GitHub Markdown. Fall back to a recording only when you
must show motion, and to a PNG only when rendering itself is what is in question.

Do not capture the same screen in two formats "to be safe". Every format is regenerated and
reviewed on every change, so a second one is a permanent cost paid for a question nobody
asked.

### Do not assume the platform

Detect the operating system rather than assuming it. A pipeline that shells out to one
platform's screenshot binary, or to an emulator that exists only on a developer's laptop,
fails on every other machine and on CI — usually silently, producing a zero-byte file. Prefer
approaches that need no emulator at all; where an image is genuinely required, use a headless
renderer that rasterises a cast or an ANSI stream (`agg`, `termshot`, or equivalent), because
that runs the same everywhere.

## Step 2 — build a throw-away workspace

Never screenshot against real data. Create a temporary directory containing a dummy project
tree and a dummy dataset that exercises the interesting cases: a few realistic-looking names,
at least one long value that tests truncation, at least one empty or null field, and enough
rows that any table or scrollbar looks populated.

Two rules that matter more than they look:

- **Nothing real.** No customer names, no internal paths, no tokens, no company-specific
  identifiers. These images end up in a public README.
- **Nothing embarrassing.** Placeholder text is read by every future visitor.

## Step 3 — pin every source of non-determinism

A terminal inherits far more from its environment than a browser does, and almost all of it
is visible in the capture. Set each of these explicitly in the capture process's own
environment rather than trusting the shell that launched it, so the run behaves identically
from a terminal, from a build file, and from CI.

| Source | Control | Why it matters |
| --- | --- | --- |
| Terminal size | Set columns and rows in the script; never inherit `COLUMNS` / `LINES` or query the tty | Width decides wrapping, truncation, and which table columns survive at all. An inherited size re-lays out the screen for a reason that is not your change |
| Colour depth | Pin `TERM` and `COLORTERM` (e.g. `xterm-256color`, `truecolor`) | The same style resolves to 16, 256, or 24-bit colour depending on these two, so an unpinned capture shows the host's palette rather than the app's |
| Colour on or off | Decide, then set it: `NO_COLOR` to strip, `FORCE_COLOR` / `CLICOLOR_FORCE` to keep it through a pipe | Every library defaults differently and most honour these. Leaving them unset means whichever library you happened to call decides what the docs show |
| tty detection | Run under a pseudo-terminal when you want the interactive rendering; do not simply redirect stdout to a file | Programs branch on `isatty()`. Under a pipe they routinely drop colour, drop progress bars, and fall back to a plain single-column layout — a rendering no user ever sees |
| Locale | Pin `LC_ALL` and `LANG` to one UTF-8 value | Locale decides decimal points, thousands separators, month and day names, and sort order. A capture in the build machine's locale documents that machine |
| Encoding | Pin the runtime's I/O encoding to UTF-8 explicitly | Box-drawing and any non-ASCII glyph turn into mojibake or an encoding error under a different default, and the result reads as an application bug |
| Character width | Keep ambiguous-width and emoji glyphs out of the fixture unless they are the subject | East Asian wide and ambiguous-width characters occupy one or two cells depending on the terminal's setting, so identical text shifts every column after it |
| Wall clock | Freeze it — inject a fixed timestamp or patch the clock | "Last run 3 minutes ago", dates, and expiry badges move on every capture while the code stands still |
| Elapsed time | Stub measured durations separately from the clock | A frozen clock does not fix `finished in 1.27s`. That is an interval, and it varies with machine load |
| Timezone | Pin `TZ` | The same instant renders as a different local time, and near midnight as a different date |
| Hostname | Set the environment's hostname to a placeholder, or configure the app's display value | Prompts, title bars, and "connected to …" lines embed the build machine's name and publish it |
| Username and home | Pin `USER`, `USERNAME`, `LOGNAME`, and `HOME` to fixed placeholders | Same leak, and any path shown as a home directory differs per machine and per operating system |
| Working directory shown | `cd` to a fixed, known path before capturing — a named directory created inside the temporary root, not the temporary root itself | Temporary directories have random names. If the app prints a prompt, a path, or a file tree, that random name lands in the capture and byte-identity is gone |
| Cursor | Park it deliberately — focus a known widget or move it to a known cell — and disable blink in the renderer | The cursor is a visible block in the image. Its position depends on where the last keystroke left it, and blink gives one state two possible frames |
| Scrollback versus viewport | Decide which you are capturing and say so in the script | A viewport capture shows the final screen; a stream capture shows everything ever printed, including what scrolled away. They answer different questions and never compare |
| Progress indicators | Disable them — most tools take `--no-progress` or `--quiet`, or honour `CI` and `TERM=dumb`. Otherwise capture only after completion | A spinner or bar frame depends on exactly when the capture landed, so one run in ten shows a different picture for identical code |
| Random data | Seed every source: the language RNG, any array or statistics library's RNG, and any seed the application itself accepts | Unseeded values change string widths, which changes wrapping, which changes everything below them |
| Unordered iteration | Sort anything whose order is not guaranteed — map iteration, file globs, set traversal, concurrent completion order | These are stable within a run and unstable across runs or versions, which is the hardest churn to attribute |
| Version and revision strings | Pin any version, build number, or commit SHA the app displays | A header showing the current SHA changes every capture on every commit, so every docs diff looks like a UI change |
| Renderer appearance, image captures only | Pin the font family, size, line height, padding, window chrome, and colour scheme of whatever rasterises the image | A font absent on the next machine substitutes silently and changes every glyph metric on screen |
| Capture timing | Wait for a settled condition — target screen mounted, no pending work, two consecutive identical frames — never a fixed sleep | A sleep is either too short and flakes, or too long and wastes the run, and it never actually knows the app has finished drawing |

The POSIX form below shows the variable list, which is the portable part; set the same values
however your platform sets them.

```bash
env \
  TERM=xterm-256color COLORTERM=truecolor \
  LC_ALL=C.UTF-8 LANG=C.UTF-8 TZ=UTC \
  HOME=/tmp/tui-capture-home USER=user LOGNAME=user \
  COLUMNS=100 LINES=30 \
  <capture command>
```

Record the values you used in the script itself, next to the capture. Six months later the
question is always "why does this look different on my machine", and the answer is in that
list.

## Step 4 — size the terminal

Set explicit columns and rows. A terminal cell is roughly twice as tall as it is wide, so
`cols : 2 × rows` approximates the display aspect ratio — `240 × 68` is close to 16:9.

Size the primary captures so the widest content fits without horizontal scrolling. A
screenshot with a cut-off table column is worse than no screenshot, because it looks like
evidence. Check the widest table in the app and count.

That is the docs size, not the only size. Capture the narrow case separately — see step 5 —
rather than choosing one width and hoping it covers both.

## Step 5 — capture every screen, in every state it has

One image per screen and state, named for the screen and the state rather than numbered:
`tui-welcome.svg`, `tui-report-empty.svg`, `tui-config-error.svg`. Numbered names break as
soon as a screen is inserted, because every later file then names a different picture while
every reference to it stays silently wrong.

Drive the app to each state through its real interaction path — send the keypresses a user
would send — rather than constructing the widget directly. Constructing directly is how a
screenshot ends up showing a state the app cannot actually reach, and an unreachable state
looks perfectly fine while the real one is broken.

Support a flag to capture a single screen. Iterating on one screen should not cost a full run.

### The states worth capturing

The happy path is the state whoever built it has already looked at a hundred times. The bugs
are in the rest.

| State | Capture it because |
| --- | --- |
| Default, populated | It is the baseline every comparison is made against, and the one the docs publish |
| Empty | First-run and zero-result layouts collapse here. A table with no rows often renders as a bare header or a lone border, and placeholder copy is written last and checked never |
| Error | Error surfaces get the least design attention and the most user attention, and they lean hardest on colour, which is exactly where the no-colour case fails |
| Long output that scrolls | Truncation, wrapping, and "and 43 more" behaviour exist only in this state. Decide viewport or stream first, because the two produce different pictures of the same run |
| Narrow terminal | 80×24 is still what a fresh terminal and most SSH sessions give you. A layout that only works at 200 columns is broken for a real share of users, and they see it before you do |
| No colour | Run with the no-colour environment set. It is the only way to see what the interface looks like with hue removed — `visual-verify` check 2 judges the result |
| Reduced colour depth | Force 16 colours and capture again. Styles resolve differently at each depth, so this is a distinct picture rather than a variant of the last one |

Not every screen has every state. Capture the ones it has, and say which do not exist for
that screen rather than silently omitting them — an omission and an absence look identical in
a directory listing.

The narrow, no-colour, and reduced-depth captures usually exist to be audited rather than
published. Produce them, check them, and ship only the populated set to the docs unless the
docs are specifically about accessibility or small terminals.

## Step 6 — write to the right output directory

For a docs refresh, default the output to wherever the docs already keep images
(`docs/img/`, `docs/assets/`, `assets/`, `.github/`), and take a `--out` flag to override. If
the directory already holds captures, match their existing naming rather than renaming the
set — a rename is a docs-wide diff for no gain.

When `visual-verify` is the caller, write into `.visual-verify/before/` or
`.visual-verify/after/` with that skill's naming scheme instead, and do not touch the docs
directory. The two sets have different lifecycles and only one of them is committed.

## Step 7 — wire it into the docs

Reference the images from the README with real alt text describing the screen, not
"screenshot". Alt text is the only version of the image available to a screen reader, to a
text-only client, and to anyone whose images failed to load.

If the project has CI, consider a job that regenerates the captures and fails when they
differ. That turns "the docs are stale" from something nobody notices into a test failure,
which is the only form of documentation rot that reliably gets fixed. It is also the strongest
possible check on step 3: a capture that is not deterministic will fail that job immediately.

## Invocation

The adapted script belongs to the consuming project — its own scripts directory, committed
there. `capture.example.py` stays here as the reference and is never run as-is and never
edited in place: this skill directory is a kit path that the consuming repo must never commit,
and an edit here forks the kit silently.

Keep the script runnable standalone, with no arguments needed for the common case:

```bash
python scripts/capture_screens.py                 # all screens, default out dir
python scripts/capture_screens.py --out docs/img  # custom out dir
python scripts/capture_screens.py --only report   # one screen, fast iteration
```

## Requirements

The application must be launchable or importable by the capture script — usually an editable
install (`pip install -e ".[dev]"` or the equivalent for the project's toolchain). State this
in the script's docstring so the failure mode is obvious rather than looking like a bug in the
app.

Make the script exit non-zero when a capture is missing, blank, or below the size floor. A
capture pipeline that reports success while writing empty files is worse than no pipeline,
because the docs then contain blanks that nobody is watching for.

## Never committed

Skills and agents from this kit are **copied** into a consuming repository's working directory
so that repo's tooling can find them. They are **never committed** to that repository. They
are committed in one place only: this kit. A consuming repository's git history must contain
zero kit files, at any path, forever. A committed copy forks silently, because someone edits
it there and the two versions diverge with nothing to reconcile them; updates stop arriving,
because a copy under version control looks authoritative and nobody re-copies it; and it
re-creates the exact duplication this kit exists to remove, turning one source into many.
Enforcement is local and requires committing nothing: add the kit paths to `.git/info/exclude`
in the consuming repo, which is per-clone, untracked, and needs no commit of its own. Use
`.gitignore` only when a whole team copies the kit and genuinely wants a shared ignore rule —
and note that this is the one line about the kit that does get committed there, so it is a
deliberate trade rather than the default.

The captures split by purpose. Documentation images are produced deliberately, live in the
docs image directory, and **are** committed — they are part of the docs. Verification
captures under `.visual-verify/` are temporary working artefacts, are regenerated on every
run, and are never committed; put that directory in `.git/info/exclude` alongside the kit
paths. So is the throw-away workspace from step 2, if the script ever writes it inside the
repo rather than into a temporary directory.

## Do not

- Do not screenshot against real data, a real home directory, or a real project tree. These
  images end up in a public README, and a leak there is permanent in the git history.
- Do not capture by taking a desktop screenshot or a photograph by hand. It cannot be re-run,
  so it goes stale the first time nobody has an afternoon spare, and nothing marks it stale.
- Do not fix a churning capture by regenerating it and committing the churn. The churn is the
  symptom of an uncontrolled source in step 3; find it, because it will move again.
- Do not crop, retouch, or hand-edit a capture. An edited capture is a claim about the
  interface that the interface does not support, and it audits clean forever.
- Do not add a CI step that installs a terminal emulator, a font set, or a recorder to make a
  capture work. Choose an approach that needs none instead.
- Do not judge the interface here. No remarks about alignment, colour, spacing, or copy —
  `visual-verify` owns that, and an opinion raised during capture is read as a finding.
- Do not capture the same screen in two formats without a second question that needs the
  second format.
- Do not commit kit files or verification captures into the consuming repository.

## Verify

- [ ] Every expected file exists and is non-trivial in size — under about 5 KB of SVG usually
      means the app rendered blank.
- [ ] Each capture contains a distinctive string you know belongs on that screen; grep the SVG
      or the text for it.
- [ ] The capture ran twice and the outputs are byte-identical. Run the second one from a
      different working directory and a different shell, which is what catches an inherited
      variable that the first run happened to satisfy.
- [ ] Every control in step 3 is set explicitly by the script rather than inherited, and the
      values are recorded next to the capture.
- [ ] You opened at least one and looked at it: no text clipped at the right edge, no
      unpopulated table, no spinner caught mid-frame, no error dialog captured by accident.
- [ ] No real data, hostname, username, home path, or temporary directory name appears in any
      capture — grep for the build machine's own values, not just for the fixture's.
- [ ] Every state each screen actually has was captured, and any state that does not exist for
      that screen is named as absent rather than left out.
- [ ] The narrow-terminal and no-colour captures were looked at, not merely produced.
- [ ] Filenames name the screen and the state, never a number, and match any existing scheme
      in the output directory.
- [ ] Docs captures are in the docs image directory with real alt text where they are
      referenced; verification captures are in `.visual-verify/` and are not staged.
- [ ] `git status` in the consuming repo shows no kit file and no verification capture.
