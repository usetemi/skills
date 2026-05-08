#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf"]
# ///
"""Render every page of a PDF to PNG for visual verification.

Two-mode operation based on what was filled:

  --static     pdftoppm @ 220 dpi (fast, no appearance-stream regen)
               Use for: flat overlays, markdown→PDF, decrypted-only changes

  --acroform   Chrome via Playwright (regenerates /NeedAppearances streams)
               Use for: AcroForm /V fills where pdftoppm shows blank

Renderer escalation ladder (when static blank but data audit passes):
  1. Try --static → if blank, escalate
  2. Try --acroform (Playwright/Chrome) → matches Adobe rendering
  3. Open in Adobe Reader manually → ground truth

Usage:
    uv run verify_render.py <file.pdf>                          # static
    uv run verify_render.py <file.pdf> --acroform               # Playwright
    uv run verify_render.py <file.pdf> --out /tmp/render        # specify dir
    uv run verify_render.py <file.pdf> --dpi 300                # higher res
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def render_static(pdf, out_dir, dpi):
    if not shutil.which("pdftoppm"):
        print("ERROR: pdftoppm not found. Install poppler-utils.", file=sys.stderr)
        sys.exit(2)
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, os.path.splitext(os.path.basename(pdf))[0])
    subprocess.check_call(["pdftoppm", "-r", str(dpi), "-png", pdf, base])
    pngs = sorted(f for f in os.listdir(out_dir) if f.endswith(".png"))
    print(f"wrote {len(pngs)} PNGs to {out_dir}/")
    for p in pngs:
        print(f"  {p}")
    return pngs


def render_acroform(pdf, out_dir, dpi):
    """Render via Playwright + Chrome, which honors /NeedAppearances."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "ERROR: Playwright not installed. Run:\n"
            "  uv pip install playwright\n"
            "  playwright install chromium\n"
            "OR use --static then open in Adobe manually.",
            file=sys.stderr,
        )
        sys.exit(2)

    os.makedirs(out_dir, exist_ok=True)
    abs_pdf = os.path.abspath(pdf)
    base = os.path.splitext(os.path.basename(pdf))[0]

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            viewport={"width": 1200, "height": 1600},
            device_scale_factor=dpi / 96,
        )
        page = context.new_page()
        page.goto(f"file://{abs_pdf}")
        # Chrome's PDF viewer takes a moment to render
        page.wait_for_timeout(2000)
        png_path = os.path.join(out_dir, f"{base}.png")
        page.screenshot(path=png_path, full_page=True)
        browser.close()

    print(f"wrote {png_path}")
    print()
    print("NOTE: Chrome's PDF viewer renders one continuous page in screenshot.")
    print("      For per-page output, use --static and open in Adobe to verify")
    print("      AcroForm field rendering manually.")
    return [png_path]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="PDF to render")
    ap.add_argument("--out", default=None, help="output dir (default: tempdir)")
    ap.add_argument("--dpi", type=int, default=220, help="render DPI (default 220)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument(
        "--static",
        action="store_true",
        help="pdftoppm static raster (default; for overlays/generated)",
    )
    g.add_argument(
        "--acroform",
        action="store_true",
        help="Playwright/Chrome (for AcroForm /V fills)",
    )
    args = ap.parse_args()

    out_dir = args.out or tempfile.mkdtemp(prefix="pdf_verify_")

    if args.acroform:
        render_acroform(args.pdf, out_dir, args.dpi)
    else:
        render_static(args.pdf, out_dir, args.dpi)

    print()
    print("Read every PNG. Coordinate collisions and field-mapping errors are")
    print("silent in code, obvious in render. Build the audit table:")
    print("  Field | Type | Expected | Actual | ✓/✗")


if __name__ == "__main__":
    sys.exit(main())
