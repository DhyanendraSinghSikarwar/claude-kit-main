---
name: markdown-mermaid
description: Use when creating or editing Markdown files, especially with diagrams. Enforces full markdownlint default ruleset and Mermaid syntax constraints.
---
Before finalizing any .md output, check every rule below explicitly.

## Markdownlint default ruleset

| Rule  | Requirement |
| --- | --- |
| MD001 | Heading levels increment by one (no skipping H2 -> H4) |
| MD003 | Heading style consistent (ATX `#` throughout) |
| MD004 | Unordered list style consistent (`-` throughout) |
| MD005 | Consistent indentation for list items at same level |
| MD007 | Unordered list indentation = 2 spaces |
| MD009 | No trailing spaces |
| MD010 | No hard tabs |
| MD011 | No reversed link syntax `(text)[url]` |
| MD012 | No multiple consecutive blank lines |
| MD018 | Space required after ATX heading `#` |
| MD019 | No multiple spaces after heading `#` |
| MD022 | Headings surrounded by blank lines |
| MD023 | Headings start at line beginning (no leading spaces) |
| MD024 | No duplicate sibling headings |
| MD025 | Single top-level H1 per document |
| MD026 | No trailing punctuation in headings |
| MD027 | No multiple spaces after blockquote `>` |
| MD028 | No blank line inside a blockquote |
| MD029 | Ordered list prefixes consistent (`1.` `1.` `1.` or `1.` `2.` `3.`) |
| MD030 | Exactly one space after list marker |
| MD031 | Fenced code blocks surrounded by blank lines |
| MD032 | Lists surrounded by blank lines |
| MD033 | No inline HTML (unless explicitly required) |
| MD034 | No bare URLs — wrap in `<>` or `[text](url)` |
| MD035 | Horizontal rule style consistent (`---` throughout) |
| MD036 | No emphasis (`**bold**`) used as a heading substitute |
| MD037 | No spaces inside emphasis markers (`** bold **` is invalid) |
| MD038 | No spaces inside inline code span backticks |
| MD039 | No spaces inside link text brackets |
| **MD040** | **Every fenced code block must declare a language** (` ```bash `, never bare ` ``` `) |
| MD041 | First line of file is a top-level heading |
| MD042 | No empty links `[text]()` |
| MD044 | Proper-noun capitalization consistent (e.g. "Markdown" not "markdown" in prose) |
| MD045 | Images have non-empty alt text |
| MD046 | Code block style consistent (fenced, not indented) |
| MD047 | File ends with exactly one trailing newline |
| MD048 | Code fence style consistent (backtick, not tilde) |
| MD049 | Emphasis style consistent (`_` or `*`, pick one) |
| MD050 | Strong style consistent (`__` or `**`, pick one) |
| MD051 | Link fragments resolve to an actual heading |
| MD052 | Reference-style links/images have matching definitions |
| MD053 | No unused reference-link definitions |
| MD055 | Table pipe style consistent (leading/trailing `|` throughout) |
| MD056 | Table column count consistent across all rows |
| MD058 | Tables surrounded by blank lines |

Note: rule set drifts across markdownlint versions — verify against the
installed version (`markdownlint --version`) if strict CI compliance matters.

## Mermaid constraints

- Target syntax compatible with Mermaid 10.3 (no `elk` layout engine, no
  `packet-beta`, avoid v11+-only diagram types).
- Line breaks inside node labels: always `<br/>`, never `\n`.

## Process

1. Write the Markdown.
2. Re-read it against the table above line by line.
3. Run `markdownlint <file>` via Bash if the CLI is available; fix any reported
   violations before returning the file.
