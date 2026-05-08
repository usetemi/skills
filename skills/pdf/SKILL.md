---
name: pdf
description: Fill, redline, and generate PDFs with the right tool for the source. Detects AcroForm vs flat PDFs, handles AES-encrypted government forms, navigates appearance-stream gotchas, and verifies every output by rendering. Use when the user asks to fill a PDF form, redline a PDF, generate a PDF from markdown, or reproduce a packet of forms. PDF-only — DOCX, XLSX, and other formats are out of scope.
---

# PDF Mechanics

## Role
The mechanical layer for PDF work. Domain skills (legal, finance, regulatory packets) decide *what* the document should say. This skill decides *how* to produce it correctly. Domain skills delegate here rather than re-derive PDF mechanics each session.

**Scope:** PDF only. DOCX track-changes, XLSX, image manipulation belong in their own skills.

## First step: inspect, then choose path

```
SOURCE                     GOAL              PATH
──────                     ────              ────
PDF (encrypted)            anything          decrypt first → re-inspect
PDF (AcroForm fields > 0)  fill              scripts/fill_acroform.py
PDF (AcroForm fields > 0)  redline           overlay onto AcroForm; fill is for values, not markup
PDF (flat, 0 fields)       fill              scripts/fill_overlay.py
PDF (flat, 0 fields)       redline           scripts/render_redlines.py
Markdown                   generate PDF      scripts/markdown_to_pdf.py
```

**Always run `scripts/inspect_pdf.py <file>` first.** It reports: page count, encryption status, AcroForm field count + names + types + tooltips per page, mediabox dimensions per page, embedded fonts. Two PDFs in the same packet from the same sender can be one flat and one form-equipped — always count fields **per-PDF**, never per-packet.

**Never start with overlay if AcroForm fields exist.** The field path is faster, more accurate, and survives flatten/print. It also auto-handles per-digit SSN boxes, per-character date boxes, and combobox dropdowns that overlay would require pixel-calibrating.

## Library choices (no option paralysis)

- **`pypdf`** for AcroForm reads/writes. `PyPDF2` is legacy; pypdf supports `PdfWriter(clone_from=reader)` and is actively maintained.
- **`reportlab`** for any text/line drawing onto a canvas (overlays, generation).
- **`pdfplumber`** for word-level coordinate extraction. Never estimate coordinates.
- **`pycryptodome`** for AES decryption (transitively used by pypdf when reading encrypted forms).
- **`pdftoppm`** (poppler-utils) for static rasterization. **See verification section — pdftoppm does NOT honor `NeedAppearances`** and is a false-negative source for AcroForm fills.
- **Playwright** with Chrome's PDF viewer for verification of AcroForm fills. Chrome regenerates appearance streams; pdftoppm doesn't.

## Path: AcroForm fill

When `inspect_pdf.py` reports `acroform_fields > 0`:

```python
import pypdf
from pypdf.generic import BooleanObject, NameObject

reader = pypdf.PdfReader(SOURCE)
writer = pypdf.PdfWriter(clone_from=reader)

# /NeedAppearances=True forces COMPLIANT viewers to regenerate field
# appearance streams from /V values. Chrome, Adobe Reader, Mac Preview
# honor it. pdftoppm and many static rasterizers do NOT — see verification.
acroform = writer._root_object["/AcroForm"]
if hasattr(acroform, "get_object"):
    acroform = acroform.get_object()  # pypdf >=4 returns IndirectObject
acroform[NameObject("/NeedAppearances")] = BooleanObject(True)

# Fill per-page, NOT document-wide. Field names like "Document Title 1"
# repeat across Section 2 and Supplement B; document-wide writes mass-fill.
for i, page in enumerate(writer.pages):
    page_fields = FIELDS_BY_PAGE.get(i, {})
    if page_fields:
        writer.update_page_form_field_values(page, page_fields)

with open(OUT, "wb") as f:
    writer.write(f)
```

`scripts/fill_acroform.py` is this template; copy and edit `FIELDS_BY_PAGE`.

### Field discovery

`inspect_pdf.py` prints every field's `name` (`/T`), `type` (`/FT`: `Tx`/`Btn`/`Ch`/`Sig`), `tooltip` (`/TU`), `rect`, and `current_value` (`/V`). Cryptic names are common: `f1_07`, `c1_3[0]`, even typo'd names like `Today's Date mmddyyy` (one fewer `y` than the tooltip claims). Build a `name → tooltip → expected value` map per template; never hardcode across template versions.

### Field-type quirks

- **`/Tx` text fields:** `update_page_form_field_values` works. Just set the string.
- **`/Btn` checkboxes:** value is `/Yes` or `/Off` (or the per-button "on" state from `/AP/N` keys). Use `inspect_pdf.py` to see the on-state name.
- **`/Btn` radio buttons:** the parent field's `/V` selects the active child. Don't write to children.
- **`/Ch` comboboxes (state dropdowns, etc.):** **silently no-op when value isn't in `/Opt`.** Set the string AND set `/I` (selection index into `/Opt`). Strip `/AP` for that field to force regeneration. Comboboxes are the #1 "data set, value invisible" trap.
- **`/Sig` signature widgets:** **never fill.** Filling `/V` corrupts them. Filter out during fill loops; let DocuSeal/Adobe place the signature.
- **Internal-only fields** (e.g., "Account created by", "Verified By Pharmacist"): comment them out of `FIELDS_BY_PAGE` so the next agent sees they were intentionally skipped.

### Multi-page government form headers

IRS forms (2553, 8832, etc.), USCIS forms, and many state filings have name+EIN headers (`f2_01`/`f2_02`, `f3_01`/`f3_02`, `f4_01`/`f4_02`) that **must carry forward on every page** even when the substantive parts (II/III/IV) don't apply. Auditors and IRS scanners read field data directly; rendering preview misses the structure. Always populate page headers across the entire form.

### Iteration discipline

**Re-clone from the original template every fill.** Don't iterate by saving, editing, saving, editing. Stale appearance streams from earlier saves persist; some fields will show yesterday's value despite today's `/V`. Pattern:

```python
def fill():
    reader = pypdf.PdfReader(TEMPLATE)              # original, untouched
    writer = pypdf.PdfWriter(clone_from=reader)
    # ... mutate writer ...
    writer.write(open(OUT, 'wb'))                    # save once
```

## Path: flat PDF overlay (reportlab merge)

When `acroform_fields == 0` and the document has visible underlines/checkboxes:

1. **Run pdfplumber word extraction** to get exact label coordinates. Don't estimate.
2. **Build one reportlab canvas per page.** Coordinate origin: pdfplumber returns y from top of page; reportlab measures y from bottom. Use `y_top → PAGE_H - y_top`.
3. **Detect page size from the source.** `inspect_pdf.py` reports `mediabox` per page. Don't assume letter — A4 (595 × 842.25) and letter (612 × 792) coexist in mixed packets.
4. **Merge each overlay page onto the corresponding source page** with `page.merge_page(overlay_page)`.

```python
import io, pypdf
from reportlab.pdfgen import canvas

def draw_overlay(values, page_w, page_h):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    c.setFont("Helvetica", 10)
    def y(top): return page_h - top  # pdfplumber→reportlab origin flip
    for (x, y_top, text) in values:
        c.drawString(x, y(y_top), text)
    c.showPage(); c.save(); buf.seek(0); return buf

src = pypdf.PdfReader(SOURCE)
writer = pypdf.PdfWriter()
for i, page in enumerate(src.pages):
    w, h = float(page.mediabox.width), float(page.mediabox.height)
    overlay = pypdf.PdfReader(draw_overlay(VALUES_BY_PAGE.get(i, []), w, h))
    page.merge_page(overlay.pages[0])
    writer.add_page(page)
```

`scripts/fill_overlay.py` is this template.

### Don't overlay on top of live widgets

PDF rendering order is **page content → reportlab overlay → live widgets (annotations, drawn last).** If a flat-looking PDF actually has even one live AcroForm widget on the page, the widget paints opaque over your overlay. Adobe shows blank where the static PNG showed your text. Either flatten the widget first (remove from `/Annots`) or fill via `/V` instead. `inspect_pdf.py` flags widgets per page so this isn't a surprise.

## Path: PDF redline (overlay with strikethrough/insertion)

For markup on existing PDFs (vendor contracts, applications). Same merge mechanic as fill overlay; the drawn primitives are strikethroughs and insertion carets.

### Mechanical constraints

- **Strikethrough alone usually suffices.** When deleting a phrase produces grammatically valid output, skip the insertion. "Strike X, insert Y of the same meaning" is noise. Inline insertions on dense pages collide with adjacent baselines — strikethrough doesn't.
- **Word-level whitespace matters.** Use pdfplumber to get exact word rects. Inline insertions need clear horizontal whitespace at the same line. If no clear gap exists, route the insertion to the right margin with a caret + leader line connecting them — not a separate page.
- **No replacement pages** unless the original page has zero margin space *and* the addition is genuinely long. The cover email does the "explain the redline" job better.

`scripts/render_redlines.py` is the template. The list-of-strikes pattern (`(x0, y_top, x1, y_bot)` rects) is the right shape for terse session inputs.

### Combobox dropdown clip

Combobox `/Rect` covers the input area, but the dropdown chevron paints starting at the right edge. Drawing markup at `rect[0]` (left edge) gets covered. Draw centered or right of `rect[0]+~12pt` if you must overlay near a combobox.

## Path: AES-encrypted government PDFs

Most state Judicial Council and federal agency forms ship AES-encrypted with appearance streams that don't regenerate on fill. Standard form-fill on the encrypted original produces invisible values.

```python
import pypdf
reader = pypdf.PdfReader(ENCRYPTED_PATH)
if reader.is_encrypted:
    reader.decrypt('')  # most government forms have empty owner password
writer = pypdf.PdfWriter(clone_from=reader)
writer.write(open(DECRYPTED_PATH, 'wb'))
```

Decrypt once into `templates/`, work from the decrypted copy. `scripts/decrypt_template.py` is the template. After decryption, re-run `inspect_pdf.py` against the decrypted file — encryption can hide field counts.

## Path: markdown → PDF generation

When the source is a markdown document the agent itself authored (legal docs, side letters, board resolutions). The markdown is the canonical text; this path renders it to a styled PDF.

`scripts/markdown_to_pdf.py` parses an annotated markdown grammar:

```
<h1 class="title">...</h1>           → centered bold title
<p class="recital">...</p>           → hanging-indent recital
<p class="indent">...</p>            → indented paragraph
<span class="mono">...</span>        → inline monospace
<div class="signatures">A | B</div>  → two-column signature block
**N. Section Name**                  → section heading
N.N *Name.* Text...                  → numbered section paragraph
**IN WITNESS WHEREOF**...            → witness clause
**Bold** / *Italic*                  → inline formatting
```

The annotation grammar is HTML-class-tagged so editors preview the source as plain markdown and the renderer has unambiguous parsing rules. **Custom domain extensions** (e.g., `<p class="rosca-disclosure">` for ROSCA-required formatting) live in the calling skill, not here.

## Verification (mandatory gate)

After any fill/redline/generate operation, run **two layers** of verification:

### Layer 1: data audit (programmatic, fast)

Read `/V` of every field after fill, compare against intended values, flag mismatches. Build the audit table:

```
Field            | Type | Expected   | Actual     | ✓/✗
─────────────────────────────────────────────────────────
Clinic Name      | Tx   | Kevin...   | Kevin...   | ✓
State            | Ch   | TX         | TX         | ✓
Signature        | Sig  | (skipped)  | (empty)    | ✓
Today's Date     | Tx   | 05/07/2026 | 05/06/2026 | ✗
```

Especially important for combobox/checkbox where appearance lags data. The audit catches silent failures the rendered preview misses.

### Layer 2: visual render (renderer-aware)

`scripts/verify_render.py <pdf>` rasterizes every page to PNG. Read every page visually. **But:** pick the renderer based on what you're verifying:

```
WHAT YOU FILLED                   USE THIS RENDERER          WHY
───────────────                   ─────────────────          ───
flat overlay only                 pdftoppm @ 220 dpi         no appearance streams to regenerate
AcroForm /V via NeedAppearances   Chrome via Playwright      pdftoppm doesn't honor NeedAppearances
                                  OR flatten via Adobe first then pdftoppm
markdown→PDF generated            pdftoppm @ 220 dpi         self-contained, no streams
```

**Renderer escalation ladder when the data audit passes but the render is blank:**

1. Static rasterize with pdftoppm → if blank, escalate
2. Open in Chrome via Playwright (or `playwright open file://path.pdf`) → renders the way Adobe does
3. Open in Adobe Reader manually → ground truth
4. If Adobe shows the value, the file is correct; pdftoppm is the limitation, not the PDF.

**Don't burn cycles trying to make pdftoppm render NeedAppearances output.** That's a renderer limitation, not a PDF bug. Ship to the receiving renderer (counterparty's Adobe, DocuSeal, signing platform) and verify there.

### Audit table is mandatory when

- The document has discrete fields a reviewer or counterparty will check (applications, government forms, vendor onboarding paperwork)
- The document is going to a signing service (DocuSeal, Adobe Sign)
- The document will be filed with a regulator

Skip the audit table for free-form prose generation (markdown→PDF) where the source is the audit.

## Anti-patterns

- **Filling encrypted PDFs without decrypting.** Values land in `/V` but `/AP` doesn't regenerate; rendering shows blank.
- **Reaching for reportlab overlay before checking for AcroForm fields.** Always inspect first.
- **Document-wide field updates instead of per-page.** Repeated names like `Document Title 1` mass-write.
- **Iterating by re-saving.** Stale appearance streams persist across saves. Re-clone from template every fill.
- **Combining `/AP` strip with `pdftk flatten`.** pdftk reads from `/AP/N` to flatten; if you stripped `/AP` to force regeneration, flatten produces blank fields. Pick one path.
- **Overlaying text onto live widgets.** Widget appearance streams paint over the overlay in Adobe.
- **Trusting pdftoppm for AcroForm rendering verification.** It doesn't honor `NeedAppearances`.
- **Writing to `/Sig` signature fields.** Corrupts the widget. Filter them out.
- **Writing to combobox `/Ch` fields without setting `/I`.** Silently no-ops.
- **Estimating PDF coordinates.** Use pdfplumber's word-level extraction.
- **Hardcoding field names across template versions.** Government forms revise; field names change. Re-discover via `inspect_pdf.py` per template download.
- **Outputting placeholder text** (`[SSN]`, `[TODO]`) **in filing-ready documents.** Read sensitive data from `.secrets` at fill time.
- **Adding "Page Na" replacement pages** when a margin caret + cover email would do.
- **Flattening before signing.** Flatten is one-way. Keep AcroForm working copy in `working_data/`; flatten only the post-signature archive copy.
- **Using `PyPDF2`** when `pypdf` is available. PyPDF2 lacks `clone_from`.

## When to escalate to a domain skill

This skill is mechanical. Escalate when:

- The question is *what* the document should say — domain skills decide content
- The question is *which* field maps to which value — domain context decides (whose name, which entity, what address)
- The question involves regulatory citations, statutory language, or legal characterization
- Multiple valid form-fill paths exist and the choice has compliance implications

Calling skills (`legal`, `finance`, etc.) handle those calls and pass the resolved spec to this skill for execution.
