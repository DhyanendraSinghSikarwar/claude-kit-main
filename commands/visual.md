---
description: Capture the interface, audit it against what the docs promise, and fix what the audit finds.
argument-hint: "[screen, state, or extra context, optional]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Task
---

Run a visual verification pass over this project's interface by following the `visual-verify`
skill.

- Branch: !`git rev-parse --abbrev-ref HEAD`
- Changed since the last commit: !`git diff HEAD --stat`
- Recent commits: !`git log -5 --oneline`

Restrict the run to these screens or states if any are named: $ARGUMENTS

Report findings by severity, each with the screenshot and region as evidence; what was fixed,
naming the before and after images; what was left and why; and what could not be verified.
Do not decide anything that needs a design or product judgement — report it.

End with exactly one of the skill's two terminal verdicts — `VERIFIED` or `OPEN` — on its own
line; `OPEN` names what remains and what each item needs.
