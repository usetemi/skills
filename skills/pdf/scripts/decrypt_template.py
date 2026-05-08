#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pypdf", "pycryptodome"]
# ///
"""Decrypt an AES-encrypted government PDF (Cal Judicial Council, IRS, USCIS).

Most government forms ship encrypted with appearance streams that don't
regenerate on fill. Decrypt once into a templates/ directory and work from
the decrypted copy. Most use empty owner password.

Usage:
    uv run decrypt_template.py <encrypted.pdf> <decrypted.pdf>
    uv run decrypt_template.py <encrypted.pdf> <decrypted.pdf> --password 'foo'
"""
import argparse
import sys

import pypdf


def decrypt(src, dst, password=""):
    reader = pypdf.PdfReader(src)
    if not reader.is_encrypted:
        print(f"NOTE: {src} is not encrypted. Copying as-is.", file=sys.stderr)
    else:
        result = reader.decrypt(password)
        if result == 0:
            print(f"ERROR: decrypt failed (wrong password?)", file=sys.stderr)
            sys.exit(2)

    writer = pypdf.PdfWriter(clone_from=reader)
    with open(dst, "wb") as f:
        writer.write(f)
    print(f"wrote {dst}")
    print()
    print("NEXT: re-run scripts/inspect_pdf.py against the DECRYPTED file.")
    print("      Encryption can hide field counts. Decision tree resumes")
    print("      from the inspect output (AcroForm vs flat).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="encrypted PDF")
    ap.add_argument("output", help="decrypted output PDF")
    ap.add_argument("--password", default="", help="owner password (default empty)")
    args = ap.parse_args()
    decrypt(args.source, args.output, args.password)


if __name__ == "__main__":
    sys.exit(main())
