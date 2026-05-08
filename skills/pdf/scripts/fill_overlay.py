#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "reportlab", "pdfplumber"]
# ///
"""Fill a flat PDF (no AcroForm fields) by overlaying reportlab text onto each page.

Pattern:
  1. Run inspect_pdf.py first; only use this path when acroform_field_count == 0
  2. Use pdfplumber to extract exact word coordinates for label positions —
     never estimate
  3. Detect page size from mediabox; don't assume letter
  4. Coordinate flip: pdfplumber returns y from top, reportlab measures from
     bottom: y_reportlab = page_height - y_top
  5. Don't overlay onto live widgets (rare in flat PDFs but check)

Usage (template — copy and edit VALUES_BY_PAGE for your form):
    uv run fill_overlay.py <template.pdf> <output.pdf>
"""
import argparse
import io
import sys

import pypdf
from reportlab.lib.colors import HexColor, black
from reportlab.pdfgen import canvas


# ---- EDIT THIS BLOCK PER FORM ----
# Map page index (0-based) → list of (x, y_top, text, [font, size]) tuples.
# y_top is from the TOP of the page (pdfplumber convention).
# Font/size optional; defaults to Helvetica 10.
INK = HexColor("#0B3D91")  # blue-black for visibly filled-in feel; use black for prints

VALUES_BY_PAGE = {
    0: [
        # (x, y_top, text)
        (64, 316, "EXAMPLE PRACTICE NAME"),
        (64, 365, "Kevin Brandstetter, M.D."),
    ],
    # 1: [...],
    # 2: [...],
}

# Checkbox marks: list of (page_idx, x_center, y_top_center) — draws an "X"
CHECKBOX_MARKS = [
    # (3, 241.8, 150.7),
]
# ---- END EDIT BLOCK ----


def draw_overlay(values, page_w, page_h, color=INK, font="Helvetica", size=10):
    """Build a single-page reportlab overlay matching the source page size."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    c.setFillColor(color)
    c.setFont(font, size)

    def y(top):
        return page_h - top

    for entry in values:
        if len(entry) == 3:
            x, y_top, text = entry
            f, s = font, size
        elif len(entry) == 5:
            x, y_top, text, f, s = entry
            c.setFont(f, s)
        else:
            raise ValueError(f"bad entry: {entry}")
        c.drawString(x, y(y_top), text)
        c.setFont(font, size)

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def draw_checkbox(c, x_center, y_baseline, color=INK):
    c.setFillColor(color)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_center - 3, y_baseline, "X")


def fill(template, output):
    src = pypdf.PdfReader(template)
    if src.is_encrypted:
        src.decrypt("")
    writer = pypdf.PdfWriter()

    for i, page in enumerate(src.pages):
        page_w = float(page.mediabox.width)
        page_h = float(page.mediabox.height)

        page_values = VALUES_BY_PAGE.get(i, [])
        page_marks = [(x, y) for (pi, x, y) in CHECKBOX_MARKS if pi == i]

        if page_values or page_marks:
            buf = io.BytesIO()
            c = canvas.Canvas(buf, pagesize=(page_w, page_h))
            c.setFillColor(INK)
            c.setFont("Helvetica", 10)

            def y_flip(top):
                return page_h - top

            for entry in page_values:
                if len(entry) == 3:
                    x, y_top, text = entry
                    c.drawString(x, y_flip(y_top), text)
                elif len(entry) == 5:
                    x, y_top, text, font, size = entry
                    c.setFont(font, size)
                    c.drawString(x, y_flip(y_top), text)
                    c.setFont("Helvetica", 10)

            for x_center, y_top in page_marks:
                draw_checkbox(c, x_center, y_flip(y_top))

            c.save()
            buf.seek(0)
            overlay = pypdf.PdfReader(buf)
            page.merge_page(overlay.pages[0])

        writer.add_page(page)

    with open(output, "wb") as f:
        writer.write(f)
    print(f"wrote {output}")
    print()
    print("NEXT: render with scripts/verify_render.py and walk every page.")
    print("Flat overlays render reliably in pdftoppm @ 220 dpi.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template", help="path to source flat PDF")
    ap.add_argument("output", help="path to filled output PDF")
    args = ap.parse_args()
    fill(args.template, args.output)


if __name__ == "__main__":
    sys.exit(main())
