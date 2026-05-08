#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "reportlab", "pdfplumber"]
# ///
"""Apply redline markup (strikethroughs + insertions) to a flat PDF as a
reportlab overlay.

Mechanical constraints (see SKILL.md):
  - Strikethrough alone usually suffices; skip insertions when deletion produces
    grammatically valid output
  - Use pdfplumber to extract word-level coordinates BEFORE drawing — never estimate
  - For insertions where there's no inline whitespace, route to right margin
    with caret + leader line. Don't add "Page Na" replacement pages
  - Don't overlay near combobox `/Rect` left edges (~12pt clip from chevron)

Strike rect format: (x0, y_top, x1, y_bot) — extracted from pdfplumber word boxes.

Usage (template — copy and edit STRIKES / INSERTIONS):
    uv run render_redlines.py <source.pdf> <output.pdf>
"""
import argparse
import io
import sys

import pypdf
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas


# ---- EDIT THIS BLOCK PER REDLINE ----
RED = HexColor("#C00000")

# Strikes per page: page_index → list of (x0, y_top, x1, y_bot) rects
STRIKES_BY_PAGE = {
    # 2: [
    #     (288.7, 389.6, 429.2, 440.2),  # "by phone or internet,"
    #     (77.9, 192.8, 444.2, 455.2),   # "meeting the patient and"
    # ],
}

# Margin insertions: page_index → list of dicts
# {anchor_x, anchor_y_top, anchor_y_bot, addition_text, addition_x, addition_y_baseline}
# Caret at anchor, dashed leader to addition in right margin.
INSERTIONS_BY_PAGE = {
    # 2: [
    #     {
    #         "anchor_x": 264.5,
    #         "anchor_y_baseline_top": 455.2,
    #         "addition_text": " legal practitioner-patient",
    #         "addition_x": 392,
    #     },
    # ],
}
# ---- END EDIT BLOCK ----


def draw_overlay_for_page(page_w, page_h, strikes, insertions):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    def y(top):
        return page_h - top

    # Strikethroughs
    c.setStrokeColor(RED)
    c.setLineWidth(0.8)
    for x0, y_top, x1, y_bot in strikes:
        y_mid = y((y_top + y_bot) / 2.0)
        c.line(x0, y_mid, x1, y_mid)

    # Margin insertions: caret + dashed leader + underlined italic text
    for ins in insertions:
        anchor_x = ins["anchor_x"]
        anchor_y = y(ins["anchor_y_baseline_top"])
        add_text = ins["addition_text"]
        add_x = ins["addition_x"]
        add_y = anchor_y

        # Caret
        c.setFillColor(RED)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(anchor_x - 2, anchor_y - 1, "^")

        # Inserted text — italic, underlined
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(add_x, add_y, add_text)
        add_w = c.stringWidth(add_text, "Helvetica-Oblique", 9)
        c.setStrokeColor(RED)
        c.setLineWidth(0.5)
        c.line(add_x, add_y - 1, add_x + add_w, add_y - 1)

        # Dashed leader from caret to addition
        c.setLineWidth(0.4)
        c.setDash(2, 2)
        c.line(anchor_x + 4, anchor_y + 2, add_x - 2, add_y + 2)
        c.setDash()

    c.save()
    buf.seek(0)
    return buf


def render(source, output):
    src = pypdf.PdfReader(source)
    if src.is_encrypted:
        src.decrypt("")
    writer = pypdf.PdfWriter()

    for i, page in enumerate(src.pages):
        strikes = STRIKES_BY_PAGE.get(i, [])
        insertions = INSERTIONS_BY_PAGE.get(i, [])
        if strikes or insertions:
            page_w = float(page.mediabox.width)
            page_h = float(page.mediabox.height)
            overlay = pypdf.PdfReader(
                draw_overlay_for_page(page_w, page_h, strikes, insertions)
            )
            page.merge_page(overlay.pages[0])
        writer.add_page(page)

    with open(output, "wb") as f:
        writer.write(f)
    print(f"wrote {output}")
    print()
    print("NEXT: render with scripts/verify_render.py @ 220 dpi.")
    print("Read every redlined page. Coordinate collisions are silent in code.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="path to source PDF (flat, no AcroForm)")
    ap.add_argument("output", help="path to redlined output PDF")
    args = ap.parse_args()
    render(args.source, args.output)


if __name__ == "__main__":
    sys.exit(main())
