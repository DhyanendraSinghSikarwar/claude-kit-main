---
name: git-sync
description: The safe mechanics of moving work between the working tree and the remote — fetching, merging or rebasing, resolving conflicts, staging, committing, and pushing. Use whenever work needs to be pulled, staged, committed, or pushed, and whenever a push is rejected or a merge conflicts.
---

# Sync a branch with its remote

Moves work between the working tree and the remote and reports what happened, in a fixed
report shape. Produces at most one commit and one push per run.

These operations are mechanical — fixed command sequences with no judgement in them — which
is why they belong to the cheap tier. They are also the only operations here that can destroy
work that exists nowhere else. Both facts point the same way: this is a fixed
procedure, run exactly as written, with an explicit list of commands that are never run. Do
not substitute a command you believe is equivalent. The commands below were chosen for what
they refuse to do, not only for what they do.

## Delegation

If your runtime supports subagents, spawn one with the body of `../../agents/git-runner.md`
as its instructions (ignore that file's YAML frontmatter — it is packaging metadata, the
prose below it is the prompt). Tier `cheap` is sufficient and correct, because the delegation
is scoped to the parts with no judgement left in them: the runner executes pre-flight, the
fast-forward update, staging, commit, and push, and reports output.

It refuses `git rebase` and any non-fast-forward merge by design, so a branch whose history
has diverged comes back to you unmerged. You make the shared-or-private call in Step 3, run
the merge or rebase yourself, and hand the tree back for staging onward. Do not re-issue the
instruction with firmer wording; the refusal is the agent working, not failing.

If your runtime has no subagents, follow the procedure below inline. It is complete on its
own; delegation keeps `git diff` output out of the main context and changes nothing else.

Take the commit message from the `commit-draft` skill. Do not compose one here.

## Step 1 — pre-flight

Run all of these before touching anything, and read every result. Each one rules out a
distinct way the rest of the procedure goes wrong.

```bash
git rev-parse --is-inside-work-tree                    # is this a repo at all
git rev-parse --abbrev-ref HEAD                        # branch name, or "HEAD" if detached
git rev-parse --abbrev-ref --symbolic-full-name @{u}   # upstream; non-zero exit = none
git status --short --branch
git stash list
# an unfinished merge / rebase / cherry-pick / revert — `git status --short` never shows one
ls "$(git rev-parse --git-dir)" | grep -E 'MERGE_HEAD|CHERRY_PICK_HEAD|REVERT_HEAD|rebase-'
```

| Result | Means | Do |
| --- | --- | --- |
| Not a work tree | No repo here, or you are above it | Stop and say so. Do not run `git init` |
| `HEAD` from `--abbrev-ref HEAD` | Detached HEAD | Stop. Commits made here are reachable from nothing and are lost at the next checkout |
| Non-zero from `@{u}` | Branch tracks no remote | Skip the update step; set tracking on the first push |
| No remotes at all (`git remote`) | Local-only repo | Normal. Say it once, skip update and push, commit as usual |
| `git status --short` non-empty | Uncommitted work present | Expected before a commit; a blocker before any reset or checkout |
| `git stash list` non-empty | Something is stashed | Report every entry, with its message and date |
| That `ls` prints a name | A merge, rebase, cherry-pick, or revert is half-finished | Stop. Conclude or abort it deliberately first — a conflict-free merge in progress shows in none of the commands above, so committing now finishes someone else's merge under your message |

A stash check is not optional politeness. A forgotten stash is the most common way work
disappears without anyone noticing it is gone: the changes are not in the tree, not in the
log, and not in any diff you will read, so the branch looks finished while a piece of it sits
in a queue nobody prints. Report stashes; never drop, pop, or apply one that you did not
create in this run.

## Step 2 — never commit on the default branch

Detect the default branch. Do not assume it is called `main` — plenty of repositories are
still on `master`, and `trunk` and `develop` are both in use. Guessing wrong either trips
branch protection at push time, after all the work, or worse, does not trip it and commits
straight to the branch everyone else builds from.

```bash
git symbolic-ref --quiet --short refs/remotes/origin/HEAD  # e.g. origin/main
git remote set-head origin --auto                          # fallback: ask, then cache it
git branch --list main master trunk develop                # last resort: no remote at all
```

The first command is local and free because the answer was cached at clone time. The second
makes one network call and repairs the cache, so run it only if the first prints nothing.

If `HEAD` is on the default branch, create a branch before doing anything else:

```bash
git switch -c <type>/<short-description>
```

Use `git switch`, not `git checkout -b`. `git checkout` is overloaded — the same command
switches branches and restores files — so a mistyped branch name that happens to match a path
silently discards your edits to that path instead of creating a branch. `git switch` has no
path mode and can only fail loudly.

Committing directly to the default branch is permitted only when the user has said so in this
session. Their earlier habit of doing it is not that permission.

## Step 3 — update before working

```bash
git fetch origin --prune
git log --oneline HEAD..@{u}     # incoming: commits the remote has and you do not
git log --oneline @{u}..HEAD     # local-only: commits you have and the remote does not
```

`--prune` deletes remote-tracking refs for branches that no longer exist on the remote. Stale
refs make `@{u}` resolve to something that was deleted weeks ago, so the two `git log`
commands above quietly answer a question about a branch nobody is on.

Prefer fetch plus an explicit merge or rebase over a bare `git pull`. `git pull` does one of
three different things depending on `pull.rebase`, `pull.ff`, and any branch-level override —
configuration you did not set and have not read, which may differ between two clones of the
same repository. A command whose behaviour is an environment variable is not a command you
can follow exactly.

Then apply the first row that matches:

| Situation | Command | Why |
| --- | --- | --- |
| Nothing local, remote ahead | `git merge --ff-only origin/<branch>` | Cannot conflict and creates no commit; fails loudly if you were wrong about having nothing local |
| Branch is private — never pushed, or pushed only by you | `git rebase origin/<branch>` | Keeps history linear and the eventual diff readable |
| Branch is shared, or anyone else may have pulled it | `git merge origin/<branch>` | Rebasing published history rewrites commits other people already have |

That last reason is the whole rule. A rebase replaces every commit with a new object at a new
sha. Anyone who already pulled the old ones now holds commits that no longer exist upstream,
and their next pull grafts both copies into their history as duplicates. Merging costs one
merge commit and breaks nothing.

If you cannot establish whether a branch is shared, treat it as shared. The cost of an
unnecessary merge commit is cosmetic; the cost of a wrong rebase is other people's afternoon.

Only the first row is delegable. The other two turn on who else holds these commits, which is
a judgement and not a lookup, so `git-runner` will not take it — a delegated run stops at the
diverged history and reports both logs. Decide here, run the merge or rebase yourself, then
hand the tree back for staging onward.

## Step 4 — conflicts

```bash
git status --short
git diff --name-only --diff-filter=U     # exactly the unmerged paths
```

| Marker | Means |
| --- | --- |
| `UU` | Both sides modified the same file |
| `AA` | Both sides added a file at the same path |
| `AU` / `UA` | Added by one side only, while the other changed the path |
| `DU` / `UD` | One side deleted the file, the other modified it |

### Generated files and lockfiles are regenerated, never hand-merged

Lockfiles, build output, minified bundles, generated clients, and compiled schema stubs are
outputs, not sources. Take one side wholesale, then re-run the tool that produces them:

```bash
git checkout --ours <path>       # or --theirs
# then re-run the project's own generator, e.g.:
#   npm install | poetry lock | cargo update -p <pkg> | go mod tidy | make generate
```

A lockfile is a solved dependency graph. A hand-merged lockfile is a graph that was never
solved — it installs a combination neither side ever tested, and the failure surfaces later,
somewhere unrelated, as a version nobody chose.

During a **rebase**, `--ours` is the upstream side and `--theirs` is your own commit — the
reverse of what they mean during a merge, because a rebase replays your work onto theirs.
Read the file after taking a side and confirm you got the content you meant, rather than
trusting the flag name.

### When to stop

If both sides changed the same logic, and choosing either one loses behaviour the other
added, that is a decision, not a merge. Stop and hand back with the file, the two versions,
and what each does. Leave the tree clean rather than half-resolved, because a partially
resolved tree looks finished to the next command that reads it:

```bash
git merge --abort
git rebase --abort
```

Abort before handing back, and say that you did. A conflict resolved by guessing produces a
commit that compiles, passes review, and silently drops one side's feature.

## Step 5 — stage deliberately

```bash
git status --short                       # everything the tree contains
git add <path> <path>                    # only paths you have looked at
git add -p <path>                        # hunk by hunk when one file holds two changes
git diff --staged                        # exactly what is about to be committed
git diff --staged --stat                 # the same, as a shape check
```

Do not use `git add -A`. It is convenient, and it is precisely how secrets, editor backups,
local configuration, virtualenvs, and build output get committed: it stages whatever happened
to be in the tree, including the things you never opened and the things a tool wrote while
you were working. Stage named paths, then read `git diff --staged` before committing. That
diff is the last point at which a mistake is free.

If `git diff --staged --quiet` exits 0, nothing is staged. Stop; do not create an empty
commit to have something to report.

## Step 6 — scan the staged content

Run this scan over the staged diff every time, including on a change you are confident about.
Everything in this table is permanent once pushed, which is what makes checking cheaper than
being right.

| Look for | Pattern | Why it matters |
| --- | --- | --- |
| Credential-looking strings | `api_key`, `secret`, `token`, `password`, `bearer`, `authorization` next to a `=` or `:` | Anything that reaches a remote must be rotated, not deleted — assume it was read |
| Opaque literals | Unbroken runs of 40 or more base64 or hex characters | Catches keys that carry none of the words above |
| Environment files | Any path whose basename starts `.env` | By convention this is the file that holds the secrets, whatever it happens to hold today |
| Private keys | `BEGIN OPENSSH PRIVATE KEY`, `BEGIN RSA PRIVATE KEY`, `.pem`, `.p12`, `id_rsa` | One committed key compromises every host that trusts it |
| Absolute local paths | `/home/`, `/Users/`, a drive letter followed by a backslash | They resolve on your machine only, and they leak the local username and directory layout |
| Large or binary files | Any file over roughly 1 MB, and any binary the project does not already track | See below — size is permanent |
| Kit files | A copied skill, agent, or command from the kit, typically under `.claude/skills/`, `.claude/agents/`, `.claude/commands/` | They are committed in the kit alone; a copy in this history forks silently and stops receiving updates |

```bash
git diff --staged -U0 | grep -nEi '(api[_-]?key|secret|token|password|bearer|authorization)'
git diff --staged -U0 | grep -nE '[A-Za-z0-9+/=_-]{40,}'
git diff --staged -U0 | grep -n 'BEGIN .*PRIVATE KEY'
git diff --staged -U0 | grep -nE '/home/|/Users/|[A-Za-z]:\\'
git diff --staged --name-only | grep -E '(^|/)\.env'
git diff --staged --numstat            # a binary file shows as "-  -" instead of counts
git diff --staged --name-only | while read -r f; do
  [ -f "$f" ] && printf '%s\t%s\n' "$(wc -c <"$f")" "$f"
done | sort -rn | head
python3 <kit>/skills/git-sync/scripts/kit_guard.py --staged
```

The size threshold matters because a blob is permanent in history even after the file is
deleted. A later commit removing it takes it out of the tree and not out of the object store,
so every clone of the repository keeps downloading it forever, and removing it for real means
rewriting history and making everyone re-clone. A 40 MB binary added by accident is a cost
paid once per clone, indefinitely.

A hit is not automatically a stop — a fixture named `test_token.json` is fine. Report what
matched and why you cleared it. An unreported match and an unnoticed one look the same later.

The kit guard is the exception: a non-zero exit is always a stop. Unstage what it names and
commit the rest, because an edited kit file belongs back in the kit as its own commit there,
which is also the only way anyone else ever receives the fix.

The guard only reports. It never touches the index — it prints a `git restore --staged` line
per path and leaves the unstaging to you, because a guard that quietly rearranges someone's
staged work is a guard they switch off, and a switched-off guard enforces nothing. Read its
output rather than the exit code alone: it also reports paths that matched on location alone,
which do not fail the run and are yours to clear or to exempt by exact path with `--allow`.

## Step 7 — commit

Take the message from the `commit-draft` skill. For anything with a body, write it to a file
and pass the file, so the body survives shell quoting intact:

```bash
git commit -F <message-file>
git commit -m "<subject>"          # subject-only messages
```

**No bypass flags.** Not `--no-verify`, not `-n`, not `HUSKY=0`, not `SKIP=...`, not any
environment variable that disables a hook. The hooks are the project's own quality gate,
installed by someone who was burned by exactly the thing they check; skipping them does not
remove the failure, it relocates it to CI, where the loop is minutes instead of seconds and a
red pipeline blocks everyone rather than just you.

If a hook rewrites files — a formatter, an import sorter, a lockfile refresher — the commit
may have been made from content that no longer matches the tree. Re-check afterwards:

```bash
git status --short
```

If the hook modified tracked files, stage those files and commit again. Do not amend if the
previous commit has already been pushed.

If a hook fails, fix what it reported and commit again. A failing hook is a finding, not an
obstacle.

## Step 8 — push

Always name the remote and the branch. A bare `git push` obeys `push.default`, which is
another piece of configuration you did not set, and under some settings it pushes refs you
did not name.

```bash
git push origin HEAD                    # upstream already set
git push -u origin <branch>             # first push: -u sets tracking for every later push
```

Push the branch you are on. Do not push `HEAD:<some-other-branch>` unless the user asked for
exactly that.

### Retry transient failures, on this schedule

| Attempt | Wait before it |
| --- | --- |
| 1 | — |
| 2 | 2 s |
| 3 | 4 s |
| 4 | 8 s |
| 5 | 16 s |

Five attempts, about 30 seconds total, then stop and report. The cap exists because anything
still failing after 30 seconds is an outage or a misconfiguration rather than a blip, and an
uncapped retry loop turns a clear error into a session that appears to be working.

### A rejection is not a transient failure

| The remote said | Class | Do |
| --- | --- | --- |
| `Could not resolve host`, `Connection timed out`, `Connection reset`, TLS handshake failure, `502`/`503` | Transient | Retry on the schedule above |
| `! [rejected] ... (fetch first)` or `(non-fast-forward)` | The remote moved | Go back to step 3, reconcile, push once more. Never force |
| `! [remote rejected] ... (pre-receive hook declined)` | Server-side policy — protected branch, required check, file-size limit | Report the server's message verbatim and stop |
| `Permission denied (publickey)`, `403`, `Authentication failed` | Credentials | Report and stop |

A rejection means the remote considered the request and declined it, so retrying sends the
same refs to the same decision and produces N identical errors. For a policy rejection or a
credential failure, do not work around it: do not change the remote URL, do not switch
authentication method, and do not push to a different branch to get something through.

Reconcile a `fetch first` rejection once. If the second push is rejected again, the branch is
moving faster than you are — stop and hand back rather than entering a fetch-push loop.

## Step 9 — report

Report facts in this fixed shape, and nothing else. Every line appears every run; write
`none` rather than omitting one, because a missing line is indistinguishable from a step that
was forgotten.

```markdown
**Branch**: feature/date-parsing (tracking origin/feature/date-parsing)
**Update**: fetched; 3 commits merged fast-forward
**Staged**: 4 files — src/parser/date.py, tests/test_date.py, CHANGELOG.md, README.md
**Commit**: a1b2c3d — fix(parser): accept offsets without a colon
**Push**: origin/feature/date-parsing, 1 attempt, upstream already set
**Skipped or unexpected**: 1 stash entry present (`WIP on main`, 2026-08-02), not touched
```

No commentary, no assessment of the change, no suggestions. Anything surprising goes on the
last line as a fact: a stash you found, a hook that rewrote files, a retry that was needed, a
scan hit you cleared, a step that did not apply.

## Do not

- Do not run a command that is not in this skill because it seems equivalent. The commands
  here were chosen for what they refuse to do.
- Do not change git configuration to make a command succeed — not `user.email`, not
  `pull.rebase`, not a remote URL. A command that needs the config changed is telling you
  something, and the change outlives this session.
- Do not resolve a conflict in logic you did not write. Hand it back.
- Do not create, merge, or comment on a pull request, and do not delete any branch. This
  skill moves commits; it does not manage the forge.
- Do not push tags, cut a release, or bump a version. That is the `changelog-release` skill.
- Do not amend, squash, or reword a commit that has been pushed.
- Do not run `git gc`, `git prune`, or repository maintenance. Housekeeping that touches the
  object store is never part of shipping a change.
- Do not treat a rejected push as a reason to force.

## Never run these

For each, the safer command that does the same intended job.

| Never | Because | Instead |
| --- | --- | --- |
| `git push --force` to a shared branch | It discards whatever anyone else pushed since your last fetch, and that work usually exists in no other clone | Fetch, reconcile locally per step 3, push normally |
| Any `--force` without a lease | An unconditional force cannot distinguish "my rebase" from "someone else's new commit"; a lease refuses the push if the remote moved since your last fetch | `git push --force-with-lease --force-if-includes`, and only on a branch that is yours alone |
| `git reset --hard` with uncommitted work present | Uncommitted changes are the one thing git holds no copy of, so they are destroyed with no reflog entry to recover from | `git stash push -u` first, or commit to a scratch branch, then reset |
| `git clean -fdx` without confirmation | `-x` deletes ignored files too — local configuration, credentials, virtualenvs, caches — none of which are in any commit | `git clean -nd` first, read the list aloud, then delete only the paths that were confirmed |
| `git checkout -- <path>` or `git restore <path>` to tidy up | It overwrites the file from the index and discards the edits silently; there is no reflog for the working tree | Show `git diff -- <path>` first, and act only on paths the user named. The `--ours` / `--theirs` form during an active conflict is a different operation and is permitted |
| Rebase, amend, squash, or filter of commits already pushed | It rewrites objects other people hold; their next pull re-applies the old commits as duplicates, or they force-push the old history back over yours | A new commit on top, or `git revert <sha>` to undo a published commit |
| `git push --tags`, or pushing a tag nobody asked for | CI and release tooling treat a tag on the remote as a release; deleting a tag does not un-fetch it from the clones that already have it | Push the single named tag, when asked: `git push origin v1.2.3` |

## Verify

- [ ] Pre-flight ran: repo confirmed, branch known, upstream known, tree state known, stash
      list read and reported.
- [ ] The default branch was detected from the remote HEAD rather than assumed, and `HEAD` is
      not on it (or the user said to commit there in this session).
- [ ] The update used `git fetch` plus an explicit merge or rebase, never a bare `git pull`,
      and the merge-or-rebase choice matches whether the branch is shared.
- [ ] Any conflict was either resolved by regenerating a generated file with its own tool, or
      handed back with the tree cleanly aborted — never left half-resolved.
- [ ] Files were staged by name, `git add -A` was not used, and `git diff --staged` was read
      in full before the commit.
- [ ] The content scan ran, and every match is either absent from the commit or reported with
      the reason it was cleared.
- [ ] No file over roughly 1 MB, and no unexpected binary, is in the commit.
- [ ] No kit file is staged — `kit_guard.py --staged` exits zero.
- [ ] The commit used a `commit-draft` message and no verification bypass flag; if a hook
      rewrote files, the result was restaged and re-committed.
- [ ] The push named a remote and a branch, set upstream on a first push, and retried only
      transient failures — at most five attempts.
- [ ] No rejection was answered with a force push, a changed remote, or a different branch.
- [ ] The report carries all six lines, with `none` where nothing applies.
