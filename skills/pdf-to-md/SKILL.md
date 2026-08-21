---
name: pdf-to-md
description: Use whenever a PDF must be read, quoted, or referenced, by any model. Converts it to Markdown out of band so PDF binary noise and OCR artefacts never enter the working context.
---

# Convert a PDF to Markdown

Produces a clean Markdown file from a PDF. The main context reads only the resulting
Markdown — never the raw PDF, and never the OCR output directly.

## Delegation

Two stages, split by what each half actually needs:

| Stage | Agent | Tier | Why that tier |
| --- | --- | --- | --- |
| Extract (steps 1-3) | `../../agents/pdf-extractor.md` | cheap | Deterministic — getting characters off the page |
| Structure (step 4) | `../../agents/doc-structurer.md` | deep | Deciding what those characters *mean* structurally |

Pass the deep stage the **extracted text, not the PDF**. Re-opening the binary puts back
exactly the noise this split exists to keep out, and everything it needs is already in the
extraction.

The split matters because the two halves fail differently. Extraction fails loudly — a
garbled character is visible. Structuring fails quietly: a table flattened into prose, a
heading demoted to body text, and two columns interleaved all read as plausible text, so
nobody notices until a quote turns out to be wrong.

If your runtime has no subagents, follow the procedure below inline, in a scratch directory,
and read back only the finished Markdown. Do not read the raw extraction after receiving the
structured version — that spends the tokens the split just saved.

## Procedure

### Step 1 — establish what kind of PDF it is

```bash
pdffonts input.pdf | head        # fonts listed  -> has a real text layer
pdftotext -f 1 -l 2 input.pdf -  # prints text   -> confirmed
```

If `pdftotext` prints nothing or only whitespace across the first two pages, the PDF is
scanned images and needs OCR (step 3). Otherwise use the text layer (step 2). Getting this
right matters: OCR-ing a PDF that already has text throws away accuracy for no reason.

### Step 2 — extract the text layer

Try these in order and use the first that is installed:

```bash
# Best layout fidelity, handles tables and columns
pdftotext -layout input.pdf output.txt

# Python, gives you page control and can also dump images
python -c "import pymupdf,sys; d=pymupdf.open('input.pdf'); print(chr(12).join(p.get_text() for p in d))" > output.txt

# Good on tables specifically
python -c "import pdfplumber; ..."
```

If none are installed:

```bash
pip install pymupdf --break-system-packages -q
```

### Step 3 — OCR, only if step 1 said to

```bash
ocrmypdf --skip-text --optimize 0 input.pdf ocr.pdf && pdftotext -layout ocr.pdf output.txt
```

If `ocrmypdf` is unavailable, rasterise and OCR page by page:

```bash
pdftoppm -r 300 -png input.pdf page      # 300 dpi; lower loses small type
for f in page-*.png; do tesseract "$f" "${f%.png}" -l eng txt; done
cat page-*.txt > output.txt
```

Record in the output that the text came from OCR, and at what dpi. Downstream readers need
to know that character-level errors are possible.

### Step 4 — clean up into Markdown

Apply each of these, in order:

1. **Rejoin wrapped lines.** A line that does not end in `.`, `:`, `;`, `?`, `!`, or a
   closing bracket, and whose next line starts lowercase, is a hard-wrapped continuation —
   join them with a space.
2. **Repair hyphenation.** `inter-\nnational` becomes `international`. Only when the next
   line starts lowercase.
3. **Strip running headers and footers.** Any short line that repeats on three or more
   pages at the same position is furniture. Remove it.
4. **Remove page numbers.** Lines that are a bare number, or `Page N of M`.
5. **Promote headings.** A short line, title-case or all-caps, standing alone between blank
   lines, followed by body text, becomes an ATX heading. Preserve the document's own
   numbering (`3.1 Scope` becomes `### 3.1 Scope`) rather than inventing a hierarchy.
6. **Rebuild tables** as Markdown pipe tables. `-layout` preserves column spacing, so split
   on runs of two or more spaces. If a table will not survive the conversion, keep it in a
   fenced block instead and say so — a mangled Markdown table is worse than fixed-width text.
7. **Mark page boundaries** with `<!-- page N -->` comments. This is what makes citation back
   to the source possible; do not skip it.
8. **Note dropped figures** as `![figure: <caption if any>](#)` so the reader knows content
   existed there.

### Step 5 — verify before returning

- [ ] Output is non-trivial in size relative to the page count (a 40-page PDF yielding 2 KB
      means extraction failed — go back to step 1).
- [ ] Page markers are present and monotonic.
- [ ] Spot-check three pages spread through the document against the original.
- [ ] No `\f`, `\x0c`, or stray control characters remain.
- [ ] Ligatures are normalised: `ﬁ ﬂ ﬀ` to `fi fl ff`.

### Step 6 — deliver

Write the Markdown next to the PDF, or into the session output directory. If the user asked
to keep it, present it as a file. State in one line which extraction path was used (text
layer or OCR) and any pages that failed.

## Do not

- Do not read the raw PDF bytes into context.
- Do not paste the whole intermediate OCR text into context — write it to a file and clean
  the file.
- Do not silently truncate. If the PDF is very large, convert it all and say which sections
  you actually read.
