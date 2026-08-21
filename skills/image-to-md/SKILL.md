---
name: image-to-md
description: Convert an image — a screenshot, scan, photographed page, chart, or diagram — into Markdown, extracting text cheaply out of band and structuring it separately. Use whenever an image must be read, quoted, or referenced rather than visually judged.
---

# Convert an image to Markdown

Turns an image into text you can quote, search, and diff. Two stages, split by what each half
actually needs:

| Stage | Tier | Does |
| --- | --- | --- |
| 1. Extract | cheap | OCR the characters and caption what is visible. Deterministic |
| 2. Structure | deep | Turn that raw text into Markdown — headings, tables, corrected OCR |

The split is the point. Extraction is mechanical and produces noisy output that should never
enter the working context. Structuring needs to know what the content *means* — which lines
are a heading, which whitespace was a table — and that is judgement.

This is for reading an image. To judge how an interface *looks*, use `visual-verify`; to
capture a terminal, use `tui-screenshots`.

## Delegation

Spawn `../../agents/image-extractor.md` (tier `cheap`) for stage 1, then
`../../agents/doc-structurer.md` (tier `deep`) for stage 2, passing it the extracted text and
**not** the image. Read back only the finished Markdown.

Without subagents, run the procedure below in a scratch directory and read back only the
final file. The raw OCR dump should not reach your main context either way — that is the
token saving, and reading it after receiving the structured version spends it again.

## Step 1 — classify the image first

The right extraction depends entirely on this, and getting it wrong wastes the whole pass.

| Image | Treat as | Approach |
| --- | --- | --- |
| Screenshot of text, UI, or a terminal | Text | OCR directly; it is already high contrast |
| Scan or photograph of a page | Document | Deskew and threshold first, then OCR |
| Chart or graph | Data | OCR the labels, axes, and legend. Describe the trend; **never** read values off the plot area |
| Diagram or flowchart | Structure | OCR the node labels, then describe the connections as a list or Mermaid |
| Photograph with incidental text | Scene | Caption it; OCR only if the text is the reason it was provided |
| Handwriting | Low confidence | Attempt it, mark the whole output uncertain, and say so plainly |

## Step 2 — extract

```bash
tesseract input.png output_base -l eng          # writes output_base.txt
tesseract input.png out --psm 6                 # a uniform block of text
tesseract input.png out --psm 11                # sparse text, e.g. a UI screenshot
```

Preprocess only when the first attempt is poor — an already-clean screenshot is degraded by
thresholding, not improved:

```bash
magick input.jpg -colorspace Gray -deskew 40% -threshold 60% clean.png
```

For a PDF page, do not screenshot it. Use the `pdf-to-md` skill, which reads the text layer
directly and is both exact and cheaper than OCR-ing a render of it.

## Step 3 — structure

Hand the extracted text to the deep tier. It reconstructs what layout destroyed — heading
levels, tables from aligned whitespace, list markers, joined line-wraps — and corrects the
systematic OCR confusions (`rn`→`m`, `0`↔`O`, `1`↔`l`, `5`↔`S`) only where the surrounding
word makes the reading unambiguous.

Anything genuinely ambiguous stays as extracted and is marked `[?]`. A silent guess is
indistinguishable from source text downstream, and the only value this file has is that
someone can rely on it.

## Step 4 — numbers, and charts especially

Never reformat, round, or recompute an extracted number, date, or identifier. Reproduce it as
extracted.

For charts, this hardens into a rule: **read values only from printed labels.** Do not
estimate a value from a bar's height or a point's position. A number inferred from pixels
looks exactly like a number that was written down, and it will be quoted onward into a
decision by someone who cannot tell the difference. If a chart has no data labels, say the
values are not recoverable and describe the shape instead.

## Step 5 — verify before returning

- [ ] Every heading in the image appears as a heading, at a sensible level.
- [ ] Tables are Markdown tables, with the header row that the image had.
- [ ] No line-wrap artefacts remain mid-sentence.
- [ ] Numbers match the image exactly, character for character.
- [ ] Every chart value came from a printed label, not from the plot area.
- [ ] Uncertain text is marked `[?]` rather than guessed.
- [ ] The raw OCR dump was not read into the main context.

## Step 6 — deliver

Return the Markdown file's path and a one-line summary of what the image contained. End with
`## Extraction notes` covering anything unreadable, anything marked `[?]`, and any structure
that was inferred rather than read. If none apply, say so in one line — that section is what
tells the reader how far to trust the rest.

## Do not

- Do not paste raw OCR output into your reply. It is the noise this skill removes.
- Do not read values off a chart's plot area.
- Do not "improve" wording, fix the source's grammar, or summarise instead of transcribing.
- Do not invent content for an unreadable region. Mark it and move on.
- Do not OCR a PDF page render when the PDF has a text layer.
