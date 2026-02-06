#!/usr/bin/env python3
"""
Fill PDF form fields with their own field names for debugging

This script fills each form field in a PDF with its own name,
making it easy to identify which field name corresponds to which
position in the PDF form.

Usage:
    python fill_pdf_with_field_names.py <input_pdf> <output_pdf>

Example:
    python fill_pdf_with_field_names.py ../assets/1211.pdf 1211_labeled.pdf
"""

import sys
from pathlib import Path
from io import BytesIO


def fill_pdf_with_field_names(input_pdf: str, output_pdf: str):
    """
    Fill PDF form fields with their own names

    Args:
        input_pdf: Path to input PDF
        output_pdf: Path to output PDF
    """
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("❌ Error: pypdf is not installed")
        print("Please install it: pip install pypdf")
        sys.exit(1)

    input_path = Path(input_pdf)
    if not input_path.exists():
        print(f"❌ Error: PDF file not found: {input_pdf}")
        sys.exit(1)

    print(f"📄 Reading PDF: {input_pdf}")
    reader = PdfReader(str(input_path))
    writer = PdfWriter()

    # Clone the entire document including AcroForm (form field definitions)
    writer.clone_reader_document_root(reader)

    # Get all form fields
    fields = reader.get_fields()
    if not fields:
        print("❌ No form fields found in this PDF")
        sys.exit(1)

    print(f"✅ Found {len(fields)} form fields")

    # Create a dict with field_name -> field_name as value
    field_values = {}
    for field_name in fields.keys():
        # Use the field name itself as the value
        field_values[field_name] = field_name

    print(f"📝 Filling {len(field_values)} fields with their names...")

    # Update form fields for each page
    for page_num, page in enumerate(writer.pages):
        try:
            writer.update_page_form_field_values(page, field_values)
            print(f"   ✓ Updated fields on page {page_num + 1}")
        except Exception as e:
            print(f"   ⚠ Warning: Could not update fields on page {page_num + 1}: {e}")

    # Write output
    print(f"💾 Writing output to: {output_pdf}")
    with open(output_pdf, "wb") as f:
        writer.write(f)

    output_size = Path(output_pdf).stat().st_size
    print(f"✅ Done! Generated {output_pdf} ({output_size} bytes)")
    print(f"\nNow you can open {output_pdf} to see which field name appears where!")


def main():
    """Main entry point"""
    if len(sys.argv) < 3:
        print("Usage: python fill_pdf_with_field_names.py <input_pdf> <output_pdf>")
        print()
        print("Examples:")
        print(
            "  python fill_pdf_with_field_names.py ../assets/1211.pdf 1211_labeled.pdf"
        )
        print(
            "  python fill_pdf_with_field_names.py ../assets/1201.pdf 1201_labeled.pdf"
        )
        sys.exit(1)

    input_pdf = sys.argv[1]
    output_pdf = sys.argv[2]

    try:
        fill_pdf_with_field_names(input_pdf, output_pdf)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
