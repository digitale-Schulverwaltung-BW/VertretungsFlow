#!/usr/bin/env python3
"""
Extract form field names from PDF files

This script extracts all form fields from a PDF file and displays
their names, types, and current values. This is essential for
creating the field mapping configuration for the PDF form filling feature.

Usage:
    python extract_pdf_fields.py <pdf_file>

Example:
    python extract_pdf_fields.py ../wordpress-plugin/assets/1211.pdf

Author: Claude Sonnet 4.5
"""

import sys
from pathlib import Path
from typing import Dict, Any


def extract_pdf_fields(pdf_path: str) -> Dict[str, Any]:
    """
    Extract all form field names from PDF

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Dictionary with field names as keys and field info as values

    Raises:
        FileNotFoundError: If PDF file doesn't exist
        ImportError: If PyPDF2 is not installed
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

    fields = {}
    pdf_fields = reader.get_fields()
    if pdf_fields:
        for field_name, field_obj in pdf_fields.items():
            # Extract field type
            field_type = field_obj.get("/FT", "Unknown")
            if field_type:
                # Decode PDF name objects (e.g., /Tx -> Text field)
                type_map = {
                    "/Tx": "Text",
                    "/Btn": "Button/Checkbox",
                    "/Ch": "Choice/Dropdown",
                    "/Sig": "Signature",
                }
                field_type = type_map.get(str(field_type), str(field_type))

            # Extract current value
            field_value = field_obj.get("/V", "")
            if hasattr(field_value, "get_object"):
                field_value = field_value.get_object()

            # Extract flags (for additional info)
            flags = field_obj.get("/Ff", 0)

            # Determine if field is required (bit 1 in flags)
            is_required = bool(flags & 2)

            # Determine if field is read-only (bit 0 in flags)
            is_readonly = bool(flags & 1)

            fields[field_name] = {
                "type": field_type,
                "value": str(field_value) if field_value else "",
                "flags": flags,
                "required": is_required,
                "readonly": is_readonly,
            }

    return fields


def print_fields(fields: Dict[str, Any], pdf_path: str):
    """Pretty-print extracted fields"""
    print(f"\n{'='*70}")
    print(f"PDF Form Fields: {Path(pdf_path).name}")
    print(f"{'='*70}\n")

    if not fields:
        print("❌ No form fields found in this PDF")
        print("\nPossible reasons:")
        print("  - PDF is not a fillable form")
        print("  - PDF uses non-standard form fields")
        print("  - PDF fields are flattened (merged with content)")
        return

    print(f"✅ Found {len(fields)} form fields:\n")

    # Sort fields alphabetically for easier reading
    for field_name in sorted(fields.keys()):
        info = fields[field_name]

        print(f"📄 Field: {field_name}")
        print(f"   Type:     {info['type']}")

        if info["value"]:
            print(f"   Value:    {info['value']}")
        else:
            print(f"   Value:    (empty)")

        attributes = []
        if info["required"]:
            attributes.append("REQUIRED")
        if info["readonly"]:
            attributes.append("READ-ONLY")

        if attributes:
            print(f"   Attrs:    {', '.join(attributes)}")

        print(f"   Flags:    {info['flags']} (binary: {bin(info['flags'])})")
        print()


def generate_config_template(fields: Dict[str, Any], pdf_filename: str):
    """Generate a template config snippet for the extracted fields"""
    print(f"\n{'='*70}")
    print("Generated Config Template (JSON)")
    print(f"{'='*70}\n")

    print(f'"field_mappings": {{')

    for i, field_name in enumerate(sorted(fields.keys())):
        comma = "," if i < len(fields) - 1 else ""
        print(f'  "{field_name}": "{{{{ absence.FIELD_NAME_HERE }}}}{comma}"')

    print(f"}}\n")

    print("Available template variables:")
    print("  {{ absence.teacher.full_name }}")
    print("  {{ absence.teacher.email }}")
    print("  {{ absence.start_date | format_date('%d.%m.%Y') }}")
    print("  {{ absence.end_date | format_date('%d.%m.%Y') }}")
    print("  {{ absence.excursion_classes }}")
    print("  {{ absence.admin_notes }}")
    print("  {{ lessons_time_start }}")
    print("  {{ lessons_time_end }}")
    print("  {{ lessons_subjects_combined }}")
    print("  {{ lessons_rooms_combined }}")
    print()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_fields.py <pdf_file>")
        print()
        print("Examples:")
        print("  python extract_pdf_fields.py ../wordpress-plugin/assets/1211.pdf")
        print("  python extract_pdf_fields.py ../wordpress-plugin/assets/1201.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]

    try:
        fields = extract_pdf_fields(pdf_path)
        print_fields(fields, pdf_path)

        if fields:
            generate_config_template(fields, Path(pdf_path).name)

            # Output summary
            print(f"{'='*70}")
            print(f"Summary: {len(fields)} fields extracted from {Path(pdf_path).name}")
            print(f"{'='*70}\n")

            print("Next steps:")
            print("  1. Review the field names above")
            print("  2. Map them to absence data in pdf_form_mappings.json")
            print("  3. Test with a real absence to verify mappings")
            print()

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
