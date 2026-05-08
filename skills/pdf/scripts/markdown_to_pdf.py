#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["reportlab"]
# ///
"""Generate a styled PDF from an annotated markdown legal/business document.

The markdown is the canonical text; this script controls layout/styling.

Supported grammar:
    <h1 class="title">...</h1>           Centered bold title
    <p class="recital">...</p>           Hanging-indent recital
    <p class="indent">...</p>            Indented paragraph
    <span class="mono">...</span>        Inline monospace
    <div class="signatures">A | B</div>  Two-column signature block
    **N. Section Name**                  Section heading
    N.N *Name.* Text...                  Numbered section paragraph
    **IN WITNESS WHEREOF**...            Witness clause
    **Bold** / *Italic*                  Inline formatting
    # H1 line                            Skipped (markdown viewer only)

Custom domain extensions belong in the calling skill, not here.

Usage:
    uv run markdown_to_pdf.py <markdown_path> [output_path]
"""
import argparse
import os
import re
import sys

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT = "Times-Roman"
FONT_BOLD = "Times-Bold"

style_title = ParagraphStyle(
    "Title", fontName=FONT_BOLD, fontSize=14, alignment=TA_CENTER,
    spaceAfter=6, leading=18,
)
style_heading = ParagraphStyle(
    "Heading", fontName=FONT_BOLD, fontSize=11, spaceBefore=16,
    spaceAfter=6, leading=14,
)
style_body = ParagraphStyle(
    "Body", fontName=FONT, fontSize=10, alignment=TA_JUSTIFY,
    spaceAfter=8, leading=13,
)
style_body_indent = ParagraphStyle(
    "BodyIndent", fontName=FONT, fontSize=10, alignment=TA_JUSTIFY,
    spaceAfter=8, leading=13, leftIndent=24,
)
style_recital = ParagraphStyle(
    "Recital", fontName=FONT, fontSize=10, alignment=TA_JUSTIFY,
    spaceAfter=6, leading=13, leftIndent=24, firstLineIndent=-24,
)
style_section = ParagraphStyle(
    "Section", fontName=FONT, fontSize=10, alignment=TA_JUSTIFY,
    spaceAfter=8, leading=13,
)
style_sig = ParagraphStyle(
    "Sig", fontName=FONT, fontSize=10, spaceAfter=4, leading=13,
)


def md_to_rl(text):
    """Inline markdown → reportlab XML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(
        r'<span class="mono">(.*?)</span>',
        r'<font face="Courier" size="9">\1</font>',
        text,
    )
    return text


def parse_markdown(path):
    with open(path) as f:
        raw = f.read()

    blocks = re.split(r"\n\n+", raw.strip())
    elements = []

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        if block.startswith("# "):
            continue  # markdown-only title

        if '<h1 class="title">' in block:
            m = re.search(r'<h1 class="title">(.*?)</h1>', block, re.DOTALL)
            if m:
                elements.append(("title", m.group(1).strip()))
            continue

        if '<p class="recital">' in block:
            for m in re.finditer(r'<p class="recital">(.*?)</p>', block, re.DOTALL):
                elements.append(("recital", md_to_rl(m.group(1).strip())))
            continue

        if '<p class="indent">' in block:
            for m in re.finditer(r'<p class="indent">(.*?)</p>', block, re.DOTALL):
                elements.append(("indent", md_to_rl(m.group(1).strip())))
            continue

        if '<div class="signatures">' in block:
            m = re.search(
                r'<div class="signatures">\s*(.*?)\s*</div>', block, re.DOTALL
            )
            if m:
                elements.append(("signatures", m.group(1).strip()))
            continue

        if block.startswith("**IN WITNESS WHEREOF**"):
            elements.append(("witness", md_to_rl(block)))
            continue

        bold_match = re.match(r"^\*\*(.+?)\*\*$", block)
        if bold_match:
            elements.append(("heading", bold_match.group(1)))
            continue

        if re.match(r"^\d+\.\d+", block):
            elements.append(("section", md_to_rl(block)))
            continue

        elements.append(("body", md_to_rl(block)))

    return elements


def build_pdf(md_path, output_path):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1.25 * inch,
        rightMargin=1.25 * inch,
    )

    elements = parse_markdown(md_path)
    story = []

    for kind, content in elements:
        if kind == "title":
            story.append(Paragraph(f"<b>{content}</b>", style_title))
            story.append(Spacer(1, 12))
        elif kind == "heading":
            if re.match(r"\d+\.", content):
                content = re.sub(r"^(\d+\.)\s*", r"\1&nbsp;&nbsp;&nbsp;&nbsp;", content)
            story.append(Paragraph(f"<b>{content}</b>", style_heading))
        elif kind == "recital":
            content = re.sub(r"^([A-Z]\.)\s*", r"\1&nbsp;&nbsp;&nbsp;&nbsp;", content)
            story.append(Paragraph(content, style_recital))
        elif kind == "section":
            content = re.sub(r"^(\d+\.\d{2})\s*", r"\1&nbsp;&nbsp;", content)
            content = re.sub(r"^(\d+\.\d)\s+", r"\1&nbsp;&nbsp;&nbsp;&nbsp;", content)
            story.append(Paragraph(content, style_section))
        elif kind == "body":
            story.append(Paragraph(content, style_body))
        elif kind == "indent":
            story.append(Paragraph(content, style_body_indent))
        elif kind == "witness":
            story.append(Spacer(1, 16))
            story.append(Paragraph(content, style_body))
        elif kind == "signatures":
            story.append(Spacer(1, 36))
            names = [n.strip() for n in content.split("|")]
            if len(names) == 2:
                sig_data = [
                    [
                        Paragraph(f"<b>{names[0]}</b>", style_sig),
                        Paragraph(f"<b>{names[1]}</b>", style_sig),
                    ],
                    [Paragraph("", style_sig), Paragraph("", style_sig)],
                    [
                        Paragraph("Signature: _________________________", style_sig),
                        Paragraph("Signature: _________________________", style_sig),
                    ],
                    [Paragraph("", style_sig), Paragraph("", style_sig)],
                    [
                        Paragraph("Date: ______________________________", style_sig),
                        Paragraph("Date: ______________________________", style_sig),
                    ],
                ]
                col_width = (letter[0] - 2.5 * inch) / 2
                sig_table = Table(sig_data, colWidths=[col_width, col_width])
                sig_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]))
                story.append(sig_table)

    doc.build(story)
    print(f"wrote {os.path.abspath(output_path)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown", help="annotated markdown source")
    ap.add_argument("output", nargs="?", help="output PDF (default: alongside source)")
    args = ap.parse_args()
    md = args.markdown
    out = args.output or os.path.splitext(md)[0] + ".pdf"
    build_pdf(md, out)


if __name__ == "__main__":
    sys.exit(main())
