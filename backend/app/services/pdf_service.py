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

logger = logging.getLogger(__name__)


class PDFService:
    """Service for PDF form generation and filling"""

    def __init__(self):
        """Initialize PDF service"""
        self.config: Optional[Dict[str, Any]] = None
        self.config_path = Path(__file__).parent.parent.parent / "config" / "pdf_form_mappings.json"
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
                    detail="PDF configuration not found"
                )

            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            logger.info(f"✅ PDF config loaded: {len(self.config.get('forms', {}))} forms")
            return self.config

        except json.JSONDecodeError as e:
            logger.error(f"Invalid PDF config JSON: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid PDF configuration"
            )
        except Exception as e:
            logger.error(f"Error loading PDF config: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to load PDF configuration"
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
                available.append({
                    "type": form_type,
                    "label": form_config.get("display_name", form_type),
                    "pdf_filename": form_config.get("pdf_filename", "")
                })

        logger.info(f"Available forms for absence {absence.id} (reason={absence.reason}): {len(available)}")
        return available

    def _format_webuntis_time(self, webuntis_time: int) -> str:
        """
        Convert WebUntis time format to HH:MM

        Args:
            webuntis_time: WebUntis time (e.g., 730 = 07:30, 815 = 08:15)

        Returns:
            Time string in format "HH:MM"
        """
        hours = webuntis_time // 100
        minutes = webuntis_time % 100
        return f"{hours:02d}:{minutes:02d}"

    def _get_time_from_period(self, timegrid: Dict[int, int], period: int, time_type: str) -> str:
        """
        Reverse lookup: Find time for a given period from timegrid

        Args:
            timegrid: Timegrid dict from WebUntis ({start_time -> period})
            period: Period number (1-16)
            time_type: "start" or "end"

        Returns:
            Time string in format "HH:MM"
        """
        # Reverse search: find start_time where period matches
        for start_time, p in timegrid.items():
            # Handle both int and str keys (JSONB conversion)
            try:
                p_int = int(p)
            except (ValueError, TypeError):
                continue

            if p_int == period:
                if time_type == "start":
                    return self._format_webuntis_time(start_time)
                else:
                    # Calculate end time: add 45 minutes (German school periods)
                    hours = start_time // 100
                    minutes = start_time % 100
                    end_minutes = minutes + 45
                    end_hours = hours
                    if end_minutes >= 60:
                        end_minutes -= 60
                        end_hours += 1
                    return f"{end_hours:02d}:{end_minutes:02d}"

        # Fallback to config if period not found in timegrid
        logger.warning(f"Period {period} nicht im WebUntis Timegrid gefunden, nutze Config Fallback")
        config = self._load_pdf_config()
        if time_type == "end":
            period_mapping = config.get("period_end_time_mapping", {})
            return period_mapping.get(str(period), "15:45")
        else:
            period_mapping = config.get("period_time_mapping", {})
            return period_mapping.get(str(period), "08:00")

    def _get_time_for_period_from_lessons_or_timegrid(
        self,
        lessons: List[AffectedLesson],
        period: int,
        time_type: str,
        timegrid: Dict[int, int]
    ) -> str:
        """
        Get time for a specific period, preferring WebUntis lesson data over timegrid reverse lookup

        Args:
            lessons: List of affected lessons
            period: Period number (1-16)
            time_type: "start" or "end"
            timegrid: Timegrid dict from WebUntis ({start_time -> period})

        Returns:
            Time string in format "HH:MM"
        """
        # Try to find a lesson with the given period that has time data
        for lesson in lessons:
            if lesson.period == period:
                if time_type == "start" and lesson.start_time:
                    return self._format_webuntis_time(lesson.start_time)
                elif time_type == "end" and lesson.end_time:
                    return self._format_webuntis_time(lesson.end_time)

        # Fallback to timegrid reverse lookup
        return self._get_time_from_period(timegrid, period, time_type)

    async def _build_template_context(
        self,
        absence: Absence,
        lessons: List[AffectedLesson],
        db: Session
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
            timegrid = await self.webuntis_service._load_timegrid(db, force_refresh=False)
            if not timegrid:
                logger.warning("⚠️ WebUntis Timegrid leer, nutze Config Fallback")
                timegrid = {}
        except Exception as e:
            logger.warning(f"⚠️ WebUntis Timegrid Exception: {e}, nutze Config Fallback")
            timegrid = {}

        # Extract time from absence periods (from StepOne)
        # Prefer WebUntis lesson times if available, then reverse-lookup from timegrid
        lessons_time_start = self._get_time_for_period_from_lessons_or_timegrid(
            lessons, absence.start_period, "start", timegrid
        )
        lessons_time_end = self._get_time_for_period_from_lessons_or_timegrid(
            lessons, absence.end_period, "end", timegrid
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

        context = {
            "absence": {
                "teacher": {
                    "full_name": full_name,
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": absence.teacher.email if absence.teacher else ""
                },
                "start_date": absence.start_date,
                "end_date": absence.end_date,
                "excursion_classes": absence.excursion_classes or "",
                "admin_notes": absence.admin_notes or ""
            },
            "lessons_time_start": lessons_time_start or "",
            "lessons_time_end": lessons_time_end or "",
            "lessons_subjects_combined": lessons_subjects_combined,
            "lessons_rooms_combined": lessons_rooms_combined,
            "config": defaults
        }

        return context

    def _process_template_variable(self, template: str, context: Dict[str, Any]) -> str:
        """
        Process a single template variable with filters

        Args:
            template: Template string (e.g., "{{ absence.start_date | format_date('%d.%m.%Y') }}")
            context: Context dictionary

        Returns:
            Processed value as string
        """
        if not template or not isinstance(template, str):
            return ""

        # Remove {{ }} and whitespace
        template = template.strip()
        if template.startswith("{{") and template.endswith("}}"):
            template = template[2:-2].strip()
        else:
            # Not a template variable, return as-is
            return template

        # Check for filters (e.g., "absence.start_date | format_date('%d.%m.%Y')")
        if "|" in template:
            var_path, filter_expr = template.split("|", 1)
            var_path = var_path.strip()
            filter_expr = filter_expr.strip()

            # Extract value
            value = self._get_nested_value(context, var_path)

            # Apply filter
            return self._apply_filter(value, filter_expr)
        else:
            # No filter, just extract value
            value = self._get_nested_value(context, template)
            return str(value) if value is not None else ""

    def _get_nested_value(self, context: Dict[str, Any], path: str) -> Any:
        """
        Get nested value from context using dot notation

        Args:
            context: Context dictionary
            path: Dot-separated path (e.g., "absence.teacher.full_name")

        Returns:
            Value or None if not found
        """
        keys = path.split(".")
        value = context

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                logger.warning(f"Path not found in context: {path}")
                return None

        return value

    def _apply_filter(self, value: Any, filter_expr: str) -> str:
        """
        Apply filter to value

        Args:
            value: Input value
            filter_expr: Filter expression (e.g., "format_date('%d.%m.%Y')")

        Returns:
            Filtered value as string
        """
        # Extract filter name and args
        match = re.match(r"(\w+)\((.*?)\)", filter_expr)
        if not match:
            logger.warning(f"Invalid filter expression: {filter_expr}")
            return str(value) if value is not None else ""

        filter_name = match.group(1)
        filter_args = match.group(2).strip("'\"")

        # Apply filter
        if filter_name == "format_date":
            if isinstance(value, datetime):
                return value.strftime(filter_args)
            else:
                logger.warning(f"format_date filter requires datetime, got {type(value)}")
                return str(value) if value is not None else ""
        else:
            logger.warning(f"Unknown filter: {filter_name}")
            return str(value) if value is not None else ""

    def _process_field_mappings(
        self,
        field_mappings: Dict[str, str],
        context: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Process all field mappings with template variables

        Args:
            field_mappings: Dict of PDF field name -> template variable
            context: Context dictionary

        Returns:
            Dict of PDF field name -> filled value
        """
        filled_fields = {}

        for pdf_field_name, template in field_mappings.items():
            # Skip comment fields (start with _)
            if pdf_field_name.startswith("_"):
                continue

            # Process template variable
            value = self._process_template_variable(template, context)
            filled_fields[pdf_field_name] = value

        return filled_fields

    async def generate_filled_pdf(
        self,
        absence: Absence,
        form_type: str,
        db: Session
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
                detail=f"Form type '{form_type}' not found"
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
                detail=f"PDF template '{pdf_filename}' not found"
            )

        # Get affected lessons
        lessons = absence.affected_lessons or []

        # Build template context
        context = await self._build_template_context(absence, lessons, db)

        # Process field mappings
        filled_fields = self._process_field_mappings(field_mappings, context)

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
                detail=f"PDF generation failed: {str(e)}"
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
                text = text.decode('utf-8')
            except UnicodeDecodeError:
                text = text.decode('latin-1', errors='replace')

        # Ensure it's a string
        if not isinstance(text, str):
            text = str(text)

        # Try to handle the encoding issue by ensuring proper UTF-8
        # The issue is that PyPDF2 might be double-encoding strings
        try:
            # Try to encode as Latin-1 to see if it's compatible
            text.encode('latin-1')
            # If it works, return as-is (it's Latin-1 compatible)
            return text
        except UnicodeEncodeError:
            # Contains characters not in Latin-1, keep as UTF-8 string
            # PyPDF2 3.0.1 should handle this correctly
            logger.debug(f"Text contains non-Latin-1 characters: {text}")
            return text

    def _merge_fdf_with_pdf(self, pdf_path: Path, filled_fields: Dict[str, str]) -> bytes:
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
                detail="PDF processing libraries not installed"
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
                writer.update_page_form_field_values(
                    page,
                    fixed_fields
                )
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
