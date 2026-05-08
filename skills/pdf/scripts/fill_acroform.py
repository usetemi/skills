#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "pycryptodome"]
# ///
"""Fill an AcroForm PDF via per-page field updates. Use when inspect_pdf.py
reports acroform_fields > 0.

Pattern:
  1. Re-clone from the original template every fill (don't iterate on saves)
  2. /NeedAppearances=True so Chrome/Adobe regenerate appearance streams
  3. Per-page filling — never document-wide (field names like "Document Title 1"
     repeat across pages)
  4. Skip /Sig signature widgets — filling them corrupts
  5. For /Ch comboboxes, set /I (index into /Opt) too — string alone silently no-ops

Usage (template — copy and edit FIELDS_BY_PAGE for your form):
    uv run fill_acroform.py <template.pdf> <output.pdf>
"""
import argparse
import sys

import pypdf
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    NameObject,
    NumberObject,
    TextStringObject,
)


# ---- EDIT THIS BLOCK PER FORM ----
# Map page index (0-based) → {field_name: value}
# Example below is illustrative; replace with your form's fields.
FIELDS_BY_PAGE = {
    0: {
        # text fields
        "Clinic Name": "EXAMPLE",
        "Date": "05/08/2026",
    },
    # 1: { "f2_01": "EXAMPLE", ... },  # multi-page header carry-forward
    # 2: { "f3_01": "EXAMPLE", ... },
}

# Combobox values — set both string and selection index
# {page_index: {field_name: (value_string, opt_index)}}
COMBOBOX_BY_PAGE = {
    # 0: {"State": ("TX", 43)},
}

# Checkbox values — name → "/Yes" or "/Off" (or per-button on-state)
CHECKBOX_BY_PAGE = {
    # 0: {"Box A": "/Yes"},
}

# Field names to leave blank intentionally (signatures, internal-only fields)
SKIP_FIELDS = {
    "Signature",
    "Signature17_es_:signer:signature",
    "Signature_es_:signer:signature",
    # Internal pharmacy/agency fields
    "Account created by",
    "Verified By Pharmacist",
    "Notes",
}
# ---- END EDIT BLOCK ----


def fill(template, output):
    reader = pypdf.PdfReader(template)
    if reader.is_encrypted:
        reader.decrypt("")
    writer = pypdf.PdfWriter(clone_from=reader)

    # /AcroForm in pypdf >=4 returns IndirectObject; resolve before mutation
    acroform = writer._root_object.get("/AcroForm")
    if acroform is None:
        print("ERROR: no /AcroForm. Use fill_overlay.py for flat PDFs.", file=sys.stderr)
        sys.exit(2)
    if hasattr(acroform, "get_object"):
        acroform = acroform.get_object()
    acroform[NameObject("/NeedAppearances")] = BooleanObject(True)

    # Fill text fields per-page (avoids document-wide name collisions)
    for page_idx, fields in FIELDS_BY_PAGE.items():
        # Filter out skip fields and any field types that need special handling
        safe_fields = {k: v for k, v in fields.items() if k not in SKIP_FIELDS}
        if safe_fields:
            writer.update_page_form_field_values(writer.pages[page_idx], safe_fields)

    # Comboboxes: set /V and /I both. Strip /AP to force regeneration.
    for page_idx, combo_fields in COMBOBOX_BY_PAGE.items():
        page = writer.pages[page_idx]
        for annot_ref in page.get("/Annots") or []:
            annot = annot_ref.get_object()
            fname = str(annot.get("/T") or "")
            if fname in combo_fields:
                value, opt_idx = combo_fields[fname]
                annot[NameObject("/V")] = TextStringObject(value)
                annot[NameObject("/I")] = ArrayObject([NumberObject(opt_idx)])
                if "/AP" in annot:
                    del annot["/AP"]

    # Checkboxes: write /V as the on-state name
    for page_idx, check_fields in CHECKBOX_BY_PAGE.items():
        writer.update_page_form_field_values(writer.pages[page_idx], check_fields)

    with open(output, "wb") as f:
        writer.write(f)

    # Verify by re-reading
    verify = pypdf.PdfReader(output)
    populated = sum(1 for v in (verify.get_fields() or {}).values() if v.get("/V"))
    print(f"wrote {output}")
    print(f"populated /V in {populated} fields")
    print()
    print("NEXT: render with scripts/verify_render.py and walk the audit table.")
    print("NOTE: pdftoppm does NOT honor /NeedAppearances. Use Chrome via")
    print("      Playwright OR open in Adobe to verify visual rendering.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("template", help="path to source PDF (will not be modified)")
    ap.add_argument("output", help="path to filled output PDF")
    args = ap.parse_args()
    fill(args.template, args.output)


if __name__ == "__main__":
    sys.exit(main())
