---
name: project-bootstrap
description: Set up a new or existing project to use this kit — select the relevant agents and skills, decide whether they are referenced in place or copied into the working directory, keep any copies out of version control, and write a starter CLAUDE.md (or equivalent agent instructions file). Use when starting a new repo, when a repo has no agent configuration yet, when a copied kit needs refreshing or untracking, or when the user asks to "set up Claude here" or "add the kit to this project".
---

# Bootstrap a project

Wires this kit into a project and writes the project's agent instructions file. Runs once
per repository. The result should be a project where the right agents and skills are
available and the instructions file says only what is true about *this* project.

## The non-commit rule

Read this before copying anything, because it constrains how the copy is done.

Skills and agents from this kit are **copied** into a consuming repository's working directory
so that repo's tooling can find them. They are **never committed** to that repository. They
are committed in one place only: this kit. A consuming repository's git history must contain
zero kit files, at any path, forever.

Three reasons, each failing differently:

- A committed copy forks silently. The moment it is in another repo's history someone edits
  it there, and the two versions diverge with nothing to reconcile them.
- Updates stop arriving. A copy under version control looks authoritative, so nobody
  re-copies it, and every improvement made here stops at the repo boundary.
- It re-creates the exact duplication this kit exists to remove. The whole purpose is one
  source and many consumers; a committed copy makes it many sources.

Enforcement is local and requires committing nothing: add the kit paths to `.git/info/exclude`
in the consuming repo, which is per-clone, untracked, and needs no commit of its own. Use
`.gitignore` only when a whole team copies the kit and genuinely wants a shared ignore rule —
and note that this is the one line about the kit that does get committed there, so it is a
deliberate trade rather than the default.

The rule covers the kit's own files and nothing else. Everything the project produces with
the kit's help — its `CLAUDE.md`, its documents, its changelog, its tests — belongs to the
project and is committed normally.

## Step 0 — decide where the files live

Ask the user which they want, unless it is already obvious from the repo. The distinction is
where the files sit, not what they are allowed to do: both modes run identical content.

| Mode | Where the files are | Choose when |
| --- | --- | --- |
| **Reference** | The kit stays installed globally, as a plugin or a shared directory. Nothing is copied; the project only gets an instructions file. | Default. Updates to the kit arrive automatically, and there is nothing in the working directory that has to be kept out of git. |
| **Working-copy** | The selected agents and skills are copied into the project's working directory, and excluded from version control. | The project needs a pinned or locally modified set, is worked on by someone who does not have the kit installed, or must work offline. |

Working-copy costs more than it looks. The copy goes stale the moment the kit moves, it has to
be excluded and kept excluded, and it is the only mode in which the non-commit rule can be
broken at all. The exclusion, verification, and marker steps below are not follow-ups to the
copy — they are part of it. Choose Reference unless something above forces the copy.

## Step 1 — read the project before writing anything

Do not generate a generic instructions file. Gather these facts first:

1. **Language and toolchain** — from `pyproject.toml`, `go.mod`, `package.json`,
   `Cargo.toml`, `*.csproj`, `pom.xml`, `Gemfile`.
2. **How to build, test, and lint** — from a `Makefile`, `justfile`, `noxfile.py`, npm
   scripts, or the CI workflow in `.github/workflows/`. The CI workflow is the most reliable
   source, because it is the set of commands that actually has to pass.
3. **Layout** — where source, tests, docs, and scripts live. Note anything unusual; skip
   what a reader could guess.
4. **Conventions already in use** — read `git log --oneline -30` for the commit style, and
   check for `.editorconfig`, linter configs, and formatter settings.
5. **What the project is for** — one sentence, from the README.
6. **Whether the kit has been here before** — a `.claude/` directory, or kit files tracked in
   git from an earlier attempt. Step 3 says what to do about tracked ones; find them now,
   because a repo that already tracks them needs fixing before anything is copied on top.

If a fact is not discoverable, ask the user rather than guessing. A confidently wrong build
command in an instructions file is worse than an absent one, because it gets trusted.

## Step 2 — select agents and skills

Do not enable everything. Every enabled item costs context in every session, and a long list
of irrelevant capabilities makes the relevant ones harder to find.

Always relevant:

- `commit-draft` / `commit-drafter` — every repo has commits.
- `scoped-search` — every repo benefits from bounded search.
- `markdown-mermaid` — every repo has Markdown.

Relevant when the condition holds:

| Enable | When |
| --- | --- |
| `test-summary`, `test-runner`, `test-summarizer` | the project has a test suite |
| `bug-fixer` | failures are expected to be diagnosed and fixed in place rather than handed back to a human |
| `log-triage`, `log-triager` | the project produces logs or has CI that fails verbosely |
| `dupe-check`, `dupe-detector` | the codebase is large enough for copy-paste to accumulate |
| `changelog-release`, `release-notes` | the project is versioned or tagged |
| `changelog-scribe` | the changelog is written as work lands rather than only at release time |
| `release-validator` | the project writes to user data, ships to others, or has a public API |
| `pre-commit-gate`, `git-runner` | the project is actively maintained and each commit should carry the code, its documentation, and its changelog entry together |
| `git-sync` | the repo has a remote and is worked on from more than one clone or machine |
| `repo-doc-set`, `doc-writer` | anyone other than the author will read this repo, or its documents already drift from the code |
| `ai-disclosure` | any part of the repo was written with AI assistance and the repo is public or shared |
| `pdf-to-md`, `office-to-md`, `image-extractor` | the project ingests documents |
| `tui-screenshots` | the project has a terminal UI or CLI shown in docs |
| `ui-glossary`, `ui-cataloguer` | the project has a user interface of any kind — terminal UI, CLI with subcommands and flags, web front end, desktop app, extension |
| `visual-verify`, `screenshot-runner`, `ui-describer`, `visual-auditor` | that interface can regress visually, and a change is expected to be looked at before it ships |

The agents listed beside a skill are an optimisation, not a requirement: every skill states its
full procedure inline, so a runtime without subagents loses tokens rather than capability. If
the project's runner has no subagent support, take the skills and skip the agents.

Present the selection and the reason for each before writing anything, and let the user cut
it down.

## Step 3 — create the structure

Under Reference mode, only the instructions file is created — skip to step 4. Everything
below is Working-copy mode, and all four parts of it happen in the same pass.

### Copy the files

Create the agent directory the project's runner expects and copy the selected files in. For
Claude Code that is:

```text
.claude/
├── agents/          one .md per agent, YAML frontmatter + prompt
└── skills/
    └── <name>/
        └── SKILL.md
```

```bash
KIT=<path-to-this-kit>
mkdir -p .claude/agents .claude/skills
cp "$KIT"/agents/test-runner.md .claude/agents/
cp -R "$KIT"/skills/test-summary .claude/skills/
```

Copy only what step 2 selected. A wholesale copy re-imports everything the user just chose to
leave out, and that context cost is paid in every session afterwards.

Other runners use different paths for the same content. Check the runner's documentation
rather than assuming this layout; the file *contents* are portable even where the
directory names are not.

### Exclude them from version control

This is part of copying, not an optional follow-up. A copy that exists for even one commit
without an exclusion is a single `git add -A` away from breaking the non-commit rule
permanently, and the break is only visible later, when someone else's clone has the files.

```bash
cat >> .git/info/exclude <<'EOF'

# claude-kit working copy — copied in, never committed
/.claude/agents/
/.claude/skills/
EOF
```

`.git/info/exclude` rather than `.gitignore` because it is per-clone and untracked: honouring
the rule costs no commit at all, so there is nothing to review, nothing to merge, and no way
for the exclusion itself to become the one kit-shaped thing in the history. The leading `/`
anchors each pattern to the repo root, so a directory of the same name deeper in the tree is
unaffected.

Two cases need care:

- **The project has its own agents or skills alongside the copied ones.** Exclude the copied
  paths individually instead of the whole directory. A blanket rule would hide the project's
  own files from git too, and they would silently never be committed:

  ```bash
  for p in .claude/skills/test-summary/ .claude/agents/test-runner.md; do
    printf '/%s\n' "$p" >> .git/info/exclude
  done
  ```

- **A whole team copies the kit into this repo.** Then `.gitignore` is the deliberate
  alternative, because every clone needs the same rule and `.git/info/exclude` cannot be
  shared. Say plainly that this is the one line about the kit that does get committed, so it
  is a trade the team is making, not the default.

Do not exclude `.claude/` wholesale. `.claude/settings.json` is the project's own file and is
normally committed; a blanket rule sweeps it out of git along with the kit files, and nobody
notices until the setting it held stops applying on a fresh clone.

An exclusion stops `git add -A` from noticing the copy; it does not stop `git add -f` or a path
added by name. Install the mechanical half of the rule in the same pass:

```bash
python3 "$KIT"/skills/git-sync/scripts/kit_guard.py --hook > .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
python3 "$KIT"/skills/git-sync/scripts/kit_guard.py --tracked   # audit what history holds
```

The hook lives in `.git/hooks/`, which git never commits, so the enforcement is as local and
uncommitted as the rule it enforces. If the repo already has a `pre-commit` hook, append the
guard's `--staged` call to it instead of overwriting — a guard that clobbers someone else's
hook is uninstalled the same day. The `--tracked` run is the audit half: it reports kit files
an earlier attempt already put in the index, which the next section deals with.

### Verify nothing is tracked

Immediately after copying, before anything else is written:

```bash
git status --porcelain                             # none of the copied paths may appear
git ls-files -- .claude/agents .claude/skills      # must print nothing
git ls-files -- '*SKILL.md' '*agents/*.md'         # catches an earlier attempt at another path
```

The third command matters because a previous bootstrap may have used a different directory, and
kit files anywhere in the history break the rule just as thoroughly as kit files under
`.claude/`.

If anything is tracked, stop and untrack it before continuing. Add the exclusion first —
otherwise the next `git add -A` puts the files straight back:

```bash
git rm -r --cached .claude/agents .claude/skills
git commit -m "chore: stop tracking copied claude-kit files"
```

`--cached` removes them from the index only, so the working files survive and the project keeps
working while git stops watching them. Tell the user before making that commit; it is a commit
in their repository, not yours.

Those files remain in every commit made before the removal. Purging them from history —
`git filter-repo`, BFG — invalidates every existing clone and every open branch, so it is a
decision for the repo's owner. Report that the history still contains them and stop. Do not
rewrite history unasked.

### Record which version was copied

A copy nobody can date is indistinguishable from a fork. Write one marker inside each copied
skill directory, so the exclusion already covers it:

```bash
for d in .claude/skills/test-summary; do   # name each copied directory; do not glob the parent
  {
    printf 'kit-version:   %s\n' "$(git -C "$KIT" describe --tags --always --dirty)"
    printf 'kit-commit:    %s\n' "$(git -C "$KIT" rev-parse HEAD)"
    printf 'copied-on:     %s\n' "$(date -u +%Y-%m-%d)"
    printf 'copied-from:   %s\n' "$KIT"
    printf 'copied-agents: %s\n' ".claude/agents/test-runner.md"
  } > "$d"/.kit-version
done
```

`date -u +%Y-%m-%d` rather than `date -I`, because `-I` is a GNU extension and BSD `date` on
macOS rejects it — leaving the field empty in a marker that otherwise looks written.

Inside each copied directory, never in the `.claude/skills/` directory that holds them. The
commit guard reads a marker as proof that everything beneath it came from the kit, so a marker
one level up brands the project's own skills as kit files and blocks every commit that touches
them. Copied agents are recorded by filename in that same marker for the same reason — a marker
in `.claude/agents/` would flag the project's own agents — and they need none of their own,
because a copied agent is already identified by its frontmatter `name`.

Use a dotfile name so a loader globbing for `SKILL.md` or `*.md` never picks it up as content.
The local path in `copied-from` is fine here and nowhere else: this file is untracked, and the
path is exactly what the refresh needs.

To refresh a working copy later, compare it against the kit before overwriting anything:

```bash
git -C "$KIT" describe --tags --always            # is the kit ahead of the marker?
diff -ru -x .kit-version "$KIT"/skills/test-summary .claude/skills/test-summary
```

`-x .kit-version` because the marker lives inside the copied directory and has no counterpart
in the kit, so without it every comparison reports a difference that is not one.

An empty diff means a faithful copy; re-copy and rewrite the marker. Any diff is a local edit,
and it needs a decision rather than an overwrite: if the change is generally useful it belongs
in the kit, and if it is specific to this project it belongs in the project's instructions
file. What it must not become is a permanent private fork nobody remembers making.

### Do not

- Do not copy the whole kit "to be safe". Unselected files still load, still cost context, and
  still have to be excluded and refreshed.
- Do not copy first and exclude later. The gap is where the rule gets broken.
- Do not commit the copied files to make CI or another contributor's clone work. Install the
  kit there instead, or switch that repo to Reference mode.
- Do not edit a copied skill in place as a substitute for fixing it here. That is the silent
  fork the rule exists to prevent.
- Do not delete a marker file you cannot explain. An undated copy is the harder problem.

## Step 4 — write the instructions file

Write `CLAUDE.md` at the repo root (or the file the project's runner reads). Keep it under
roughly 100 lines. It is loaded into every single session, so length here is a permanent tax.

Include, in this order:

1. **What this project is** — one or two sentences.
2. **Commands** — the exact build, test, lint, and run commands, copy-pasteable. This is the
   highest-value section by a wide margin; get it from step 1 and verify each one runs.
3. **Layout** — only the non-obvious parts. Do not paste a full directory tree.
4. **Conventions** — commit style, formatting, naming, error-handling patterns that a
   contributor would otherwise get wrong.
5. **Invariants and constraints** — what must never break. Data that must not be destroyed,
   APIs that must stay compatible, files that are generated and must not be hand-edited.
   The `release-validator` agent reads this section directly, so it earns its space.
6. **Gotchas** — the things that have already cost someone an hour.

Under Working-copy mode, add one line stating that the kit files under the agent directory are
a copy, are excluded from version control, are never committed, and that `.kit-version` records
which version they came from. Without that line the next contributor sees files git does not
track, assumes it is an oversight, and helpfully commits them.

Deliberately exclude:

- Anything already obvious from the file tree or the README.
- General coding advice that is not specific to this project.
- Aspirational rules nobody follows. An instructions file that describes a fiction gets
  ignored wholesale, including the true parts.

## Step 5 — verify

- [ ] Every command in the instructions file has been run and works.
- [ ] Under Working-copy mode, every copied file parses: YAML frontmatter is valid and `name`
      matches the directory or filename.
- [ ] Under Working-copy mode, the kit paths are in `.git/info/exclude` — or in `.gitignore`
      as a deliberate team decision the user agreed to — and `git status` shows none of them.
- [ ] The pre-commit guard is installed at `.git/hooks/pre-commit` and `kit_guard.py --tracked`
      exits zero.
- [ ] No kit file is tracked, at any path: `git ls-files` for the agent directories and for
      `*SKILL.md` both come back empty.
- [ ] Anything found tracked was untracked with a cached removal, that removal was committed,
      and the user was told the files remain in the history.
- [ ] A `.kit-version` marker exists inside each copied skill directory — not in the directory
      that contains them — and names the kit version, commit, and date.
- [ ] `.claude/` was not excluded wholesale, so the project's own settings file is still
      tracked.
- [ ] No secrets, absolute local paths, or machine-specific details were written into the
      instructions file.
- [ ] `.gitignore` covers anything the kit generates that should not be committed.
- [ ] The instructions file is under ~100 lines.

## Step 6 — report

Tell the user, briefly: the mode chosen, what was enabled and what was skipped, and anything
you had to ask about or could not determine. If a build or test command could not be verified,
say which one — an unverified command is the one thing here most likely to mislead later.

Under Working-copy mode, add three facts: the kit version recorded in the marker, that
`git status` and `git ls-files` both confirm nothing kit-shaped is tracked, and — if an
earlier attempt had committed kit files — that they were untracked but remain in the history,
which is the owner's call to rewrite or leave.
