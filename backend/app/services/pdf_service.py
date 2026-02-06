"""
PDF Service
Business logic for PDF form generation and filling
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.models import Absence, AffectedLesson
from app.services.template_service import template_service
from app.utils.time_format_utils import (
    format_webuntis_time,
    get_time_from_period,
    get_time_for_period,
)

logger = logging.getLogger(__name__)


class PDFService:
    """Service for PDF form generation and filling"""

    def __init__(self):
        """Initialize PDF service"""
        self.config: Optional[Dict[str, Any]] = None
        self.config_path = (
            Path(__file__).parent.parent.parent / "config" / "pdf_form_mappings.json"
        )
        self.pdf_dir = Path(__file__).parent.parent.parent / "assets"

        # Import here to avoid circular imports
        from app.services.webuntis_service import WebUntisService

        self.webuntis_service = WebUntisService()

    def _load_pdf_config(self) -> Dict[str, Any]:
        """
        Load PDF configuration from JSON file

        Returns:
            Configuration dictionary

        Raises:
            HTTPException: If config file not found or invalid
        """
        if self.config is not None:
            return self.config

        try:
            if not self.config_path.exists():
                logger.error(f"PDF config not found: {self.config_path}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="PDF configuration not found",
                )

            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            logger.info(
                f"✅ PDF config loaded: {len(self.config.get('forms', {}))} forms"
            )
            return self.config

        except json.JSONDecodeError as e:
            logger.error(f"Invalid PDF config JSON: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid PDF configuration",
            )
        except Exception as e:
            logger.error(f"Error loading PDF config: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load PDF configuration",
            )

    def get_available_forms(self, absence: Absence) -> List[Dict[str, str]]:
        """
        Get available PDF forms for an absence based on reason

        Args:
            absence: Absence object

        Returns:
            List of form info dicts: [{"type": "excursion_form", "label": "...", "pdf_filename": "1211.pdf"}]
        """
        config = self._load_pdf_config()
        forms = config.get("forms", {})
        available = []

        for form_type, form_config in forms.items():
            applicable_reasons = form_config.get("applicable_reasons", [])
            if absence.reason in applicable_reasons:
                available.append(
                    {
                        "type": form_type,
                        "label": form_config.get("display_name", form_type),
                        "pdf_filename": form_config.get("pdf_filename", ""),
                    }
                )

        logger.info(
            f"Available forms for absence {absence.id} (reason={absence.reason}): {len(available)}"
        )
        return available

    async def _build_template_context(
        self, absence: Absence, lessons: List[AffectedLesson], db: Session
    ) -> Dict[str, Any]:
        """
        Build context dictionary for template variable substitution

        Args:
            absence: Absence object
            lessons: List of affected lessons

        Returns:
            Context dictionary with nested structure
        """
        config = self._load_pdf_config()
        defaults = config.get("defaults", {})

        # Get timegrid from WebUntis (cached)
        try:
            timegrid = await self.webuntis_service._load_timegrid(
                db, force_refresh=False
            )
            if not timegrid:
                logger.warning("⚠️ WebUntis Timegrid leer, nutze Config Fallback")
                timegrid = {}
        except Exception as e:
            logger.warning(
                f"⚠️ WebUntis Timegrid Exception: {e}, nutze Config Fallback"
            )
            timegrid = {}

        # Extract time from absence periods (from StepOne)
        # Prefer WebUntis lesson times if available, then reverse-lookup from timegrid
        lessons_time_start = get_time_for_period(
            lessons, absence.start_period, "start", timegrid, self.config_path
        )
        lessons_time_end = get_time_for_period(
            lessons, absence.end_period, "end", timegrid, self.config_path
        )

        # Combine subjects and rooms
        subjects = list(set([l.subject for l in lessons if l.subject]))
        rooms = list(set([l.room for l in lessons if l.room]))
        lessons_subjects_combined = ", ".join(subjects) if subjects else ""
        lessons_rooms_combined = ", ".join(rooms) if rooms else ""

        # Get name data - prefer first_name/last_name from WordPress, fallback to parsing full_name
        full_name = absence.teacher.full_name if absence.teacher else ""
        first_name = ""
        last_name = ""

        # Check if we have first_name and last_name from WordPress user meta
        if absence.teacher and absence.teacher.first_name:
            first_name = absence.teacher.first_name.capitalize()
        if absence.teacher and absence.teacher.last_name:
            last_name = absence.teacher.last_name.capitalize()

        # Fallback: Parse from full_name if first/last name not available
        if not first_name and not last_name and full_name:
            parts = full_name.split(maxsplit=1)
            if len(parts) == 2:
                first_name = parts[0].capitalize()
                last_name = parts[1].capitalize()
            elif len(parts) == 1:
                last_name = parts[0].capitalize()  # If only one name, use as last_name

        # Calculate duration in days (inclusive)
        duration_days = (absence.end_date - absence.start_date).days + 1

        context = {
            "absence": {
                "teacher": {
                    "full_name": full_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": absence.teacher.email if absence.teacher else "",
                },
                "start_date": absence.start_date,
                "end_date": absence.end_date,
                "duration_days": duration_days,
                "excursion_classes": absence.excursion_classes or "",
                "admin_notes": absence.admin_notes or "",
            },
            "lessons_time_start": lessons_time_start or "",
            "lessons_time_end": lessons_time_end or "",
            "lessons_subjects_combined": lessons_subjects_combined,
            "lessons_rooms_combined": lessons_rooms_combined,
            "config": defaults,
        }

        return context

    async def generate_filled_pdf(
        self, absence: Absence, form_type: str, db: Session
    ) -> bytes:
        """
        Generate filled PDF form

        Args:
            absence: Absence object
            form_type: Form type identifier (e.g., "excursion_form")
            db: Database session

        Returns:
            PDF bytes

        Raises:
            HTTPException: If form not found or generation fails
        """
        logger.info(f"📄 Generating PDF form '{form_type}' for absence {absence.id}")

        # Load config
        config = self._load_pdf_config()
        forms = config.get("forms", {})

        if form_type not in forms:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Form type '{form_type}' not found",
            )

        form_config = forms[form_type]
        pdf_filename = form_config.get("pdf_filename")
        field_mappings = form_config.get("field_mappings", {})

        # Check if PDF file exists
        pdf_path = self.pdf_dir / pdf_filename
        if not pdf_path.exists():
            logger.error(f"PDF template not found: {pdf_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"PDF template '{pdf_filename}' not found",
            )

        # Get affected lessons
        lessons = absence.affected_lessons or []

        # Build template context
        context = await self._build_template_context(absence, lessons, db)

        # Process field mappings
        filled_fields = template_service.process_field_mappings(field_mappings, context)

        logger.info(f"Processed {len(filled_fields)} fields for form '{form_type}'")

        # Generate FDF and merge with PDF
        try:
            pdf_bytes = self._merge_fdf_with_pdf(pdf_path, filled_fields)
            logger.info(f"✅ Generated PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"PDF generation failed: {str(e)}",
            )

    def _fix_pdf_encoding(self, text: str) -> str:
        """
        Fix encoding issues for PDF form fields

        PDF forms often expect Latin-1 (ISO-8859-1) encoding.
        We try to encode as Latin-1, and if that fails (for characters not in Latin-1),
        we use Unicode normalization.

        Args:
            text: Input text

        Returns:
            Properly encoded text string for PDF forms
        """
        if not text:
            return text

        # If it's bytes, decode first
        if isinstance(text, bytes):
            try:
                text = text.decode("utf-8")
            except UnicodeDecodeError:
                text = text.decode("latin-1", errors="replace")

        # Ensure it's a string
        if not isinstance(text, str):
            text = str(text)

        # Try to handle the encoding issue by ensuring proper UTF-8
        # The issue is that PyPDF2 might be double-encoding strings
        try:
            # Try to encode as Latin-1 to see if it's compatible
            text.encode("latin-1")
            # If it works, return as-is (it's Latin-1 compatible)
            return text
        except UnicodeEncodeError:
            # Contains characters not in Latin-1, keep as UTF-8 string
            # PyPDF2 3.0.1 should handle this correctly
            logger.debug(f"Text contains non-Latin-1 characters: {text}")
            return text

    def _merge_fdf_with_pdf(
        self, pdf_path: Path, filled_fields: Dict[str, str]
    ) -> bytes:
        """
        Fill PDF form fields with data

        Args:
            pdf_path: Path to PDF template
            filled_fields: Dict of field name -> value

        Returns:
            Filled PDF bytes
        """
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as e:
            logger.error(f"PDF libraries not available: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF processing libraries not installed",
            )

        # Read original PDF
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()

        # Clone the entire document including AcroForm (form field definitions)
        writer.clone_reader_document_root(reader)

        # pypdf 5.x handles string encoding automatically - just pass plain strings
        # The library will choose the appropriate encoding (PDFDocEncoding or UTF-16BE)
        logger.debug(f"Filling {len(filled_fields)} fields with values")
        for key, value in filled_fields.items():
            if isinstance(value, str):
                logger.debug(f"Field '{key}' = '{value}'")

        # Use filled_fields directly - pypdf handles encoding
        fixed_fields = filled_fields

        # Update form fields for each page
        for page_num, page in enumerate(writer.pages):
            try:
                writer.update_page_form_field_values(page, fixed_fields)
                logger.debug(f"Updated form fields on page {page_num + 1}")
            except Exception as e:
                logger.warning(f"Could not update fields on page {page_num + 1}: {e}")

        # Write to bytes
        output = BytesIO()
        writer.write(output)
        pdf_bytes = output.getvalue()

        return pdf_bytes


# Singleton instance
pdf_service = PDFService()
