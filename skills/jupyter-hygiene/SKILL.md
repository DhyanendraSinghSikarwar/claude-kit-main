---
name: jupyter-hygiene
description: Keep Jupyter notebooks reviewable and safe to commit — strip stored outputs, catch secrets captured in output, check execution order and seeding, and decide when a notebook should become a module instead. Use whenever a .ipynb is committed, reviewed, or diffed, or when notebook diffs are unreadable.
---

# Notebook hygiene

Makes a `.ipynb` safe and cheap to keep in version control. A notebook is JSON with its
outputs stored inline, so the file is not what you see in the browser: it carries base64 image
blobs, full stdout, and an HTML table for every dataframe anyone printed.

Three consequences, in the order they cost you:

1. **Diffs become unreadable.** Change one line and the diff shows a re-encoded PNG. Review
   stops happening, which is worse than review being hard.
2. **Secrets get committed.** An output captures whatever was on screen — an API key echoed
   by a config cell, a row of customer data, a token in a traceback. Nobody looks at outputs
   in a diff, so this is the least-noticed way credentials reach a remote.
3. **Context is consumed by noise.** Reading a notebook to answer a question about its code
   pulls in every stored output too.

## Delegation

Inspection is mechanical — reading JSON and counting. Spawn a subagent with the body of
`../../agents/notebook-cleaner.md` (tier `cheap`) and act on its report. If your runtime has
no subagents, follow the procedure below inline, reading the JSON with a tool rather than
opening the notebook into context.

## Step 1 — decide what this notebook is for

The right treatment depends entirely on this, so settle it before touching anything.

| Kind | Outputs | Because |
| --- | --- | --- |
| Working notebook — exploration, analysis in progress | Strip before every commit | Outputs are regenerable, and they are the whole diff problem |
| Published artefact — a rendered report, a tutorial, a documented example | Keep | The output *is* the deliverable; stripping it destroys the thing |
| Test or CI fixture | Keep only if a test asserts on them | Otherwise it is a working notebook |

When it is not obvious, look at where the file lives and what the project's docs say about
it. Ask rather than guess — stripping a published example silently deletes its content.

## Step 2 — strip outputs on working notebooks

Use a tool the project already has, so the result matches what its own hooks produce:

```bash
nbstripout notebook.ipynb
# or
jupyter nbconvert --clear-output --inplace notebook.ipynb
```

Make it automatic rather than remembered. A rule that depends on someone running a command
before every commit fails on the commit that matters:

```bash
# once per clone — strips outputs on the way into the index, leaves your working copy intact
nbstripout --install
```

That writes a filter into `.git/config` and `.gitattributes`. Alternatively add the check to
the project's `.pre-commit-config.yaml`, which is shared and therefore applies to everyone.

Never strip cell source. Stripping removes outputs; touching source is a code change wearing
a cleanup's clothes, and it lands in a diff nobody is reading closely.

## Step 3 — scan outputs for secrets before they are stripped

Do this **first**, in the order given. Once outputs are stripped from the working copy the
evidence is gone, and if the notebook was already committed the secret is in history whether
or not the current file still shows it.

Search output text for: `api[_-]?key`, `secret`, `token`, `password`, `Bearer `, `AKIA`,
`-----BEGIN`, and connection strings carrying credentials.

If a match reaches a remote, the credential is compromised. **Rotate it.** Removing the file,
amending the commit, or rewriting history does not un-publish it — anyone who fetched has it,
and forges keep unreferenced objects. Deleting without rotating produces a repo that looks
clean and a key that still works.

## Step 4 — check execution order

`execution_count` should run `1..n` down the notebook. When it does not — `1, 2, 7, 3` — cells
were run in an order the file does not record, so the stored results correspond to a state
nobody can reproduce by running top to bottom.

Report the actual sequence. The fix is to restart and run all, then re-strip — but that
executes the notebook, so confirm it is safe to run before doing it. A cell that writes to a
database or calls a paid API is not safe to re-run casually.

## Step 5 — determinism

A notebook whose results change between runs cannot be reviewed, because nobody can tell an
intended change from noise.

| Source | Fix |
| --- | --- |
| Unseeded randomness | Set the seed for every library in play — the stdlib, the array library, the ML framework — in the first cell |
| Reading from a path outside the repo | Parameterise it, or document the fixture and where it comes from |
| Absolute local paths | Relative paths from the notebook, or a config value |
| The current date or time | Pin it where the analysis depends on it |

## Step 6 — know when it should stop being a notebook

A notebook earns its format while the shape of the work is still unknown. Past that point it
is a module in a worse editor. Move logic into an importable module, tested with the
`test-authoring` skill, and leave the notebook as the narrative that calls it, when any of
these hold:

- The same function is pasted into a second notebook.
- Something depends on its output in production or on a schedule.
- It is long enough that cells must be run in a specific order to work.
- You want a test for something inside it.

Migrating is real work with its own review. Note it in `ROADMAP.md` rather than doing it
mid-commit.

## Do not

- Do not open a notebook's full JSON into context to inspect it. That is the cost this skill
  exists to avoid, and one plot can be hundreds of kilobytes of base64.
- Do not strip a published notebook to make a diff smaller.
- Do not commit a notebook with outputs "just this once" — the filter is per-clone and the
  next person will not have it.
- Do not fix non-linear execution by editing `execution_count` by hand. It records what
  happened; editing it makes the file lie.
- Do not delete a leaked credential and move on without rotating it.

## Verify

- [ ] The notebook's kind was decided before anything was stripped.
- [ ] Outputs were scanned for secrets *before* stripping, and any match was rotated.
- [ ] Cell sources are byte-identical after any strip.
- [ ] `execution_count` runs in order, or the deviation is reported.
- [ ] Seeds are set for every source of randomness the notebook uses.
- [ ] Stripping is automatic — via `nbstripout --install` or the project's pre-commit config
      — not dependent on someone remembering.
- [ ] A published notebook still has its outputs.
