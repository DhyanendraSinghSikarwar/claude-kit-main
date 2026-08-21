---
description: Convert a PDF, Word, Excel, or PowerPoint file to clean Markdown.
argument-hint: "<file path>"
allowed-tools: Bash, Read, Write, Glob
---

Convert the file below to Markdown without loading the raw binary or XML into context.

File: $ARGUMENTS

If no path was given, ask for one. Then dispatch by extension:

- `.pdf` — use the `pdf-to-md` skill.
- `.docx`, `.xlsx`, `.pptx`, `.csv`, `.tsv` — use the `office-to-md` skill.
- An image — use the `image-extractor` agent.

Write the result to a file beside the source or in the session output directory, run that
skill's verification checklist, and report which extraction path was used plus anything that
failed to convert.
