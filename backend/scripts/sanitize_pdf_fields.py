#!/usr/bin/env python3
"""
Sanitize PDF form fields by making all field names unique

This script detects duplicate field names in a PDF form and renames them
to be unique by appending page numbers (e.g., "Text1" -> "Text1_p1", "Text1_p2").
This is necessary because PDF forms with duplicate field names will fill all
instances with the same value, which is usually not the desired behavior.

Usage:
    python sanitize_pdf_fields.py <input_pdf> [output_pdf]

Example:
    python sanitize_pdf_fields.py ../assets/1201.pdf ../assets/1201-sanitized.pdf

Author: Claude Sonnet 4.5
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List


def analyze_pdf_fields(pdf_path: str) -> Dict[str, List[int]]:
    """
    Analyze PDF and find duplicate field names

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary mapping field names to list of page numbers where they appear
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        print("❌ Error: pypdf is not installed")
        print("Please install it: pip install pypdf")
        sys.exit(1)

    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    reader = PdfReader(pdf_path)
    field_pages = defaultdict(list)

    # Iterate through all pages and their annotations
    for page_num, page in enumerate(reader.pages, start=1):
        if "/Annots" in page:
            annots = page["/Annots"]
            if annots:
                for annot_ref in annots:
                    annot = annot_ref.get_object()
                    # Check if this is a form field (has /T key for field name)
                    if "/T" in annot:
                        field_name = str(annot["/T"])
                        field_pages[field_name].append(page_num)

    return field_pages


def sanitize_pdf_fields(input_path: str, output_path: str):
    """
    Sanitize PDF by renaming duplicate field names

    Args:
        input_path: Path to input PDF
        output_path: Path to output sanitized PDF
    """
    try:
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import TextStringObject
    except ImportError:
        print("❌ Error: pypdf is not installed")
        print("Please install it: pip install pypdf")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"Sanitizing PDF: {Path(input_path).name}")
    print(f"{'='*70}\n")

    # First, analyze to find duplicates
    print("🔍 Analyzing PDF fields...")
    field_pages = analyze_pdf_fields(input_path)

    duplicates = {name: pages for name, pages in field_pages.items() if len(pages) > 1}

    if not duplicates:
        print("✅ No duplicate field names found!")
        print("   All field names are already unique.")
        print(f"\n   Total fields: {len(field_pages)}")
        return

    print(f"⚠️  Found {len(duplicates)} duplicate field names:\n")
    for field_name, pages in sorted(duplicates.items()):
        print(f"   '{field_name}' appears on pages: {', '.join(map(str, pages))}")

    print(f"\n📝 Renaming {len(duplicates)} fields to make them unique...")

    # Read PDF and create writer
    reader = PdfReader(input_path)
    writer = PdfWriter()

    # Clone the document
    writer.clone_reader_document_root(reader)

    # Track renames for summary
    renames = []

    # Rename duplicate fields on each page
    for page_num, page in enumerate(writer.pages, start=1):
        if "/Annots" in page:
            annots = page["/Annots"]
            if annots:
                for annot_ref in annots:
                    annot = annot_ref.get_object()
                    if "/T" in annot:
                        field_name = str(annot["/T"])

                        # If this field has duplicates, rename it
                        if field_name in duplicates:
                            new_name = f"{field_name}_p{page_num}"
                            annot.update({"/T": TextStringObject(new_name)})
                            renames.append((field_name, new_name, page_num))
                            print(
                                f"   Renamed: '{field_name}' → '{new_name}' (page {page_num})"
                            )

    # Write sanitized PDF
    print(f"\n💾 Writing sanitized PDF to: {output_path}")
    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"\n{'='*70}")
    print("✅ Sanitization Complete!")
    print(f"{'='*70}\n")

    print(f"Summary:")
    print(f"  - Original fields: {len(field_pages)}")
    print(f"  - Duplicate field names: {len(duplicates)}")
    print(f"  - Fields renamed: {len(renames)}")
    print(f"  - Output: {output_path}")

    print(f"\nNext steps:")
    print(f"  1. Run extract_pdf_fields.py on the sanitized PDF:")
    print(f"     python extract_pdf_fields.py {output_path}")
    print(f"  2. Update pdf_form_mappings.json with the new field names")
    print(f"  3. Use the sanitized PDF as your template")
    print()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python sanitize_pdf_fields.py <input_pdf> [output_pdf]")
        print()
        print("Examples:")
        print("  python sanitize_pdf_fields.py ../assets/1201.pdf")
        print(
            "  python sanitize_pdf_fields.py ../assets/1201.pdf ../assets/1201-sanitized.pdf"
        )
        print()
        print("If output_pdf is not specified, it defaults to <input>-sanitized.pdf")
        sys.exit(1)

    input_path = sys.argv[1]

    # Default output path: add -sanitized suffix
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        input_file = Path(input_path)
        output_path = str(
            input_file.parent / f"{input_file.stem}-sanitized{input_file.suffix}"
        )

    try:
        sanitize_pdf_fields(input_path, output_path)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
