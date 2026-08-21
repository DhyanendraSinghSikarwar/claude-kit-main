---
name: changelog-release
description: Maintain a Keep a Changelog file and cut a release — pick the next semantic version from the actual diff, write the entry, tag, and draft release notes. Use when the user asks to update the changelog, cut a release, bump the version, or prepare release notes.
---

# Changelog and release

Two related jobs that share the same source of truth, the diff since the last tag:

- **Update the changelog** — add entries under `## [Unreleased]` as work lands.
- **Cut a release** — choose the version, promote `Unreleased`, tag, and publish notes.

Do only what was asked. Adding entries does not imply cutting a release.

## Delegation

For the prose of the release notes, if your runtime supports subagents, spawn one with the
body of `../../agents/release-notes.md` as its instructions (ignore that file's YAML
frontmatter). Tier `standard` — this is writing, not parsing. Version selection and the file
edits stay here, because they are mechanical and must not be improvised.

## Format

Follow Keep a Changelog 1.1.0. Newest release first, `Unreleased` at the top.

```markdown
# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-03-14

### Added

- Description of a new capability, in terms of what a user can now do.

### Fixed

- The symptom a user would have seen, not the internal cause.

[Unreleased]: https://github.com/OWNER/REPO/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/OWNER/REPO/compare/v1.1.0...v1.2.0
```

The six permitted section headings, in this order: **Added**, **Changed**, **Deprecated**,
**Removed**, **Fixed**, **Security**. Omit any that are empty. Do not invent new ones —
"Internal" and "Chore" do not belong in a user-facing changelog, and if a change is worth
recording only for developers, it belongs in the commit history rather than here.

Dates are ISO-8601 (`YYYY-MM-DD`). Versions are link references at the bottom of the file so
each one is clickable to its compare view.

## Adding entries

### Step 1 — find what is new

```bash
git describe --tags --abbrev=0          # last release tag
git log <tag>..HEAD --oneline
git diff <tag>..HEAD --stat
```

Read the actual diff for anything whose subject line is vague. Commit subjects lie by
omission; the diff does not.

### Step 2 — write one line per user-visible change

Write for someone who uses the project and has not read the code. Describe the effect, not
the implementation.

- Good: "Country names in any language now collapse to a single tag."
- Bad: "Added `CountryAliasCatalog`."

Rules:

- One line per change. If a line needs a second sentence, it is probably two changes.
- Skip refactors, formatting, test-only changes, and dependency bumps that change nothing a
  user can observe. A changelog that lists every commit is a `git log` with extra steps.
- Reference issues or PRs at the end where they exist: `(#142)`.
- Never edit an already-released section. It is a historical record. Corrections go in the
  next release.

## Cutting a release

### Step 1 — choose the version from the diff

Compare against the last tag and apply the first rule that matches:

| Bump | When the diff contains |
| --- | --- |
| **major** (`2.0.0`) | any removal or incompatible change to a public API, CLI flag, config key, or on-disk format |
| **minor** (`1.3.0`) | new functionality, added backwards-compatibly |
| **patch** (`1.2.1`) | only bug fixes and internal changes |

If the current version is `0.y.z`, the project is pre-1.0 and the API is not yet stable:
breaking changes bump the **minor**, everything else bumps the patch. Say so explicitly when
you propose the version, because it is the most commonly misapplied rule in SemVer.

State the proposed version and the single change that justified it, then get confirmation
before writing anything. Version numbers are permanent once pushed.

### Step 2 — update the changelog

1. Change `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` using today's date.
2. Add a fresh empty `## [Unreleased]` above it.
3. Update the link references at the bottom: point `[Unreleased]` at `vX.Y.Z...HEAD` and add
   a `[X.Y.Z]` line comparing against the previous tag.

### Step 3 — bump the version wherever it is declared

Find every place the version lives and update all of them. Missing one produces a package
that reports the wrong version, which is confusing and hard to notice.

| File | Field |
| --- | --- |
| `pyproject.toml` | `version` under `[project]` or `[tool.poetry]` |
| `package.json` | `version` |
| `Cargo.toml` | `version` under `[package]` |
| `*.csproj` | `<Version>` |
| `build.yaml`, `manifest.json` | plugin-specific version fields |
| `__init__.py`, `version.go`, `version.ts` | a `__version__` or `Version` constant |

Search for the previous version string across the repo to catch the ones not in this table:

```bash
git grep -n "1\.2\.0" -- . ':!CHANGELOG.md'
```

Do not update a lockfile by hand; regenerate it with the project's own tool.

### Step 4 — commit and tag

```bash
git add -A
git commit -m "chore(release): vX.Y.Z"
git tag -a vX.Y.Z -m "vX.Y.Z"
```

Use an annotated tag (`-a`), not a lightweight one, so `git describe` and the release
tooling behave. Match the existing tag prefix — check `git tag --list | tail -5` before
assuming `v`.

Do **not** push unless the user asked you to. Pushing a tag is effectively irreversible on a
shared remote.

### Step 5 — draft the release notes

The changelog entry and the release notes are not the same document. The changelog is terse
and cumulative; the release notes are standalone and lead with what demands action.

Order: **Breaking** first and unmissable, then Added, Changed, Fixed. For each breaking
change, state the old form, the new form, and what happens to existing data or configs if the
user does nothing. End with a compatibility line naming the minimum runtime or platform
version, and note if it changed.

### Step 6 — verify

- [ ] The version in the changelog, the tag, and every manifest all match.
- [ ] The date is today, in ISO-8601.
- [ ] Link references at the bottom of the changelog resolve and point at the right compare.
- [ ] No previously released section was modified.
- [ ] Every entry traces to something in the diff.
- [ ] The tag is annotated and matches the repo's existing prefix convention.

## If the project has no changelog yet

Create one, but do not reconstruct the entire history — a fabricated backfill is worse than
no history. Start with an `Unreleased` section plus one entry covering the current release,
and note the starting point:

```markdown
## [1.0.0] - 2026-03-14

Initial changelog. For changes before this point, see the commit history.
```
