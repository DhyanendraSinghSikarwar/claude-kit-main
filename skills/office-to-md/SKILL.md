---
name: office-to-md
description: Use whenever a .docx, .xlsx, .pptx, or .csv file must be read or quoted. Converts it to Markdown out of band so raw Office XML never enters the working context.
---

# Convert an Office file to Markdown

Produces clean Markdown or CSV from a Word, Excel, or PowerPoint file. The main context
reads only the converted output — never the raw archive XML.

## Delegation

Two stages, split by what each half actually needs:

| Stage | Agent | Tier | Why that tier |
| --- | --- | --- | --- |
| Extract | `../../agents/office-extractor.md` | cheap | Deterministic — pulling text out of the XML |
| Structure | `../../agents/doc-structurer.md` | deep | Rebuilding headings, tables, and reading order |

Pass the deep stage the **extracted text, not the original file**. Re-opening it puts the raw
Office XML back into context, which is the cost this split exists to avoid.

Skip the second stage for a spreadsheet whose extraction is already a clean table — there is
no structure left to infer, and a pass that has nothing to do can only introduce error.

If your runtime has no subagents, follow the procedure below inline, and do not read the raw
extraction after receiving the structured version.

## Why not read the file directly

`.docx`, `.xlsx`, and `.pptx` are zip archives of XML. Reading them raw floods context with
markup for a small amount of text, and the text arrives fragmented across runs, so quoting
it accurately is unreliable. Always convert first.

## Word — `.docx`

Preferred, if installed:

```bash
pandoc -f docx -t gfm --wrap=none --extract-media=./media input.docx -o output.md
```

Pandoc handles headings, lists, tables, footnotes, and images in one pass, which is why it
is first choice.

Fallback:

```bash
pip install python-docx --break-system-packages -q
```

Then walk the document body **in document order** — iterate over the body's child elements
rather than `doc.paragraphs` followed by `doc.tables`, because those two lists lose the
interleaving and a table ends up detached from the paragraph introducing it.

Map as follows:

| Word | Markdown |
| --- | --- |
| Style `Heading N` | `#` × N |
| Style `Title` | `#` |
| Style `List Paragraph` with numbering | `1.` or `-` per the numbering format |
| Bold / italic runs | `**` / `_` |
| Table | pipe table, first row as header |
| Hyperlink | `[text](url)` |
| Footnote | `[^n]` plus a definition at the end |

For tracked changes, take the **accepted** text — include insertions, drop deletions — and
say in one line that the document contained tracked changes. For comments, list them at the
end with the text they anchor to; do not inline them.

## Excel — `.xlsx`

```bash
pip install openpyxl --break-system-packages -q
```

Rules that matter:

- Open with `data_only=True` to get **computed values**, not formula strings. If you need
  the formulas too, open a second time with `data_only=False` and report both.
- Note that `data_only=True` returns `None` for every formula cell if the file was written
  by a library rather than by Excel, because no cached value exists. If you see all-`None`
  formula cells, say so rather than reporting the sheet as empty.
- Convert **each sheet separately**, with the sheet name as a heading.
- Emit CSV, not a Markdown table, when a sheet exceeds 30 rows or 10 columns — a 500-row
  pipe table is unreadable and enormous. Write the CSV to a file and summarise its shape.
- Report the used range, merged cells, and any sheet that is hidden.
- Dates arrive as `datetime` objects; format them ISO-8601. Do not let them render as serial
  numbers.

## PowerPoint — `.pptx`

```bash
pip install python-pptx --break-system-packages -q
```

One `## Slide N` heading per slide. Under it: the title placeholder, then body text in
placeholder order, then a `> Notes:` blockquote for the speaker notes. Describe images by
their alt text if present, otherwise as `![image](#)`. Preserve tables as pipe tables.

## CSV and TSV

Read directly — no conversion needed. Sniff the delimiter and encoding first
(`chardet`, or try `utf-8` then `cp1252`). If the file exceeds 1000 rows, report the header,
dtypes, row count, and a 20-row sample rather than the whole file.

## Verify before returning

- [ ] Output length is plausible for the source's page or sheet count.
- [ ] Headings form a sensible hierarchy with no skipped levels.
- [ ] Tables have consistent column counts across rows.
- [ ] No raw XML tags, `w:`, `a:`, or `r:` prefixes survived.
- [ ] Encoding artefacts (`â€™`, `Â`) are cleaned up.

## Deliver

Write the Markdown beside the source or into the session output directory, and state which
converter was used. If the file was a spreadsheet emitted as CSV, present the CSV path too.
