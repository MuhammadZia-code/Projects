# GEM Template Library → Navigable PDF

Tooling that turns the `TPL` directory of CMG GEM simulation templates (hundreds
of individual `.dat` decks organized into category folders) into a single,
fully navigable PDF.

## What the PDF contains

- **Master Table of Contents** — the full name of every category (e.g.
  `ASP MODELING` for `asp`, `GREENHOUSE GAS` for `ghg`), taken from each
  folder's `*000.doc` file. Every category name is a clickable hyperlink that
  jumps to that category's table of contents.
- **One Table of Contents per category** — lists each case (`gmasp001`,
  `gmasp002`, …) together with the brief description from the category's `.doc`
  file. Every case id is a clickable hyperlink that jumps to that `.dat` file.
- **One section per `.dat` file** — each file **starts on a new page**, with a
  header band (file name, description, and "back to TOC" links) and **line
  numbers down the full length of the file**. Long lines wrap while keeping a
  single line number per source line.
- **PDF outline / bookmarks sidebar** mirroring the structure
  (category → case) for quick navigation in any PDF viewer.

## Regenerating

```bash
# 1. Extract the templates so that ./TPL/<category>/*.dat exist
unzip TPL.zip            # produces ./TPL/...

# 2. Install dependencies (reportlab renders; pypdf shrinks the result)
pip install reportlab pypdf

# 3. Build the PDF  (override the source dir with TPL_DIR=... if needed)
python3 scripts/generate_pdf.py GEM_Template_Library.pdf
```

`reportlab` is required; `pypdf` is optional — if present, the build runs a
final pass that de-duplicates identical objects and recompresses page streams
(keeping the outline and all internal links), which cuts the file from
~37 MB to ~24 MB. If `pypdf` is not installed, that step is skipped.

The build reads every `.dat` file and the category `.doc` files, so re-running
it picks up any added or changed templates automatically.

## Files

| File | Purpose |
|------|---------|
| `scripts/parse_tpl.py`   | Parses category `.doc` files for titles and per-case descriptions, and builds the folder/case data model. |
| `scripts/generate_pdf.py`| Renders the navigable PDF (TOCs, per-file pages, line numbers, hyperlinks, outline) with ReportLab. |

## Notes on the source data

- Descriptions come straight from the category `*000.doc` files. A handful of
  cases have no usable description because the source `.doc` omits them or
  contains a typo (e.g. `GMFLU))$.DAT` for `gmflu004`); those show `—` in the
  TOC, which is faithful to the source.
- `.doc` files are plain text; non-ASCII separators (en-dashes stored as
  Windows-1252 bytes) and smart quotes are decoded and handled.
