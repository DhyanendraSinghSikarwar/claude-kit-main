# claude-kit

Project-agnostic agents, skills, commands, and hooks shared across all my repositories.

Every project pulls from here rather than carrying its own copy. Nothing in this repository
knows the name of any specific project — if a file mentions one, that is a bug.

## Why this exists

Two of my repos were carrying byte-identical copies of the same eight agents and seven
skills, and a third had drifted into a near-duplicate set with different names. That is the
problem this repository solves: one source, many consumers.

## Install

This repository is a Claude Code plugin marketplace containing a single plugin.

```bash
/plugin marketplace add <path-or-git-url-to-this-repo>
/plugin install claude-kit@claude-kit
```

Once installed the agents, skills, commands, and hooks are available in every session. To
scope it to particular projects instead, list it under `enabledPlugins` in that project's
`.claude/settings.json`.

For a project that needs its own editable copy — pinned, modified, or usable by someone who
does not have the kit — run `/bootstrap` inside that project and choose Working-copy mode.
That copies the selected files in, excludes them from version control, and records what was
copied.

## The non-commit rule

**Kit files are copied into a consuming repository's working directory. They are never
committed to it. They are committed here, and nowhere else. A consuming repository's git
history must contain zero kit files, at any path, forever.**

Three separate things go wrong when a copy is committed, and each fails differently:

- **It forks silently.** The moment a copy is under another repository's version control,
  someone edits it there, and the two versions diverge with nothing to reconcile them.
- **Updates stop arriving.** A committed copy looks authoritative, so nobody re-copies it.
  Every improvement made here stops at that repository's boundary.
- **It re-creates the duplication this kit exists to remove.** One source and many consumers
  is the entire point; a committed copy makes it many sources, which is the problem described
  at the top of this file.

Honouring it costs the consuming repository nothing. Put the kit paths in
`.git/info/exclude`, which is per-clone and untracked, so no commit is needed to ignore them.
Use `.gitignore` only when a whole team copies the kit and genuinely wants a shared rule —
that is the one committed line about the kit, so it is a deliberate trade rather than the
default.

Enforcement is mechanical, because a rule stated only in prose gets ignored the first time it
is inconvenient. Run these from inside the consuming repository, not from the kit — the paths
they write to are that repository's, and in the kit itself the guard exempts the kit's own
tree, so there is nothing there for it to catch:

```bash
GUARD=<path-to-this-kit>/skills/git-sync/scripts/kit_guard.py

python3 "$GUARD" --staged     # blocks a commit containing kit files
python3 "$GUARD" --tracked    # audits a repo that may already have some
python3 "$GUARD" --hook > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

The guard is read-only. It reports and exits with a code; it never unstages anything, because
a guard that silently rewrites someone's staged work is a guard they disable. It also detects
a kit source repository — this one — so the kit's own files are not flagged in it.

## What is in here

### Commands

Thin entry points. Each one gathers the obvious context up front and hands off to a skill.

| Command | Does |
| --- | --- |
| `/commit` | Conventional Commits message from the staged diff |
| `/pr` | PR description for the current branch |
| `/test` | Detect toolchain, run build and tests, report failures as a table |
| `/triage` | Reduce a log dump to distinct error signatures |
| `/dupes` | Find copy-pasted code, and judge which is worth merging |
| `/release` | Pick the version, update the changelog, bump manifests, tag |
| `/validate` | Pre-release correctness review — invariants, API usage, data safety |
| `/bootstrap` | Wire this kit into a project and write its `CLAUDE.md` |
| `/extract` | Convert a PDF or Office file to clean Markdown |
| `/precommit` | The full gate — test, fix, document, changelog, commit, push |
| `/write-tests` | Write tests that can actually fail (`/test` runs them) |
| `/lint` | Run the linters and type checkers this project configures |
| `/docs` | Refresh the seven canonical documents without running the rest of the gate |
| `/visual` | Screenshot the interface, audit it against the docs, fix what it finds |

### Skills

The procedures. Each is written to be followed by any capable model, with or without
subagent support.

| Skill | Does |
| --- | --- |
| `pre-commit-gate` | The ritual before every commit — test, fix, document, changelog, ship |
| `test-authoring` | Write tests, proven by watching each one fail first |
| `js-test-harness` | Front-end test harness — node vs jsdom, and the pins CI needs |
| `sweep-check` | Find every site a new rule has to reach, not just the reported one |
| `python-lint` | Run the project's own checkers, grouped by rule |
| `code-standards` | Derive a codebase's real conventions and match them |
| `css-review` | Token discipline, specificity, dead rules, breakpoints |
| `jupyter-hygiene` | Strip notebook outputs, catch secrets, check execution order |
| `image-to-md` | Image to Markdown — cheap OCR, then structured separately |
| `repo-doc-set` | The seven documents every repo carries, and what belongs in each |
| `visual-verify` | Screenshot, describe, audit against what the docs promise, rectify |
| `ai-disclosure` | `AI.md` plus the commands that reproduce every figure in it |
| `ui-glossary` | `ui_glossary.html` naming every UI element, derived from source |
| `git-sync` | Pull, stage, commit, push — and the commands that are never run |
| `commit-draft` | Commit messages and PR descriptions from a real diff |
| `changelog-release` | Keep a Changelog maintenance and cutting a release |
| `project-bootstrap` | Set a project up to use this kit |
| `test-summary` | Compress a test run to failures plus counts |
| `log-triage` | Group a log into distinct error signatures |
| `dupe-check` | Find and judge duplicate code |
| `pdf-to-md` | PDF to Markdown, text layer or OCR |
| `office-to-md` | Word, Excel, PowerPoint to Markdown |
| `markdown-mermaid` | Full markdownlint ruleset and Mermaid constraints |
| `tui-screenshots` | Deterministic terminal UI screenshots for docs |
| `texture-flatten` | Flatten texture packs into neutral tintable UI tiles |
| `github-account-switch` | Switch the active GitHub account for a repo |

### Agents

Subagent prompts. These exist to keep token-heavy, mechanical work out of the main context —
reading a full diff, parsing a stack trace, OCR-ing a PDF.

| Agent | Tier | Does |
| --- | --- | --- |
| `commit-drafter` | cheap | Reads the diff, writes the message |
| `test-runner` | cheap | Detects the toolchain, builds, tests, reports |
| `test-summarizer` | cheap | Compresses test output to a failure table |
| `log-triager` | cheap | Groups logs into error signatures |
| `dupe-detector` | cheap | Flags near-duplicate blocks |
| `pdf-extractor` | cheap | PDF to Markdown |
| `office-extractor` | cheap | Word and Excel to text |
| `image-extractor` | cheap | OCR plus a caption |
| `scoped-search` | cheap | Read-only search bounded to a subtree |
| `git-runner` | cheap | Runs the git plumbing, decides nothing |
| `ui-cataloguer` | cheap | Enumerates every UI element from the source |
| `screenshot-runner` | cheap | Captures the interface deterministically |
| `release-notes` | standard | Drafts release notes from the diff since the last tag |
| `changelog-scribe` | standard | Changelog entry from the diff plus `PLAN.md` |
| `ui-describer` | standard | Turns a screenshot into an auditable written record |
| `doc-oracle` | standard | Answers from oversized project docs, with citations |
| `test-author` | standard | Writes tests, each observed failing before it passes |
| `lint-runner` | cheap | Detects and runs the configured checkers |
| `notebook-cleaner` | cheap | Inspects and strips `.ipynb` outputs |
| `doc-structurer` | deep | Raw extracted text into structured Markdown |
| `release-validator` | deep | Adversarial pre-release correctness review |
| `bug-fixer` | deep | Finds the root cause behind a failure and fixes it |
| `doc-writer` | deep | Keeps the seven canonical documents true |
| `visual-auditor` | deep | Judges the interface against what the docs promise |

### Hooks

`hooks/notify.py` handles desktop notifications and an activity log. It is dependency-free,
cross-platform, never blocks, and always exits 0 — a broken notifier must not be able to stop
an agent from working.

| Event | Behaviour |
| --- | --- |
| `Notification` | Desktop toast — Claude wants permission or input |
| `Stop` | Desktop toast — the turn is finished |
| `SubagentStop` | Logged only; toasting every subagent trains you to ignore all of them |
| `PreToolUse` | Logged only, for `Bash`, `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Task` |
| `SessionStart` | Logged |

The log is JSON Lines at `~/.claude/claude-kit-activity.jsonl`.

| Variable | Effect |
| --- | --- |
| `CLAUDE_KIT_NOTIFY=0` | No desktop notifications; logging continues |
| `CLAUDE_KIT_LOG=0` | No activity log; notifications continue |
| `CLAUDE_KIT_LOG_PATH` | Move the log |
| `CLAUDE_KIT_TOOL_TOAST=1` | Also toast on every matched tool use — noisy, off by default |

## Model tiers

Skills never name a vendor model. Agents declare a vendor-neutral `tier` alongside whatever
concrete binding the host runtime needs, so the same agent runs anywhere.

| Tier | Meaning | Claude binding |
| --- | --- | --- |
| `cheap` | Mechanical work — parsing, extraction, grouping. No judgement required. | `haiku` |
| `standard` | Writing and synthesis with judgement. | `sonnet` |
| `deep` | Adversarial review, correctness reasoning, finding what tests miss. | `opus` |

To run this kit on another stack, map the three tiers to your models once. Nothing else needs
changing. See `PORTABILITY.md`.

## Conventions

Anything added here must hold to all of these:

1. **Project-agnostic.** No project names, no absolute paths, no organisation-specific
   assumptions. Detect the toolchain; do not assume it.
2. **Skills are self-contained.** A skill states its full procedure. Delegation to a subagent
   is an optimisation the skill offers, never a dependency it requires.
3. **Skills name no vendor models.** Use the tier vocabulary.
4. **Explain the why for anything non-obvious.** A rule without a reason gets ignored the
   first time it is inconvenient.
5. **Every skill ends with a verification step.** A checklist of what to confirm before
   claiming success.
6. **State what not to do.** Most failures in practice are doing too much, not too little.

## Layout

```text
claude-kit/
├── .claude-plugin/
│   ├── plugin.json          plugin manifest
│   └── marketplace.json     marketplace manifest
├── agents/                  one .md per agent: frontmatter + prompt
├── skills/<name>/SKILL.md   one directory per skill, plus any scripts
├── commands/                one .md per slash command
└── hooks/
    ├── hooks.json           Claude Code hook wiring
    └── notify.py            the notifier and activity logger
```

## Licence

MIT. See `LICENSE`.
