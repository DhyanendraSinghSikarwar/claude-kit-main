---
description: Cut a release — pick the semantic version from the diff, update the changelog, bump manifests, tag, and draft notes.
argument-hint: "[explicit version, optional — otherwise inferred from the diff]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
---

Use the `changelog-release` skill to cut a release.

- Last tag: !`git describe --tags --abbrev=0 2>/dev/null || echo "(no tags yet)"`
- Commits since: !`git log $(git describe --tags --abbrev=0 2>/dev/null)..HEAD --oneline 2>/dev/null || git log --oneline -30`
- Changed files since: !`git diff $(git describe --tags --abbrev=0 2>/dev/null)..HEAD --stat 2>/dev/null || git diff --stat HEAD~10..HEAD`

Version, if the user specified one: $ARGUMENTS. If empty, infer it from the diff using the
SemVer table in the skill, and remember the pre-1.0 rule if the current version starts with `0.`.

Stop and confirm the proposed version with the user before editing any file. Do not push the
commit or the tag unless explicitly asked.
