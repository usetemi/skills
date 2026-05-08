#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "pycryptodome"]
# ///
"""Inspect a PDF before filling/redlining. Run this FIRST, every time.

Prints:
  - encryption status (if encrypted, decrypt before continuing)
  - page count + per-page mediabox (don't assume letter)
  - AcroForm field count + per-page name/type/tooltip/rect/current-value
  - live widget annotations (overlaying onto these breaks in Adobe)
  - embedded fonts

Usage:
    uv run inspect_pdf.py <path.pdf>
    uv run inspect_pdf.py <path.pdf> --json    # machine-readable for piping
"""
import argparse
import json
import sys

import pypdf


def field_type(ft):
    return {
        "/Tx": "Tx (text)",
        "/Btn": "Btn (checkbox/radio/button)",
        "/Ch": "Ch (combobox/listbox)",
        "/Sig": "Sig (signature — NEVER fill)",
    }.get(ft, str(ft))


def inspect(path):
    reader = pypdf.PdfReader(path)
    out = {
        "path": path,
        "encrypted": reader.is_encrypted,
        "page_count": len(reader.pages),
        "pages": [],
        "acroform_field_count": 0,
        "fonts": [],
    }

    if reader.is_encrypted:
        # Try empty owner password (most government PDFs)
        try:
            reader.decrypt("")
            out["decrypt_attempt"] = "succeeded with empty password"
        except Exception as e:
            out["decrypt_attempt"] = f"failed: {e}"
            return out

    fields = reader.get_fields() or {}
    out["acroform_field_count"] = len(fields)

    # Per-page detail
    for i, page in enumerate(reader.pages):
        mb = page.mediabox
        page_info = {
            "index": i,
            "mediabox": [float(mb.left), float(mb.bottom),
                         float(mb.right), float(mb.top)],
            "size": [float(mb.width), float(mb.height)],
            "fields": [],
            "widget_annot_count": 0,
        }
        # Widget annotations on this page
        annots = page.get("/Annots") or []
        for annot_ref in annots:
            try:
                annot = annot_ref.get_object()
                if annot.get("/Subtype") == "/Widget":
                    page_info["widget_annot_count"] += 1
                    fname = annot.get("/T")
                    ft = annot.get("/FT")
                    if fname:
                        rect = annot.get("/Rect")
                        page_info["fields"].append({
                            "name": str(fname),
                            "type": field_type(ft) if ft else "unknown",
                            "tooltip": str(annot.get("/TU") or ""),
                            "rect": [float(r) for r in rect] if rect else None,
                            "current_value": str(annot.get("/V") or ""),
                            "options": [str(o) for o in (annot.get("/Opt") or [])],
                        })
            except Exception:
                continue
        out["pages"].append(page_info)

    # Embedded fonts (from page resources)
    seen_fonts = set()
    for page in reader.pages:
        res = page.get("/Resources")
        if res:
            fonts = res.get("/Font") if hasattr(res, "get") else None
            if fonts:
                try:
                    for fkey in fonts:
                        fobj = fonts[fkey].get_object() if hasattr(fonts[fkey], "get_object") else fonts[fkey]
                        bf = fobj.get("/BaseFont") if fobj else None
                        if bf:
                            seen_fonts.add(str(bf))
                except Exception:
                    pass
    out["fonts"] = sorted(seen_fonts)
    return out


def render_human(out):
    print(f"PDF: {out['path']}")
    print(f"  encrypted:           {out['encrypted']}")
    if out.get("decrypt_attempt"):
        print(f"  decrypt:             {out['decrypt_attempt']}")
    print(f"  pages:               {out['page_count']}")
    print(f"  acroform fields:     {out['acroform_field_count']}")
    print(f"  embedded fonts:      {', '.join(out['fonts']) or '(none)'}")
    print()
    for page in out["pages"]:
        i = page["index"]
        w, h = page["size"]
        # Heuristic page-size label
        if abs(w - 612) < 2 and abs(h - 792) < 2:
            label = "letter"
        elif abs(w - 595) < 2 and abs(h - 842) < 2:
            label = "A4"
        else:
            label = f"{w:.0f}×{h:.0f}"
        print(f"Page {i + 1} — {label} ({w:.1f} × {h:.1f} pts)")
        print(f"  widget annotations:  {page['widget_annot_count']}")
        if page["fields"]:
            print(f"  fields ({len(page['fields'])}):")
            for f in page["fields"]:
                opts = f" opts={f['options']}" if f["options"] else ""
                tt = f"  [{f['tooltip']}]" if f["tooltip"] else ""
                cv = f"  /V={f['current_value']!r}" if f["current_value"] else ""
                print(f"    - {f['name']!r:40} {f['type']:30}{tt}{cv}{opts}")
        print()

    # Decision hint
    print("─" * 60)
    if out["acroform_field_count"] > 0:
        print("→ AcroForm path: use scripts/fill_acroform.py")
    else:
        any_widgets = any(p["widget_annot_count"] > 0 for p in out["pages"])
        if any_widgets:
            print("→ Live widgets present despite zero filled fields. Inspect.")
        else:
            print("→ Flat PDF: use scripts/fill_overlay.py or scripts/render_redlines.py")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="path to PDF")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()
    out = inspect(args.pdf)
    if args.json:
        print(json.dumps(out, indent=2, default=str))
    else:
        render_human(out)


if __name__ == "__main__":
    sys.exit(main())
