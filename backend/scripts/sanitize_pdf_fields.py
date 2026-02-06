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


def _rename_fields_on_page(
    page, page_num: int, duplicates: Dict[str, List[int]]
) -> List[Tuple[str, str, int]]:
    """
    Rename duplicate fields on a single PDF page

    Args:
        page: PDF page object
        page_num: Page number (1-indexed)
        duplicates: Dict of duplicate field names

    Returns:
        List of (old_name, new_name, page_num) tuples
    """
    renames = []

    if "/Annots" not in page:
        return renames

    annots = page["/Annots"]
    if not annots:
        return renames

    for annot_ref in annots:
        annot = annot_ref.get_object()
        if "/T" not in annot:
            continue

        field_name = str(annot["/T"])
        if field_name not in duplicates:
            continue

        # Rename field
        from pypdf.generic import TextStringObject

        new_name = f"{field_name}_p{page_num}"
        annot.update({"/T": TextStringObject(new_name)})
        renames.append((field_name, new_name, page_num))
        print(f"   Renamed: '{field_name}' → '{new_name}' (page {page_num})")

    return renames


def _print_summary(
    field_pages: Dict, duplicates: Dict, renames: List, output_path: str
):
    """
    Print sanitization summary

    Args:
        field_pages: All field pages dict
        duplicates: Duplicate fields dict
        renames: List of renames performed
        output_path: Output file path
    """
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


def sanitize_pdf_fields(input_path: str, output_path: str):
    """
    Sanitize PDF by renaming duplicate field names

    Args:
        input_path: Path to input PDF
        output_path: Path to output sanitized PDF
    """
    # Import check
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("❌ Error: pypdf is not installed")
        print("Please install it: pip install pypdf")
        sys.exit(1)

    # Header
    print(f"\n{'='*70}")
    print(f"Sanitizing PDF: {Path(input_path).name}")
    print(f"{'='*70}\n")

    # Analyze for duplicates
    print("🔍 Analyzing PDF fields...")
    field_pages = analyze_pdf_fields(input_path)
    duplicates = {name: pages for name, pages in field_pages.items() if len(pages) > 1}

    # Early return if no duplicates
    if not duplicates:
        print("✅ No duplicate field names found!")
        print("   All field names are already unique.")
        print(f"\n   Total fields: {len(field_pages)}")
        return

    # Print duplicates found
    print(f"⚠️  Found {len(duplicates)} duplicate field names:\n")
    for field_name, pages in sorted(duplicates.items()):
        print(f"   '{field_name}' appears on pages: {', '.join(map(str, pages))}")

    print(f"\n📝 Renaming {len(duplicates)} fields to make them unique...")

    # Setup PDF writer
    reader = PdfReader(input_path)
    writer = PdfWriter()
    writer.clone_reader_document_root(reader)

    # Rename fields on each page
    all_renames = []
    for page_num, page in enumerate(writer.pages, start=1):
        renames = _rename_fields_on_page(page, page_num, duplicates)
        all_renames.extend(renames)

    # Write output
    print(f"\n💾 Writing sanitized PDF to: {output_path}")
    with open(output_path, "wb") as f:
        writer.write(f)

    # Print summary
    _print_summary(field_pages, duplicates, all_renames, output_path)


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
