---
name: js-test-harness
description: Set up or debug a JavaScript/TypeScript front-end test suite — Vitest or Jest, node versus jsdom projects, and the environment pins without which tests pass on your machine and fail on CI. Use when adding front-end tests, when a front-end test fails in a way that looks environmental, or when a suite has no runner yet.
---

# Front-end test harness

Covers the part of front-end testing that is not about what to assert — `test-authoring`
owns that — but about the harness underneath it: which environment a test runs in, what the
DOM double lies about, and which machine-dependent values have to be pinned before any date
or layout assertion means anything.

Most of what makes a front-end suite flaky is here, not in the tests.

## Two projects, not one

Split the suite by cost, and default to the cheap half:

| Project | Environment | For |
| --- | --- | --- |
| `pure` | `node` | Value-in, value-out logic — routing, formatting, grouping, parsing, state reducers, anything with no DOM. Fast enough to run without thinking about it. |
| `dom` | `jsdom` | Components, and only where a component is genuinely under test. |

jsdom is paid for, not assumed. A suite that runs everything under jsdom is several times
slower for no coverage gained, and the slowness is what stops people running it.

Vitest expresses this with `test.projects`; Jest with `projects`. Both take a per-project
`environment` and `setupFiles`.

**Route everything through the bundler, not bare node.** If any module reads
`import.meta.env`, `process.env` at module scope, or imports CSS or assets, `node --test`
cannot load it — and that constraint spreads to everything that imports it, which is usually
most of the tree.

## The environment pins

Every one of these is a value that differs between your machine and the runner, and each
produces a test that passes locally and fails in CI — or worse, passes in both while
asserting nothing.

### Timezone

Pin it. `process.env.TZ = 'UTC'` in the config, before the workers start. Any code calling
`toLocaleDateString`, `getHours`, or constructing a `Date` from a date-only string is
zone-sensitive, and the failure is off-by-one-day, which reads like a logic bug.

### Locale

**Pin it separately, and check that you actually did.** An env var (`LANG`, `LC_ALL`) reaches
the workers on Unix and is ignored by Node on Windows, so a locale "pinned" in the config is
often not pinned at all. Set it inside the environment the tests run in — a setup file
imported by every project — and assert somewhere that it took effect.

This is worth being blunt about: a config comment claiming both TZ and locale are pinned,
when only TZ ever was, is how date assertions ship depending on the author's machine. If the
claim is in a comment, verify it rather than believing it.

### Absolute paths

Tests that *read* a source file rather than importing it — CSS/JS agreement checks, label
audits, generated-file drift checks — cannot work out where the source is:

- under jsdom, `import.meta.url` is an `http:` URL (the page's origin), so `readFileSync`
  rejects it;
- `process.cwd()` is wherever the runner was launched from, which differs between
  `npm test` and `npx vitest --root <dir>`, and both are real invocations.

Export an absolute path from the **config**, which runs in Node and knows for certain.

### Timeouts

The default 5s is a measurement of the machine, not of the code. A file that renders a whole
screen — a page mounting a dozen components that each fetch on mount — is an order of
magnitude slower under jsdom than in a browser, and under full worker parallelism the
slowest crosses the default and fails with "Test timed out", which reads exactly like a hung
`await` and is nothing of the sort.

The tell: it passes when run alone, and *which* files fail changes between runs.

Raise the DOM project's timeout to ~20s. That is not slack for slow tests to hide in — a
genuine hang still fails, twenty seconds later. It is the margin between "this code is
wrong" and "this laptop was busy".

## jsdom's silence is worse than its absence

jsdom answers uselessly rather than throwing, so the component looks broken and nothing is
raised. Before concluding a component is at fault, check whether the setup file shims what
it depends on — and add the shim there, not in the test.

The ones that catch everyone:

| API | What jsdom does | What breaks |
| --- | --- | --- |
| `getBoundingClientRect` | returns all zeros | masonry/grid layout packs into one column; tooltips and popovers never position or open |
| `IntersectionObserver` | undefined | lazy lists render nothing, infinite scroll never fires |
| `ResizeObserver` | undefined | anything that measures itself throws on mount |
| `matchMedia` | undefined | theme and breakpoint code throws at module scope |
| `scrollTo`, `scrollIntoView` | undefined or no-op | focus-management assertions silently pass |
| `HTMLCanvasElement.getContext` | returns null, warns | chart and image-export code takes a fallback path you did not mean to test |
| `URL.createObjectURL` | undefined | download and preview flows throw |

`matchMedia` is the one that bites the `node` project too, because theme modules commonly
call it at import time — so even a pure test that transitively imports one needs the shim.

## Setting one up from nothing

1. Add the runner and the DOM library as **devDependencies only**. If the project advertises
   a small runtime dependency count, that claim has to stay true.
2. Create the two projects, with `setupFiles` for each.
3. Pin TZ in the config; pin the locale in a setup file both import.
4. Export the source directory as an absolute path from the config.
5. Write one pure test and one DOM test, and break both on purpose to prove the harness runs
   them.
6. Add the suite to CI in the same job as the build, so a passing build with a failing suite
   is impossible.

## What to check when a front-end test is flaky

In order, because this is roughly the frequency order:

1. Does it pass alone and fail in the full run? → timeout under parallelism, or shared
   module state leaking between files.
2. Does it fail only on CI? → TZ, locale, or a path assumption.
3. Does it assert on a layout number? → `getBoundingClientRect` is returning zeros.
4. Does it pass when the code is deliberately broken? → it asserts nothing. Rewrite it.
5. Did it start failing when an unrelated file was added? → worker scheduling changed;
   see 1.

## Two habits that decide whether the suite is worth having

- **Assert on values, never on counts.** "got 3, wanted 3" passes happily while the three are
  the wrong three, which is the entire failure mode of a filter, a sort, or a facet.
- **Read the source, not the docs, for anything about labels or copy.** A test that reads the
  help file to check the help file agrees with itself forever. Read the component for the
  label, then assert the docs name it.
