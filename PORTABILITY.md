# Portability

This kit targets Claude Code as its reference runtime, but nothing in the content is bound to
it. This document states what is portable, what is not, and what another runner has to
provide.

## The layered view

| Layer | Portable? | Why |
| --- | --- | --- |
| `skills/*/SKILL.md` | Fully | Markdown with YAML frontmatter. A complete procedure any capable model can follow, with no runtime-specific calls. |
| `agents/*.md` | Content yes, frontmatter partly | The prose below the frontmatter is a plain system prompt. The `tools:` and `model:` keys are Claude Code bindings. |
| `commands/*.md` | Mostly | The prompt body is plain Markdown. The `!` bash substitution and `$ARGUMENTS` placeholder are Claude Code syntax that some runners share and others do not. |
| `hooks/notify.py` | Fully | Stdlib Python, reads JSON on stdin, writes a notification. Any runner that can execute a command can use it. |
| `hooks/hooks.json` | No | Claude Code's event wiring format. Rewrite this one file per runtime; the script it calls stays as-is. |
| `.claude-plugin/*.json` | No | Claude Code plugin packaging. Irrelevant elsewhere and harmless if ignored. |

## What another runner needs to supply

**Skill discovery.** A way to load `SKILL.md` files and match them by their `description`
field. The frontmatter carries `name` and `description` and nothing else that matters.

**Subagents (optional).** Skills that benefit from delegation say so explicitly, name the
agent file to use as the subagent's instructions, and give the tier. Every one of them also
contains the full inline procedure, so a runner with no subagent support loses tokens, not
capability. That is a deliberate design rule, not an accident of how these were written.

**A tier mapping.** Bind `cheap`, `standard`, and `deep` to three models once. The mapping
lives in your runner's config, not in these files.

## Adapting the agent frontmatter

```yaml
---
name: test-runner
description: ...        # used for matching; keep
model: haiku            # Claude Code binding; replace or drop
tier: cheap             # vendor-neutral; keep
effort: low             # Claude Code reasoning-effort hint; drop if unsupported
tools: Bash, Read, Glob, Grep   # Claude Code tool names
---
```

The `tools:` list is a capability statement, not an API. Translate it to whatever your runner
calls the same things:

| Here | Means |
| --- | --- |
| `Bash` | Run shell commands |
| `Read` | Read a file |
| `Write` / `Edit` | Create or modify a file |
| `Glob` | Find files by path pattern |
| `Grep` | Search file contents |
| `Task` | Spawn a subagent |

An unrecognised key in YAML frontmatter is normally ignored, so in practice most runners can
read these files unmodified.

## Adapting the commands

The command body uses three pieces of Claude Code syntax:

| Syntax | Means | If unsupported |
| --- | --- | --- |
| `` !`cmd` `` | Run `cmd` and inline its output before the prompt is sent | Delete the line; the skill re-gathers the same context itself |
| `$ARGUMENTS` | Everything the user typed after the command | Substitute your runner's equivalent |
| `$1`, `$2` | Positional arguments | As above |

The pre-gathered context is an optimisation, not a requirement — every command hands off to a
skill that gathers what it needs anyway.

## Adapting the hooks

`notify.py` takes the event name as `argv[1]` and the payload as JSON on stdin. It tolerates
empty stdin, malformed JSON, and a missing argument, and it always exits 0.

The payload keys it reads, all optional, both snake_case and camelCase accepted:

```json
{
  "session_id": "...",
  "cwd": "/path/to/project",
  "tool_name": "Bash",
  "tool_input": { "command": "pytest -q" },
  "message": "human-facing notification text",
  "source": "startup"
}
```

To wire it into a different runner, call it the same way from that runner's event system:

```bash
echo "$PAYLOAD" | python3 /path/to/claude-kit/hooks/notify.py Stop
```

Event names other than the five in `hooks.json` are accepted and logged under their own name,
so you can wire in events this kit does not know about.

## Known non-portable content

One skill is machine-specific rather than project-specific, and is kept here for version
control rather than reuse:

- **`github-account-switch`** — encodes my two SSH host aliases and their key filenames, and
  the fact that port 22 is firewalled on my network so SSH must route over 443. Useless to
  anyone else without editing. Everything else in this repository is genuinely generic.
