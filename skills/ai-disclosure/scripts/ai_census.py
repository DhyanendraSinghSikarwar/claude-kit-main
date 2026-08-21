#!/usr/bin/env python3
"""Measure AI authorship in a git repository and emit the block that goes into AI.md.

Counts three things, all at one stamped HEAD sha, all from read-only git commands:

  * commits, and how many of them carry an AI co-author trailer;
  * lines added and removed, in AI-assisted commits and across all commits;
  * the surviving-blame share -- of the lines in the tree right now, the fraction that
    traces back to an AI-assisted commit. This is the headline, because added-line counts
    reward volume and cannot tell whether a line still exists.

Standard library only, so it runs anywhere python3 does with no install step: a
verification command that has to be set up first does not get run. Nothing here writes to
the repository -- every git call is a read.

    python3 ai_census.py [REPO]     Markdown block, ready to paste into AI.md
    python3 ai_census.py --json     the same data as JSON, for scripting
    python3 ai_census.py --check    recount, compare against AI.md, exit 1 if stale

Exit codes -- the troubleshooting document keys on these, so they do not change meaning:

    0   success; under --check, AI.md agrees with a fresh count
    1   --check only: AI.md is stale. The figures that moved are printed.
    2   usage or environment error -- git not on PATH, not a git repository, a repository
        with no commits, an unparseable marker, or (under --check) an AI.md that is
        missing or carries no "Measured as of" block to compare against.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import textwrap
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Set, Tuple

# Trailers written by the assistants in common use. A starting point, not a standard: fix
# it to what this history actually contains with --marker, and record that string in
# AI.md, because the figures only reproduce if the reader greps for what you grepped.
# `[ \t]` rather than `\s`, because the same string is printed as a `git log -E` pattern
# and POSIX extended regular expressions have no `\s`.
DEFAULT_MARKER = (
    r"^[ \t]*co-authored-by:.*"
    r"(claude|anthropic|copilot|chatgpt|openai|gemini|cursor|codex|aider|devin|\[bot\])"
)

# Tool-written or third-party content, which distorts every figure, usually by thousands
# of lines credited to whoever ran a generator. Tests, documentation and configuration are
# deliberately absent: they are authored content, and dropping them is the commonest way a
# share gets quietly flattering.
DEFAULT_EXCLUDES = (
    "*.lock", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum",
    "vendor/**", "third_party/**", "node_modules/**", "dist/**", "build/**", "target/**",
    "*.min.js", "*.min.css", "*.map",
    "**/*.generated.*", "**/generated/**", "**/__snapshots__/**",
)

REC, FLD = "\x1e", "\x1f"  # one record per commit; its fields are sha, body, numstat
WIDTH = 92

# git blame --line-porcelain repeats "<sha> <orig> <final>" ahead of every line. Content
# lines start with a tab and cannot collide with it. 40 or 64 hex digits covers both SHA-1
# and SHA-256 repositories.
BLAME_HEADER = re.compile(r"^([0-9a-f]{40}|[0-9a-f]{64}) \d+ \d+")
TRAILER = re.compile(r"^\s*co-authored-by:\s*(.+?)\s*$", re.I | re.M)
STAMP = re.compile(r"^##\s+Measured as of\s+`([0-9a-fA-F]{7,64})`", re.M)


class CensusError(Exception):
    """Anything that ends the run with exit code 2."""


@dataclass
class Census:
    """Every figure, plus everything needed to reproduce it. Flat, because each field is
    also a JSON key and a row the --check comparison keys on."""

    root: str = ""
    sha: str = ""
    date: str = ""
    marker: str = ""
    excludes: List[str] = field(default_factory=list)
    commits: int = 0
    ai_commits: int = 0
    added: int = 0
    removed: int = 0
    ai_added: int = 0
    ai_removed: int = 0
    lines: int = 0
    ai_lines: int = 0
    files_blamed: int = 0
    files_excluded: int = 0
    skipped_binary: int = 0
    skipped_oversize: int = 0
    skipped_unstamped: int = 0
    blame_failed: int = 0
    max_blame_bytes: int = 0
    ai_shas: Set[str] = field(default_factory=set)
    trailers: Dict[str, int] = field(default_factory=dict)
    hits: Dict[str, int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


# --------------------------------------------------------------------------------- git


def git(root: Optional[str], *args: str) -> subprocess.CompletedProcess:
    cmd = ["git"] + (["-C", root] if root else []) + list(args)
    try:
        return subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    except FileNotFoundError:
        raise CensusError("git is not on PATH; every figure here comes from a git command")


def git_out(root: Optional[str], *args: str) -> str:
    proc = git(root, *args)
    if proc.returncode != 0:
        raise CensusError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def find_repo_root(path: str) -> str:
    if not os.path.isdir(path):
        raise CensusError(f"not a directory: {path}")
    proc = git(path, "rev-parse", "--show-toplevel")
    if proc.returncode != 0:
        raise CensusError(f"{path} is not a git repository: {proc.stderr.strip()}")
    return proc.stdout.strip()


# ------------------------------------------------------------------------------- paths


def spec_forms(pattern: str) -> List[str]:
    """One exclusion glob as the git pathspec globs that express it. A bare basename
    pattern needs both forms, because a git pathspec is anchored at the repository root
    and `**/x` will not also match `x`."""
    forms = [pattern]
    if "/" not in pattern.rstrip("/"):
        forms.append(f"**/{pattern}")
    return forms


def pathspecs(patterns: Sequence[str]) -> List[str]:
    """The exclusion list as git pathspecs, exactly as every git call here passes it.

    git does all of the path matching in this script, and the block printed at the end
    passes these same specs. A second matcher written in Python would be a second answer:
    it would have to reproduce `core.quotePath` escaping, numstat's `a => b` rename cells
    and git's own glob rules, and wherever it failed a figure would stop agreeing with the
    command printed beside it -- which is the one thing this file promises.
    """
    return [f":(exclude){form}" for p in patterns for form in spec_forms(p)]


def exclusion_hits(root: str, patterns: Sequence[str],
                   removed: Sequence[str]) -> Dict[str, int]:
    """How many files each pattern removed. First match wins, so the rows sum to the total
    instead of counting one file twice under two overlapping patterns."""
    hits: Dict[str, int] = {}
    left = set(removed)
    for pattern in patterns:
        hits[pattern] = 0
        if not left:
            continue  # nothing else to attribute; skip the git call
        matched = left & {p for p in git_out(root, "ls-files", "-z", "--",
                                             *spec_forms(pattern)).split("\0") if p}
        hits[pattern] = len(matched)
        left -= matched
    return hits


# ---------------------------------------------------------------------------- counting


def collect_log(root: str, marker: "re.Pattern", specs: Sequence[str], out: Census) -> None:
    """One pass over history for commit counts and line counts, AI subset and total.

    git applies the exclusion list, through the same pathspecs the printed verify command
    passes, so this walk and that command are literally the same query. Commits that touch
    only excluded paths never reach us: git prunes them, exactly as `git rev-list --count`
    does for the commit figure.
    """
    raw = git_out(root, "log", "--no-merges", "--numstat", "--format=%x1e%H%x1f%B%x1f",
                  "--", ".", *specs)
    for record in raw.split(REC):
        parts = record.split(FLD)
        if len(parts) < 3 or not parts[0].strip():
            continue
        sha, body, tail = parts[0].strip(), parts[1], parts[2]
        added = removed = 0
        for line in tail.splitlines():
            cols = line.split("\t")
            # numstat prints "-" in both columns for a binary file: no lines to count,
            # but the commit is still in the population git returned.
            if len(cols) >= 3 and cols[0].isdigit() and cols[1].isdigit():
                added, removed = added + int(cols[0]), removed + int(cols[1])
        out.commits += 1
        out.added, out.removed = out.added + added, out.removed + removed
        for value in TRAILER.findall(body):
            out.trailers[value] = out.trailers.get(value, 0) + 1
        if marker.search(body):
            out.ai_commits += 1
            out.ai_added, out.ai_removed = out.ai_added + added, out.ai_removed + removed
            out.ai_shas.add(sha)


def looks_binary(abspath: str) -> bool:
    try:
        with open(abspath, "rb") as handle:
            return b"\0" in handle.read(8000)
    except OSError:
        return False


def blame_file(root: str, path: str, ai: Set[str], cap: int) -> Tuple[str, int, int]:
    """Blame one file at HEAD, returning (outcome, lines, ai_lines).

    Never raises. A census that dies on one weird file gets deleted rather than fixed, so
    every failure here becomes a tallied outcome instead of a traceback.
    """
    full = os.path.join(root, path)
    try:
        size = os.path.getsize(full)
    except OSError:
        size = -1  # not in the worktree: sparse checkout, or deleted locally
    if size > cap:
        return ("skipped_oversize", 0, 0)
    if size > 0 and looks_binary(full):
        return ("skipped_binary", 0, 0)
    try:
        proc = git(root, "blame", "--line-porcelain", "--no-progress", "HEAD", "--", path)
    except Exception:
        return ("blame_failed", 0, 0)
    if proc.returncode != 0:
        return ("blame_failed", 0, 0)
    if not proc.stdout:
        # An empty file blames to nothing legitimately; a non-empty one that produced no
        # output did not blame, and must not be quietly counted as zero lines.
        return ("ok" if size == 0 else "blame_failed", 0, 0)
    total = hit = 0
    for line in proc.stdout.splitlines():
        match = BLAME_HEADER.match(line)
        if match:
            total += 1
            if match.group(1) in ai:
                hit += 1
    return ("ok", total, hit)


def collect_blame(root: str, files: Sequence[str], jobs: int, progress: bool,
                  out: Census) -> None:
    total, tty = len(files), sys.stderr.isatty()
    show = progress and total > 50  # below that the run ends before anyone starts waiting
    step = max(1, total // (20 if tty else 4))
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        work = pool.map(lambda p: blame_file(root, p, out.ai_shas, out.max_blame_bytes), files)
        for done, (outcome, lines, hit) in enumerate(work, start=1):
            if outcome == "ok":
                out.files_blamed += 1
                out.lines += lines
                out.ai_lines += hit
            else:
                setattr(out, outcome, getattr(out, outcome) + 1)
            if show and (done == total or done % step == 0):
                sys.stderr.write(f"  blaming {done}/{total} files" + ("\r" if tty else "\n"))
                sys.stderr.flush()
    if show and tty:
        sys.stderr.write("\r" + " " * 40 + "\r")


def run_census(root: str, marker: str, excludes: Sequence[str], cap: int, jobs: int,
               progress: bool) -> Census:
    if git(root, "rev-parse", "--verify", "HEAD").returncode != 0:
        raise CensusError("the repository has no commits, so there is nothing to measure")
    if any(not pattern.strip() for pattern in excludes):
        # Caught here rather than in the middle of the walk: git rejects an empty pathspec,
        # and its own message arrives with no clue which flag produced it.
        raise CensusError("an exclusion glob is empty; git rejects it as a pathspec")
    out = Census(root=root, marker=marker, excludes=list(excludes), max_blame_bytes=cap,
                 sha=git_out(root, "rev-parse", "HEAD").strip(),
                 date=git_out(root, "show", "-s", "--format=%cd", "--date=short").strip())
    # --is-shallow-repository needs git 2.15; the marker file is the fallback, because a
    # shallow clone must never go undetected -- it silently understates every figure.
    shallow = git(root, "rev-parse", "--is-shallow-repository")
    if (shallow.stdout.strip() == "true" if shallow.returncode == 0
            else os.path.exists(os.path.join(root, ".git", "shallow"))):
        out.warnings.append(
            "This is a shallow clone. History and blame are both truncated, so every "
            "figure below understates AI use by an unknown amount. Run `git fetch "
            "--unshallow` and recount before publishing any of these numbers.")
    if git(root, "symbolic-ref", "-q", "HEAD").returncode != 0:
        out.warnings.append(
            "HEAD is detached. The figures are exact for the sha they are stamped with, "
            "but that sha may not be reachable from any branch you push.")

    specs = pathspecs(excludes)
    collect_log(root, re.compile(marker, re.I | re.M), specs, out)
    # Both halves of the census are filtered by the same git pathspecs, so the surviving
    # share and the line counts printed beside it describe one population of files. `-z`
    # also means no path is quoted, whatever `core.quotePath` says.
    tracked = [p for p in git_out(root, "ls-files", "-z").split("\0") if p]
    kept = {p for p in git_out(root, "ls-files", "-z", "--", ".", *specs).split("\0") if p}
    wanted = [p for p in tracked if p in kept]
    out.files_excluded = len(tracked) - len(wanted)
    out.hits = exclusion_hits(root, excludes, [p for p in tracked if p not in kept])
    # ls-files reads the index, which in a commit gate holds staged files that do not
    # exist at the stamped sha. Blaming those would fail; naming them keeps the gap
    # visible instead of turning it into a failure count nobody can explain.
    at_head = set(git_out(root, "ls-tree", "-r", "-z", "--name-only", "HEAD").split("\0"))
    blamable = [p for p in wanted if p in at_head]
    out.skipped_unstamped = len(wanted) - len(blamable)
    collect_blame(root, blamable, jobs, progress, out)

    if not out.lines:
        out.warnings.append(
            "No lines were blamed: the exclusion list removed every tracked file, or the "
            "tree holds nothing but binaries. The surviving share below means nothing.")
    if out.commits and not out.ai_commits:
        out.warnings.append(
            "No commit matched the marker. Either this history carries no AI-assisted "
            "commits, or the marker is wrong -- check it against the trailers that are "
            "really present before recording 0% anywhere.")
    return out


def to_dict(c: Census) -> dict:
    data = {k: v for k, v in vars(c).items() if k not in ("root", "ai_shas", "trailers", "hits")}
    data["short_sha"] = c.sha[:12]
    data["ai_commit_pct"] = round(100.0 * c.ai_commits / c.commits, 1) if c.commits else 0.0
    data["surviving_pct"] = round(100.0 * c.ai_lines / c.lines, 1) if c.lines else 0.0
    return data


# ------------------------------------------------------------------------------ output


def _n(value: int) -> str:
    return f"{value:,}"


def _pct(part: int, whole: int) -> str:
    return "0.0%" if whole <= 0 else f"{100.0 * part / whole:.1f}%"


COMMANDS = """# The marker, matched case-insensitively against the whole commit message. The census
# applies it as a Python regex; -E below is the closest git has.
AI='{marker}'

# The exclusions, in the order the census applied them.
{ex}

# 1. Commits, then AI-assisted commits.
git rev-list --count --no-merges HEAD -- . "${{EX[@]}}"
git rev-list --count --no-merges -E -i --grep="$AI" HEAD -- . "${{EX[@]}}"

# 2. Lines added and removed -- AI-assisted commits, then all commits.
git log --no-merges -E -i --grep="$AI" --numstat --format='' -- . "${{EX[@]}}" \\
  | awk '$1 ~ /^[0-9]+$/ {{ a += $1; d += $2 }} END {{ print "+" a, "-" d }}'
git log --no-merges --numstat --format='' -- . "${{EX[@]}}" \\
  | awk '$1 ~ /^[0-9]+$/ {{ a += $1; d += $2 }} END {{ print "+" a, "-" d }}'

# 3. Surviving-blame share, at the coverage the census used: text files only, under the
#    blame cap, blamed at HEAD. Then look each line's commit up in the AI-assisted set.
#    Drop the two skip tests and this over-counts by every binary and generated blob.
shas=$(mktemp); lines=$(mktemp)
git log --no-merges -E -i --grep="$AI" --format=%H | sort -u > "$shas"
git ls-files -- . "${{EX[@]}}" | while IFS= read -r f; do
  [ "$(wc -c < "$f" 2>/dev/null || echo 0)" -le {cap} ] || continue
  [ -s "$f" ] && ! grep -Iq '' "$f" 2>/dev/null && continue
  git blame --line-porcelain --no-progress HEAD -- "$f" 2>/dev/null
done | awk '(length($1) == 40 || length($1) == 64) && $2 ~ /^[0-9]+$/ {{ print $1 }}' > "$lines"
awk 'NR == FNR {{ ai[$1]; next }}
     {{ total++ }} $1 in ai {{ hit++ }}
     END {{ printf "%d of %d lines (%.1f%%)\\n", hit, total, 100 * hit / total }}' \\
  "$shas" "$lines\""""

COVERS = (
    ("Marker.", "A commit counts as AI-assisted when its message matches `{marker}`, "
                "case-insensitively. Merge commits are excluded throughout, because a "
                "merge authors no content."),
    # The census cannot find the cutoff: it sees the earliest trailer, not whether the
    # convention began there. Left as a placeholder the author must fill or delete,
    # because a slot silently dropped from a pasted block is how the disclosure ends up
    # counting untagged history as human-written.
    ("Unmeasured history.", "<Fill in or delete: the trailer convention starts at `<sha>` "
                            "(`<date>`), and the N commits before it are unmeasured rather "
                            "than human-written.>"),
    ("Exclusions.", "{excludes}."),
    ("Blame flags.", "`git blame` with no `-M` and no `-C`. Move and copy detection "
                     "reattributes moved lines to their original commit and can shift the "
                     "surviving share by tens of points, so the flags used are declared "
                     "rather than left for the reader to guess."),
    ("Coverage.", "Tracked files: {files_blamed} blamed, {files_excluded} removed by the "
                  "exclusion list, {skipped_binary} skipped as binary, {skipped_oversize} "
                  "skipped over the {max_blame_bytes}-byte blame cap, {skipped_unstamped} "
                  "staged but absent at the stamped sha, {blame_failed} whose blame failed "
                  "and were counted as unattributed. Blame is taken at that sha, so "
                  "uncommitted working-tree edits sit outside every figure. Nothing was "
                  "sampled: every other line was counted."),
    ("Floor, not measurement.", "Untagged AI-assisted commits, if any exist, make every "
                                "figure above a lower bound."),
)

BLOCK = """## Measured as of `{sha}` ({date})

| Figure | Value |
| --- | --- |
| Commits, no merges, exclusions applied | {commits} |
| AI-assisted commits | {ai_commits} — {ai_share} |
| Lines added / removed, AI-assisted commits | +{ai_added} / -{ai_removed} |
| Lines added / removed, all commits | +{added} / -{removed} |
| **Surviving lines from AI-assisted commits** | **{ai_lines} of {lines} — {share}** |

These figures describe the tree at that sha and change with every commit, which is why
they are stamped: an unstamped percentage cannot be checked against anything, and so is
not a disclosure.

## Verify these numbers

```bash
{commands}
```

## What the count covers

{covers}
{table}"""


def verify_commands(c: Census) -> str:
    wrapped, line = [], "EX=("
    for spec in pathspecs(c.excludes):
        quoted = f"'{spec}'"  # a pathspec the shell must neither glob nor word-split
        if len(line) + len(quoted) > WIDTH - 4:
            wrapped.append(line.rstrip())
            line = "    "
        line += quoted + " "
    wrapped.append(line.rstrip() + ")")
    return COMMANDS.format(marker=c.marker.replace("'", "'\\''"), ex="\n".join(wrapped),
                           cap=c.max_blame_bytes)


def markdown_block(c: Census) -> str:
    fields = {k: _n(v) if isinstance(v, int) else v for k, v in vars(c).items()}
    fields["excludes"] = ", ".join(f"`{p}`" for p in c.excludes)
    covers = "\n".join(
        textwrap.fill(f"- **{label}** {text.format(**fields)}", width=WIDTH,
                      subsequent_indent="  ") for label, text in COVERS)
    removed = [(p, n) for p, n in c.hits.items() if n]
    table = ""
    if removed:
        rows = "\n".join(f"| `{p}` | {_n(n)} |" for p, n in removed)
        table = f"\n| Exclusion | Files removed |\n| --- | --- |\n{rows}\n"
    head = "".join(textwrap.fill(f"> **Warning.** {w}", width=WIDTH,
                                 subsequent_indent="> ") + "\n\n" for w in c.warnings)
    return head + BLOCK.format(
        sha=c.sha, date=c.date, commits=_n(c.commits), ai_commits=_n(c.ai_commits),
        ai_share=_pct(c.ai_commits, c.commits), ai_added=_n(c.ai_added),
        ai_removed=_n(c.ai_removed), added=_n(c.added), removed=_n(c.removed),
        ai_lines=_n(c.ai_lines), lines=_n(c.lines), share=_pct(c.ai_lines, c.lines),
        covers=covers, table=table, commands=verify_commands(c))


# ------------------------------------------------------------------------------- check

CHECK_ROWS = (
    ("Stamped sha", "sha"), ("Commits", "commits"), ("AI-assisted commits", "ai_commits"),
    ("Lines added, AI", "ai_added"), ("Lines removed, AI", "ai_removed"),
    ("Lines added, all", "added"), ("Lines removed, all", "removed"),
    ("Surviving AI lines", "ai_lines"), ("Surviving lines", "lines"),
    ("Surviving AI share", "surviving_pct"),
)


def parse_ai_md(text: str) -> dict:
    """Pull the recorded sha, figures, marker and exclusions back out of AI.md."""
    found: dict = {}
    stamp = STAMP.search(text)
    if stamp:
        found["sha"] = stamp.group(1)
    for line in text.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        label, value = cells[0].lower(), cells[1]
        # The lookarounds stop "50.5" from also yielding 50 and 5.
        nums = [int(t.replace(",", ""))
                for t in re.findall(r"(?<![\d.])(\d[\d,]*)(?![\d.])", value)]
        pcts = [float(t) for t in re.findall(r"(\d+(?:\.\d+)?)\s*%", value)]
        if "surviving" in label and len(nums) >= 2:
            found["ai_lines"], found["lines"] = nums[0], nums[1]
            if pcts:
                found["surviving_pct"] = pcts[0]
        elif "lines added" in label and len(nums) >= 2:
            prefix = "ai_" if "ai-assisted" in label else ""
            found[prefix + "added"], found[prefix + "removed"] = nums[0], nums[1]
        elif "ai-assisted commits" in label and nums:
            found["ai_commits"] = nums[0]
        elif "commits" in label and nums:
            found["commits"] = nums[0]

    marker = re.search(r"^AI='(.+)'\s*$", text, re.M)
    bullet = re.search(r"\*\*Marker\.?\*\*", text)
    if marker:
        found["marker"] = marker.group(1).replace("'\\''", "'")
    elif bullet:
        quoted = re.search(r"`([^`]+)`", text[bullet.end():bullet.end() + 400])
        if quoted:
            found["marker"] = quoted.group(1)

    block = re.search(r"^EX=\((.*?)\)\s*$", text, re.M | re.S)
    if block:
        raw = re.findall(r"':\(exclude\)([^']+)'", block.group(1))
        # pathspecs() emits a bare and a **/-prefixed form of each basename pattern;
        # collapse them back so the recount applies exactly the disclosed set.
        excludes: List[str] = []
        for pattern in raw:
            base = pattern[3:] if pattern.startswith("**/") and pattern[3:] in raw else pattern
            if base not in excludes:
                excludes.append(base)
        found["excludes"] = excludes
    return found


def locate_ai_md(root: str, override: Optional[str]) -> str:
    if override:
        return override if os.path.isabs(override) else os.path.join(root, override)
    for candidate in ("AI.md", os.path.join("docs", "AI.md")):
        path = os.path.join(root, candidate)
        if os.path.isfile(path):
            return path
    raise CensusError(
        "no AI.md at the repository root or in docs/. Run without --check to print the "
        "measured block and write the file first; --check compares against an existing "
        "disclosure, it does not create one.")


def compare(stored: dict, fresh: dict) -> List[Tuple[str, str, str]]:
    """Figures that moved, as (label, in AI.md, now). A figure AI.md never stated counts as
    moved: the file is meant to carry all of them, and one that is absent cannot be
    checked, which leaves the reader exactly where staleness would."""
    moved: List[Tuple[str, str, str]] = []
    for label, key in CHECK_ROWS:
        was, now = stored.get(key), fresh[key]
        if key == "sha":
            # AI.md may record an abbreviated sha, so compare on the length it recorded
            # but display both abbreviated: two 40-character shas side by side in a
            # terminal are a wall, and this table has to be readable at a glance.
            same = bool(was) and str(fresh["sha"]).startswith(str(was))
            was, now = (was or "")[:12] or None, str(fresh["sha"])[:12]
        elif key.endswith("_pct"):
            same = was is not None and abs(float(was) - float(now)) < 0.05
            now, was = f"{float(now):.1f}%", None if was is None else f"{float(was):.1f}%"
        else:
            same = was is not None and int(was) == int(now)
            now, was = _n(int(now)), None if was is None else _n(int(was))
        if not same:
            moved.append((label, "(absent)" if was is None else was, str(now)))
    return moved


def report_check(path: str, moved: List[Tuple[str, str, str]], fresh: dict) -> int:
    print(f"AI.md: {path}")
    if not moved:
        print(f"Current at {fresh['short_sha']} — {len(CHECK_ROWS)} figures checked, all match.")
        return 0
    # The headers are part of the column: "In AI.md" is 8 characters, so widths taken from
    # the data alone let a short figure run the header into the next one.
    label_w = max([len("Figure")] + [len(row[0]) for row in moved]) + 2
    value_w = max([len("In AI.md")] + [len(row[1]) for row in moved]) + 2
    print(f"STALE — {len(moved)} of {len(CHECK_ROWS)} figures moved.\n")
    print(f"  {'Figure'.ljust(label_w)}{'In AI.md'.ljust(value_w)}Now")
    for label, was, now in moved:
        print(f"  {label.ljust(label_w)}{was.ljust(value_w)}{now}")
    print('\nRefresh the "Measured as of" and "Verify these numbers" sections with:')
    rerun = " ".join(shlex.quote(a) for a in sys.argv if a != "--check")
    print(f"  python3 {rerun} > /tmp/ai-census-block.md")
    return 1


# -------------------------------------------------------------------------------- main

EPILOG = """examples:
  python3 ai_census.py                     measure this repository, print the AI.md block
  python3 ai_census.py ../other-checkout   measure a different repository
  python3 ai_census.py --check             compare AI.md against a fresh count
  python3 ai_census.py --json | jq .surviving_pct
  python3 ai_census.py --marker 'co-authored-by:.*assistant@example\\.com'
  python3 ai_census.py --exclude 'vendor/**' --exclude '*.lock'
  python3 ai_census.py --max-blame-bytes 500000 --jobs 4

exit codes:
  0  success, or --check found AI.md current
  1  --check found AI.md stale
  2  usage or environment error
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_census.py", epilog=EPILOG,
        description="Measure AI authorship in a git repository and emit the AI.md block.",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add = parser.add_argument
    add("repo", nargs="?", default=".", help="repository to measure (default: .)")
    add("--marker", metavar="REGEX",
        help="case-insensitive regex identifying an AI co-author trailer; under --check it "
             "defaults to the marker AI.md states, so the file being checked also defines "
             "the check")
    add("--exclude", action="append", metavar="GLOB",
        help="glob to exclude, repeatable. Replaces the built-in list rather than adding "
             "to it, so the list AI.md prints is exactly the list that was applied")
    add("--max-blame-bytes", type=int, default=2_000_000, metavar="N",
        help="do not blame files larger than N bytes (default: 2000000); skipped files are "
             "reported in the output, never silently dropped")
    add("--jobs", type=int, default=0, metavar="N",
        help="parallel blame processes (default: one per core, at most 8)")
    add("--json", action="store_true", help="emit JSON instead of Markdown")
    add("--check", action="store_true",
        help="compare AI.md against a fresh count; exit 1 if it is stale")
    add("--ai-file", metavar="PATH", help="path to AI.md (default: AI.md, then docs/AI.md)")
    add("--no-progress", action="store_true", help="do not write blame progress to stderr")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = find_repo_root(args.repo)
        stored: dict = {}
        ai_path = ""
        if args.check:
            ai_path = locate_ai_md(root, args.ai_file)
            with open(ai_path, "r", encoding="utf-8") as handle:
                stored = parse_ai_md(handle.read())
            if "sha" not in stored:
                raise CensusError(
                    f'{ai_path} carries no "## Measured as of `<sha>`" heading, so there '
                    f"is nothing to compare against. Regenerate the block and paste it in.")
        marker = args.marker or stored.get("marker") or DEFAULT_MARKER
        try:
            re.compile(marker)
        except re.error as exc:
            raise CensusError(f"the marker is not a valid regex: {exc}")
        census = run_census(
            root, marker, args.exclude or stored.get("excludes") or list(DEFAULT_EXCLUDES),
            args.max_blame_bytes, args.jobs if args.jobs > 0 else min(8, os.cpu_count() or 4),
            not args.no_progress)
    except CensusError as exc:
        sys.stderr.write(f"ai_census: {exc}\n")
        return 2

    for warning in census.warnings:
        sys.stderr.write(f"WARNING: {warning}\n")
    if census.commits and not census.ai_commits and census.trailers:
        # The commonest cause of a 0% count is a marker that does not match the identity
        # this history carries, so show what is there rather than only the zero.
        top = sorted(census.trailers.items(), key=lambda kv: -kv[1])[:5]
        sys.stderr.write("         Trailers present: "
                         + "; ".join(f"{k} ({v})" for k, v in top) + "\n")

    fresh = to_dict(census)
    if args.check:
        return report_check(ai_path, compare(stored, fresh), fresh)
    if args.json:
        print(json.dumps(fresh, indent=2))
    else:
        sys.stdout.write(markdown_block(census))
    return 0


if __name__ == "__main__":
    sys.exit(main())
