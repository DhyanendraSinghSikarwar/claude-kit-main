#!/usr/bin/env python3
"""Refuse to let claude-kit files be committed into a consuming repository.

Kit skills and agents are *copied* into a consuming repo's working directory so that repo's
tooling can find them. They are never committed to it. They are committed in one place only:
the kit. A consuming repository's git history must contain zero kit files, at any path,
forever -- a committed copy forks silently, stops receiving updates, and re-creates the exact
duplication the kit exists to remove. This script is the mechanical half of that rule: prose
can be ignored, a non-zero exit cannot.

Read-only by design. It never stages, unstages, commits, or edits anything -- it reports, and
acting on the report is the caller's decision. A guard that silently unstages someone's work
is a guard people disable, and a disabled guard protects nothing.

Detection converges five signals, because both failure directions are costly: a false negative
puts a copy into history forever, a false positive blocks a legitimate commit and teaches
people to bypass the guard.

  marker  `.kit-version` in the path's directory or an ancestor. The bootstrap writes it
          into the copied directory and nothing else does, so it is the strongest signal --
          read from disk rather than the index, since it is untracked by design.
  name    frontmatter `name:` matching a known kit skill or agent. Strong wherever the file
          sits, because a copy at an unconventional path is still a copy.
  command frontmatter shaped like a slash command -- `allowed-tools` or `argument-hint` and
          no `name:` -- over a body that invokes a known kit skill or agent in backticks.
          Commands are the one kit artefact with no `name:` key, so this reference is the
          only fingerprint a copy carries, and it survives a rename of the file.
  tier    frontmatter `tier:` holding a kit tier word (cheap / standard / deep). Kit agents
          carry it, but a project's own agent may have borrowed the convention, so it counts
          only alongside a path match.
  path    a conventional location a copy lands in. Weakest alone: a project is entitled to
          its own skills and agents at those paths.

A finding blocks when `marker`, `name`, or `command` fired, or when `path` and `tier`
converged; a path match alone is reported for review and does not fail the run, and `--strict`
promotes those, which is what auditing an old repository wants. A project's own command that
merely invokes a copied kit skill matches `command` too; that is the accepted cost of closing
the gap, and `--allow PATH` exempts it by exact path.

A repository that is itself a kit source -- a `.claude-plugin/plugin.json` manifest beside
top-level `skills/` and `agents/` -- still gets scanned, but its own top-level kit tree
(`skills/`, `agents/`, `commands/`, `hooks/`, `.claude-plugin/`) is exempt, because that is
the one place these files belong in history. Everything else in it, `.claude/` included, is
checked as normal: a repo that ships a plugin can still have a copied kit working directory,
and exempting the whole repository on shape alone would wave that copy straight through. The
manifest file is required as evidence rather than the directory name alone, but its contents
are not read, so anyone's own kit counts too.

Exit codes, which the troubleshooting document keys on and so do not change:
  0  clean, or only review-level findings without --strict
  1  kit files found
  2  usage or environment error -- not a git repository, git missing, unreadable option file,
     or an allowlist entry that is a pattern. argparse also exits 2, so the two agree.

Check and refresh the known-name default whenever the kit gains a skill or an agent. The
second command verifies the new list against a real scan; then paste `names.txt` into
DEFAULT_KIT_NAMES by hand, because nothing here rewrites the constant for you:
    ( cd "$KIT" && ls -1 skills && ls -1 agents | sed 's/\\.md$//' ) | sort -u > names.txt
    python3 kit_guard.py --names-file names.txt

Standard library only, Python 3.8+. A guard that needs installing does not get installed.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Sequence

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"  # git's canonical empty tree
MARKER_NAME = ".kit-version"
TIER_WORDS = {"cheap", "standard", "deep"}
FRONTMATTER_BYTES = 4096  # frontmatter is at the top; never read a whole file to find it
GLOB_CHARS = "*?[]"
COMMAND_KEYS = ("allowed-tools", "argument-hint")  # frontmatter keys only a command carries

# Top-level directories a kit source owns. Inside such a repository these are the one place
# kit files belong, so they are dropped before the scan rather than exempting the whole repo.
KIT_SOURCE_DIRS = frozenset({".claude-plugin", "agents", "commands", "hooks", "skills"})
KIT_SOURCE_NOTE = "this repository is a kit source, so its own top-level kit tree is exempt"

# Matched with fnmatch against the repository-relative POSIX path, so `*` crosses directory
# separators: `.claude/skills/*/SKILL.md` also catches a copy nested deeper.
DEFAULT_PATH_PATTERNS = (
    ".claude/agents/*.md", ".claude/skills/*/SKILL.md", ".claude/skills/*/scripts/*",
    ".claude/commands/*.md", ".claude/hooks/notify.py", ".claude/plugins/*/agents/*.md",
    ".claude/plugins/*/skills/*/SKILL.md", "claude-kit/*", ".claude-kit/*",
    "vendor/claude-kit/*",
    "*/SKILL.md",       # a copy at some other path: an earlier bootstrap, a renamed directory
    "*" + MARKER_NAME,
)

DEFAULT_KIT_NAMES = frozenset("""
ai-disclosure changelog-release commit-draft dupe-check git-sync github-account-switch
log-triage markdown-mermaid office-to-md pdf-to-md pre-commit-gate project-bootstrap
repo-doc-set test-summary texture-flatten tui-screenshots ui-glossary visual-verify
bug-fixer changelog-scribe commit-drafter doc-writer dupe-detector git-runner image-extractor
log-triager office-extractor pdf-extractor release-notes release-validator scoped-search
screenshot-runner test-runner test-summarizer ui-cataloguer ui-describer visual-auditor
""".split())


class GuardError(Exception):
    """Environment or usage problem. Always reported, always exit 2."""


@dataclass
class Finding:
    path: str
    signals: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    remedy: str = ""
    blocking: bool = False


def git(root: str | None, args: Sequence[str]) -> bytes:
    """Run a git command and return raw stdout. Any failure becomes a GuardError."""
    cmd = ["git"] + (["-C", root] if root else []) + list(args)
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        raise GuardError("git is not on PATH; this guard only runs inside a git repository")
    if proc.returncode != 0:
        raise GuardError(proc.stderr.decode("utf-8", "replace").strip()
                         or "git " + " ".join(args) + " failed")
    return proc.stdout


def nul_paths(data: bytes) -> list[str]:
    # `-z` means git never quotes or escapes, so paths with spaces and non-ASCII names
    # arrive intact; surrogateescape keeps undecodable bytes reversible instead of raising.
    return [p.decode("utf-8", "surrogateescape") for p in data.split(b"\0") if p]


def staged_paths(root: str) -> list[str]:
    # A detached HEAD resolves like any other; a repo with no commits does not, and the empty
    # tree is the base that makes a first commit diffable. Deletions are filtered out, because
    # removing a kit file is the fix rather than the offence.
    try:
        git(root, ["rev-parse", "--verify", "--quiet", "HEAD"])
        base = "HEAD"
    except GuardError:
        base = EMPTY_TREE
    return nul_paths(git(root, ["diff", "--cached", "--name-only", "-z",
                                "--diff-filter=ACMR", base]))


def tracked_paths(root: str) -> list[str]:
    return nul_paths(git(root, ["ls-files", "-z"]))


def read_list_file(path: str) -> list[str]:
    """One entry per line; blank lines and `#` comments ignored."""
    try:
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise GuardError("cannot read {}: {}".format(path, exc))
    return [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def normalise(rel: str) -> str:
    rel = rel.replace("\\", "/")
    return rel[2:] if rel.startswith("./") else rel


def check_allowlist(entries: Sequence[str]) -> set[str]:
    """Normalise the allowlist, rejecting anything that is a pattern.

    An allowlist of patterns widens quietly as the repository grows -- `.claude/skills/*`
    exempts directories nobody has created yet. Exceptions have to stay countable.
    """
    for entry in entries:
        if any(ch in entry for ch in GLOB_CHARS):
            raise GuardError("allowlist entry {!r} looks like a pattern; give exact paths "
                             "only, so an exception cannot widen later".format(entry))
    return set(normalise(e) for e in entries)


def read_head(path: str) -> str:
    """The first FRONTMATTER_BYTES of a file; OSError if unreadable.

    One read serves both the frontmatter parse and the command-body scan, so an odd file
    raises in exactly one place and the guard's disk cost stays one open per path.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read(FRONTMATTER_BYTES)


def parse_frontmatter(head: str) -> dict[str, str]:
    """Parse a leading `---` block into flat key/value strings.

    Deliberately not a YAML parser: only top-level `key: value` lines matter, and the
    standard library has no YAML to call.
    """
    lines = head.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line[:1].isspace() or ":" not in line:  # indented keys are not top-level
            continue
        key, _, value = line.partition(":")
        fields[key.strip().lower()] = value.strip().strip("\"'")
    return fields


def invoked_kit_name(head: str, names: set[str]) -> str | None:
    """First known kit name the text names in backticks, if any.

    Odd-indexed segments of a backtick split are exactly the spans between backtick pairs,
    which is enough here and avoids pretending to parse Markdown.
    """
    for token in head.split("`")[1::2]:
        if token in names:
            return token
    return None


def marker_dir(root: str, rel: str, cache: dict[str, bool]) -> str | None:
    """Directory holding a `.kit-version` marker for this path, if any.

    The walk stops above the repository root: a stray marker there would flag every file.
    """
    parts = rel.split("/")[:-1]
    for depth in range(len(parts), 0, -1):
        d = "/".join(parts[:depth])
        if d not in cache:
            cache[d] = os.path.isfile(os.path.join(root, d, MARKER_NAME))
        if cache[d]:
            return d
    return None


def looks_like_kit_source(root: str) -> bool:
    """A kit source repository, where the kit's own tree is supposed to be committed.

    Evidence, not shape. A `.claude-plugin/plugin.json` manifest is required, not merely a
    `.claude-plugin/` directory, because `skills/` + `agents/` + a directory name is what an
    ordinary consuming repository looks like too -- and this predicate must never be the
    reason a consuming repo's copied kit files go unexamined. Contents are not read, so a
    fork or anyone's own kit counts.
    """
    return (os.path.isfile(os.path.join(root, ".claude-plugin", "plugin.json"))
            and all(os.path.isdir(os.path.join(root, d)) for d in ("skills", "agents")))


def outside_kit_tree(paths: Sequence[str]) -> list[str]:
    """Drop paths in a kit source's own top-level directories, keeping everything else.

    Narrow by design: `.claude/skills/...` in a kit source is still a working copy of some
    other kit and is still checked.
    """
    return [p for p in paths if normalise(p).split("/", 1)[0] not in KIT_SOURCE_DIRS]


def match_pattern(rel: str, patterns: Sequence[str]) -> str | None:
    for pat in patterns:
        if fnmatch.fnmatchcase(rel, pat):
            return pat
    return None


def classify(root: str, rel: str, patterns: Sequence[str], names: set[str],
             cache: dict[str, bool], remedy: str) -> Finding | None:
    """Collect every signal that fires for one path. Returns None when none fires."""
    f = Finding(path=rel, remedy=remedy.format(path=shlex.quote(rel)))

    def hit(signal: str, detail: str) -> None:
        f.signals.append(signal)
        f.details.append(detail)

    if os.path.basename(rel) == MARKER_NAME:
        hit("marker", "this is the {} marker itself".format(MARKER_NAME))
    else:
        holder = marker_dir(root, rel, cache)
        if holder:
            hit("marker", "{} present in {}".format(MARKER_NAME, holder))

    pattern = match_pattern(rel, patterns)
    if pattern:
        hit("path", "path matches {!r}".format(pattern))

    if rel.lower().endswith(".md"):
        head = ""
        try:
            head = read_head(os.path.join(root, rel))
        except OSError as exc:
            # Dangling symlink, permissions, a file staged then removed: report it as
            # unknown and carry on. A guard that dies on one odd file gets deleted.
            if pattern:
                hit("unknown", "frontmatter unreadable ({})".format(exc.strerror or exc))
        fields = parse_frontmatter(head)
        name, tier = fields.get("name", ""), fields.get("tier", "").lower()
        if name and name in names:
            hit("name", "frontmatter name: {} is a known kit skill or agent".format(name))
        elif not name and any(k in fields for k in COMMAND_KEYS):
            # A command is the one kit artefact with no `name:`, so match on what it invokes.
            # Kit commands are thin wrappers that always name their skill or agent, and that
            # reference travels with the file however it is renamed or relocated.
            invoked = invoked_kit_name(head, names)
            if invoked:
                hit("command", "command frontmatter over a body invoking the kit "
                               "`{}`".format(invoked))
        if tier in TIER_WORDS:
            hit("tier", "frontmatter tier: {}".format(tier))

    if not f.signals:
        return None
    f.blocking = ("marker" in f.signals or "name" in f.signals or "command" in f.signals
                  or ("path" in f.signals and "tier" in f.signals))
    return f


def scan(root: str, paths: Sequence[str], args: argparse.Namespace) -> dict:
    patterns = (read_list_file(args.patterns_file) if args.patterns_file
                else list(DEFAULT_PATH_PATTERNS)) + list(args.pattern or [])
    names = (set(read_list_file(args.names_file)) if args.names_file
             else set(DEFAULT_KIT_NAMES)) | set(args.name or [])
    allowed = check_allowlist(list(args.allow or []) +
                              (read_list_file(args.allow_file) if args.allow_file else []))
    # Neither remedy destroys the working file: unstaging leaves it in the tree, and a cached
    # removal untracks it while the copy on disk goes on working.
    remedy = ("git restore --staged -- {path}" if args.mode == "staged"
              else "git rm --cached -- {path}")

    cache: dict[str, bool] = {}
    findings, skipped = [], []
    for rel in sorted(set(normalise(p) for p in paths)):
        if rel in allowed:
            skipped.append(rel)
            continue
        found = classify(root, rel, patterns, names, cache, remedy)
        if found:
            findings.append(found)

    blocking = [f for f in findings if f.blocking]
    review = [f for f in findings if not f.blocking]
    failed = bool(blocking) or (bool(review) and args.strict)
    return {"mode": args.mode, "checked": len(paths), "blocking": blocking, "review": review,
            "allowed": skipped, "exit_code": 1 if failed else 0}


def as_json(report: dict) -> str:
    def row(f: Finding) -> dict:
        return {"path": f.path, "signals": f.signals, "detail": "; ".join(f.details),
                "remedy": f.remedy}

    payload = dict(report, clean=report["exit_code"] == 0,
                   blocking=[row(f) for f in report["blocking"]],
                   review=[row(f) for f in report["review"]])
    return json.dumps(payload, indent=2, ensure_ascii=True)


def as_text(report: dict, strict: bool) -> str:
    noun = report["mode"]
    note = report.get("note")
    if not report["blocking"] and not report["review"]:
        # One line on success, plus the exemption line only when something was exempt. A guard
        # that prints a paragraph when nothing is wrong gets muted, and a muted guard is worth
        # exactly as much as no guard.
        clean = "kit-guard: clean - {} {} path(s) checked, none belong to the kit.".format(
            report["checked"], noun)
        return clean + ("\nNot checked: {}.".format(note) if note else "")

    out = ["kit-guard: {} kit file(s) {} - these must never be committed.".format(
        len(report["blocking"]), noun)] if report["blocking"] else [
        "kit-guard: {} path(s) {} look kit-shaped but matched on path alone.".format(
            len(report["review"]), noun)]
    if note:
        out.append("Not checked: {}.".format(note))
    for f in report["blocking"] + report["review"]:
        out += ["",
                "  {}{}".format(f.path, "" if f.blocking else "  (review only)"),
                "      signal: {}".format(" + ".join(f.signals)),
                "      why:    {}".format("; ".join(f.details)),
                "      remedy: {}".format(f.remedy)]
    out.append("")
    if report["review"] and not strict:
        out.append("Review-level matches do not fail this run; --strict makes them fail.")
    if report["allowed"]:
        out.append("Allowlisted, not checked: {}".format(", ".join(report["allowed"])))
    out += ["For a file this project owns, exempt it by exact path: --allow PATH.",
            "Kit files are committed in one place only: the kit itself. Keep the copy and",
            "exclude it locally instead - per-clone, untracked, needing no commit of its own:",
            "    printf '/%s\\n' <path> >> .git/info/exclude"]
    return "\n".join(out)


def hook_script() -> str:
    guard = shlex.quote(os.path.abspath(__file__))
    return """#!/bin/sh
# claude-kit pre-commit guard. Refuses a commit that contains kit files.
#
# This hook belongs in .git/hooks/pre-commit, which git never commits. That is deliberate
# rather than incidental: the rule it enforces says kit files live in the kit and nowhere
# else, so the enforcement of that rule is local and uncommitted too.
#
# Install:  python3 {guard} --hook > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
#
# Exit 1 blocks the commit. Nothing is unstaged for you -- read the report and decide.
GUARD={guard}
PYTHON="${{PYTHON:-python3}}"

# A moved or uninstalled guard must not block every commit in this repository forever; that
# is how a hook gets bypassed with --no-verify and then stays bypassed for everything else.
if [ ! -f "$GUARD" ]; then
    echo "kit-guard: guard script not found at $GUARD - skipping." >&2
    exit 0
fi

exec "$PYTHON" "$GUARD" --staged
""".format(guard=guard)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kit_guard.py",
        description="Report kit files staged in, or tracked by, a consuming repository.",
        epilog="""examples:
  python3 kit_guard.py                              check what is about to be committed
  python3 kit_guard.py --tracked --strict           audit a repo that predates this guard
  python3 kit_guard.py --staged --json              machine-readable, for a caller that acts
  python3 kit_guard.py --allow .claude/skills/ours/SKILL.md
  python3 kit_guard.py --hook > .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

exit codes: 0 clean, 1 kit files found, 2 usage or environment error.
This script only reports. Unstaging or untracking is the caller's decision.""",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--staged", dest="mode", action="store_const", const="staged",
                      help="check what is staged for the next commit (default)")
    mode.add_argument("--tracked", dest="mode", action="store_const", const="tracked",
                      help="check everything the repository already tracks")
    p.set_defaults(mode="staged")
    add = p.add_argument
    add("--hook", action="store_true", help="print an installable pre-commit hook and exit")
    add("--json", action="store_true", help="machine-readable output")
    add("--strict", action="store_true", help="fail on path-only matches too")
    add("--pattern", action="append", metavar="GLOB", help="extra path pattern; repeatable")
    add("--patterns-file", metavar="FILE", help="replace the built-in patterns, one per line")
    add("--name", action="append", metavar="NAME", help="extra known kit name; repeatable")
    add("--names-file", metavar="FILE", help="replace the built-in names, one per line")
    add("--allow", action="append", metavar="PATH",
        help="exact repo-relative path to exempt; repeatable, patterns rejected")
    add("--allow-file", metavar="FILE", help="file of exact paths to exempt, one per line")
    return p


def main() -> int:
    args = build_parser().parse_args()

    # Undecodable path bytes survive as surrogates; without this they raise on write.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="surrogateescape")  # type: ignore[attr-defined]
        except Exception:
            pass

    if args.hook:
        sys.stdout.write(hook_script())
        return 0

    try:
        root = git(None, ["rev-parse", "--show-toplevel"]).decode("utf-8", "surrogateescape")
        root = root.strip()
        paths = staged_paths(root) if args.mode == "staged" else tracked_paths(root)
        note = None
        if looks_like_kit_source(root):
            # Exempt the kit's own tree, never the repository. A blanket exemption here would
            # wave through a copied kit working directory in any repo that ships a plugin.
            note = KIT_SOURCE_NOTE
            paths = outside_kit_tree(paths)
        report = scan(root, paths, args)
        if note:
            report["note"] = note
    except GuardError as exc:
        sys.stderr.write("kit-guard: {}\n".format(exc))
        return 2

    print(as_json(report) if args.json else as_text(report, args.strict))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
