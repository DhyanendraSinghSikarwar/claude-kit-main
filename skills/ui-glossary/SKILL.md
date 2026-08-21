---
name: ui-glossary
description: Build and maintain ui_glossary.html — one self-contained page naming every element of a user interface and what it does, derived from the source rather than from a screenshot. Use whenever a project has a user interface of any kind (terminal UI, CLI with subcommands and flags, web front end, desktop app, browser extension, plugin panel) and the glossary is missing or stale, or whenever a change adds, renames, removes, or re-gates a control.
---

# Catalogue the user interface

Produces `ui_glossary.html`: a single page listing every element a person can operate, what it
does, which states it has, and the source file that declares it. It exists so that a new
contributor, a support reply, or a bug report can name a control exactly — "the **Apply**
button in the Filters pane" — instead of describing where it sat on the screen that day.

Placement follows the document canon: the repository root, or `docs/` if the repo already
keeps its prose documentation there. See `repo-doc-set`.

## When a project needs one

Anything a person operates directly qualifies.

| Surface | Why it qualifies |
| --- | --- |
| Terminal UI | panes, widgets, and key bindings, none of which is discoverable from `--help` |
| CLI with subcommands and flags | flags interact and are gated by subcommand; `--help` lists them without saying what they do to each other |
| Web front end | controls appear and vanish with state, and the ones bug reports are about — the error banner, the empty-state action, the admin-only button — are off screen most of the time |
| Desktop application | menus, toolbars, dialogs, and accelerators, the majority of them hidden at any moment |
| Browser extension | the surface is split across a popup, an options page, and context-menu items that never appear together |
| Editor or IDE plugin panel | palette commands are found by typing their name, so the name *is* the interface |

A library with no entry point does not qualify: it has an API reference, and there is no
control to name. Scale the file to the surface — a four-flag CLI is a short table, not an
absent one.

## Delegation

Enumerating declaration sites is grep-and-report, so push it down. If your runtime supports
subagents, spawn one with the body of `../../agents/ui-cataloguer.md` as its instructions
(ignore that file's YAML frontmatter — it is packaging metadata, the prose below it is the
prompt). Tier `cheap` is sufficient; give it read and search tools only.

Assembling the page, wording each *does* sentence, and deciding what counts as one element
rather than three stay here. Those are judgement calls, and a catalogue agent that also writes
prose will pad the table to look thorough.

If your runtime has no subagents, follow the procedure below inline. It is the same work.

## Procedure

### Step 1 — derive the inventory from the source

Read the declarations. Do not write the glossary from memory, from a screenshot, or from
clicking through the running app: a glossary written from what is on screen silently omits
every state that is not currently on screen — error banners, empty states, permission-gated
controls, admin-only panels, anything behind a feature flag. Those are precisely the elements
a bug report is about, because they are the ones nobody can find.

| Surface kind | Elements are declared in | Search for |
| --- | --- | --- |
| Web front end | components, templates, and route tables | `<button`, `<input`, `<select`, `role=`, `aria-label`, `onClick`, component files under the view directory |
| CLI | argument-parser definitions | `add_argument`, `@click.option`, `@click.command`, `cobra.Command`, `clap` builders and derives, `.option(`, `yargs.command` |
| TUI | widget construction and compose methods | `compose(`, widget class instantiation, `addstr`, view or render methods, model definitions |
| Menus and commands | command and menu registrations | `registerCommand`, `contributes.commands`, menu builders, accelerator tables |
| Keybindings | keymap tables | `BINDINGS`, `keymap`, `contributes.keybindings`, `Accelerator`, `bind(` |
| Settings and preferences | the settings schema | `contributes.configuration`, a JSON Schema file, a settings struct or dataclass, the defaults file |
| Browser extension | the manifest plus its pages | `action`, `options_page`, `contextMenus.create`, popup and options markup |

Two things the search alone will get wrong, so check them by reading:

- **Controls rendered in a loop.** One declaration can produce twenty buttons. Record it once,
  with the label written as its pattern (`Remove <tag name>`), not twenty times.
- **Controls declared in one place and gated in another.** The permission check or feature flag
  usually lives away from the widget. Find it; the gate is a recorded field.

Record the commit you are cataloguing at, because the file will claim it:

```bash
git rev-parse --short HEAD
```

### Step 2 — record these fields per element

| Field | Holds | Why it is here |
| --- | --- | --- |
| `id` | a stable kebab-case slug, e.g. `sidebar-filter-field` | it is the anchor target and the citable name; it must survive a relabel, or every existing link breaks |
| Label | the visible text, exactly as rendered | it is what a user reads out to you |
| Accessible name | the name assistive tech announces, **only when it differs from the label** | a control whose accessible name differs from its visible label is a defect, and recording both is how it gets noticed |
| Role | the element's role: button, textbox, tab, menuitem, dialog | it names the interaction contract, which the visual type does not — a `<div>` styled as a button is a finding |
| Type | button, text input, select, checkbox, pane, tab, flag, subcommand, key binding, menu item, toast | how a reader recognises it |
| Region | the pane, screen, page, or dialog it lives in | this is the grouping key, and it is how a user says where something is |
| Does | one sentence, present tense, in the user's terms | "Narrows the list to names containing the typed text", not "calls `setFilter`" |
| States | default, disabled, loading, error, hidden — each with the condition that gates it | "why is this greyed out" is the single most common question a glossary can answer |
| Shortcut | the key binding or accelerator, `—` if none | |
| Source | `path/to/file.ext:LINE` where it is declared | it makes every entry checkable against the tree, and it is what keeps the file honest as the code moves |

If a field is genuinely absent, write `—`. Do not infer it and do not fill it from the running
app; an inferred field is indistinguishable from a verified one a month later.

Where an icon-only control has no accessible name at all, record the field as `none` rather
than `—`. An entry reading "accessible name: none" is a bug report that files itself.

### Step 3 — group by region, index alphabetically

Group rows by region, in the order a user meets them: top-level chrome first, then each pane
or screen in navigation order, then dialogs and transient surfaces last. Alphabetical grouping
is worse for the main body because nobody arrives knowing the name — they arrive knowing where
the thing was.

Put a flat alphabetical index of every element at the top, linking to each row anchor. The two
orderings answer different questions: the grouping answers "what is in this pane", the index
answers "what is the thing called *Apply*".

### Step 4 — write the HTML

| Requirement | Reason |
| --- | --- |
| One file, zero external requests — no CDN, no web font, no remote image | it has to open from a file path on a machine with no network, which is exactly where it gets read: offline, on a locked-down box, from a bare checkout |
| Filter box in plain inline JavaScript, no framework and no build step | the file must survive being opened directly over `file://`; anything needing a build rots the first time nobody runs the build |
| Semantic HTML with a real `<table>`, `<thead>`, `<tbody>` — not a grid of divs | the browser's own find must reach every cell, and it cannot search rows that are virtualised or collapsed |
| Light and dark through `prefers-color-scheme` | it opens beside whatever the reader already had open, and a white flash at midnight gets the file closed again |
| A generated-file banner naming the commit and date it was generated at | it states when the page was last true, so a reader can diff against `HEAD` instead of trusting it |
| A unique `id` and anchor per row | an issue or a support reply must be able to link to one element |
| The element count in the banner | it makes the staleness check a single comparison (Step 5) |

Skeleton — structure and banner only; the stylesheet stays this small on purpose:

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PROJECT — UI glossary</title>
<style>
  :root { --bg: #fff; --fg: #1a1a1a; --muted: #666; --line: #ddd; }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #16181d; --fg: #e8e8e8; --muted: #9aa0a6; --line: #333; }
  }
  body { background: var(--bg); color: var(--fg); max-width: 68rem; margin: 0 auto;
         padding: 2rem 1rem; font: 15px/1.5 system-ui, sans-serif; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border-bottom: 1px solid var(--line); padding: .5rem; text-align: left;
           vertical-align: top; }
  .meta { color: var(--muted); font-size: .85rem; }
  /* Anything further is presentational and optional. */
</style>
</head>
<body>
<h1>PROJECT — UI glossary</h1>

<p class="meta">Generated file — do not edit by hand; regenerate with the
<code>ui-glossary</code> skill.<br>
Commit <code>a1b2c3d</code> · 2026-03-14 · 47 elements</p>

<!-- staleness check: <the count command from Step 5> -> 47 at generation time -->

<input id="q" type="search" placeholder="Filter elements…" aria-label="Filter elements">

<nav aria-label="Index" class="meta">
  <a href="#apply-button">Apply</a> · <a href="#sidebar-filter-field">Filter field</a> · …
</nav>

<h2>Sidebar</h2>
<table>
  <thead>
    <tr><th>Element</th><th>Type</th><th>Does</th><th>States</th><th>Key</th>
        <th>Source</th></tr>
  </thead>
  <tbody>
    <tr id="sidebar-filter-field">
      <td><strong>Filter field</strong><br>
          <span class="meta">textbox · accessible name “Filter projects”</span></td>
      <td>text input</td>
      <td>Narrows the project list to names containing the typed text.</td>
      <td>default; disabled while the list is loading</td>
      <td><kbd>/</kbd></td>
      <td><code>src/ui/Sidebar.tsx:42</code></td>
    </tr>
  </tbody>
</table>

<script>
document.getElementById('q').addEventListener('input', function (e) {
  var q = e.target.value.toLowerCase();
  document.querySelectorAll('tbody tr').forEach(function (row) {
    row.hidden = q !== '' && row.textContent.toLowerCase().indexOf(q) === -1;
  });
});
</script>
</body>
</html>
```

Rows must be visible on load, with hiding done only by the filter. A page that starts with rows
hidden defeats the browser's find, which is the one search guaranteed to work.

### Step 5 — keep it current

| The diff touches | Regenerate? |
| --- | --- |
| a component, template, or widget that renders a control | yes — the element set changed |
| an argument-parser definition: a flag, a subcommand, a default | yes |
| a keymap, accelerator, or binding table | yes — the shortcut is a recorded field |
| a settings or preferences schema | yes — each setting is a control |
| a menu, palette, or context-menu registration | yes |
| a label, string table, or i18n catalogue | yes — the visible label is a recorded field |
| a permission check or feature flag wrapping a control | yes — the gate is a recorded state |
| a file that any `Source` cell points at, in a way that moves the line | yes — the citations are now wrong |
| styling, layout, or colour only | no — no recorded field changed |

**The staleness check.** Compare what the file claims against a fresh count from the source:

```bash
grep -c '<tr id=' ui_glossary.html     # elements the file documents
```

Then re-run the count command recorded in the HTML comment and compare it with the number
recorded beside it. Store both the command and its value at generation time, because a check
nobody can re-derive is a check nobody runs.

Pick a counting command that is exact for this project — one line per declaration site, from
the same search that Step 1 used. If you cannot make it exact, say in the comment what it
counts, and compare against the recorded number rather than against the element count; a
heuristic that overcounts consistently is still a usable signal, one that is only sometimes
wrong is not.

A difference means regenerate. It does not tell you what changed, and it is not meant to.

## Do not

- **Do not invent elements.** Every row traces to a declaration in the tree. A plausible entry
  for a control that does not exist sends the reader hunting for it, which costs more than the
  missing row would have.
- **Do not document a control you could not locate a definition for.** Leave it out and report
  it in your reply as a gap. An entry with no source cell cannot be verified or maintained, and
  it will outlive the control it describes.
- **Do not hand-edit the generated file.** Fix the label, the docstring, or the help text at
  the source and regenerate. A hand edit is silently lost on the next run, and until then the
  file disagrees with the tree while looking authoritative.
- **Do not drive it from screenshots or from clicking around.** See Step 1; the states you
  cannot see are the ones worth documenting.
- **Do not record styling, pixel positions, or colours.** They change every redesign and are
  wrong within a week. A name and a behaviour survive.
- **Do not list internal components, private methods, or state containers.** This is a glossary
  of what a person operates, not a component tree.
- **Do not change an existing `id` when relabelling an element.** Update the label, keep the
  slug; the slug is what links point at.
- **Do not merge two similar controls into one row** to shorten the table. If they can be
  clicked separately they are named separately, which is the whole point.
- **Do not add analytics, a framework, a font, or any other external request.** It has to work
  offline from a file path.

## Verify

- [ ] Every row has a source path and line, and opening that file shows the declaration.
- [ ] The element count in the banner equals the number of rows in the file.
- [ ] Every element the Step 1 search found appears exactly once, or is excluded for a reason
      you can state.
- [ ] The file opens over `file://` with networking off, and the console logs no failed
      request.
- [ ] The filter box narrows the table; with JavaScript disabled the full table still reads.
- [ ] The browser's own find locates a label you know is present — no rows hidden at load.
- [ ] Readable in both light and dark; check by switching the OS setting or emulating it.
- [ ] Every row `id` is unique and every index link resolves to a row.
- [ ] Accessible name and role are recorded wherever they differ from the visible label, and
      icon-only controls with no accessible name are marked `none`.
- [ ] The banner names the commit you actually generated from, and the staleness comment holds
      both the count command and its value.
- [ ] The file sits where this repo's canon puts it: the root, or `docs/`.
