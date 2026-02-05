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
        self.pdf_dir = Path(__file__).parent.parent.parent.parent / "wordpress-plugin" / "assets"

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

    def _extract_time_from_lessons(
        self,
        lessons: List[AffectedLesson],
        extract_type: str = "start"
    ) -> Optional[str]:
        """
        Extract start or end time from lessons

        Args:
            lessons: List of affected lessons
            extract_type: "start" or "end"

        Returns:
            Time string in format "HH:MM" or None
        """
        if not lessons:
            return None

        # Sort lessons by date and period
        sorted_lessons = sorted(lessons, key=lambda l: (l.date, l.period))

        if extract_type == "start":
            # Get earliest lesson's start time
            first_lesson = sorted_lessons[0]
            if first_lesson.start_time:
                return self._format_webuntis_time(first_lesson.start_time)
            else:
                # Fallback to period mapping
                return self._get_time_from_period_mapping(first_lesson.period, "start")
        else:
            # Get latest lesson's end time
            last_lesson = sorted_lessons[-1]
            if last_lesson.end_time:
                return self._format_webuntis_time(last_lesson.end_time)
            else:
                # Fallback to period mapping
                return self._get_time_from_period_mapping(last_lesson.period, "end")

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

    def _get_time_from_period_mapping(self, period: int, time_type: str = "start") -> str:
        """
        Get time from period mapping fallback

        Args:
            period: Period number (1-10)
            time_type: "start" or "end" (currently both use same mapping)

        Returns:
            Time string in format "HH:MM"
        """
        config = self._load_pdf_config()
        period_mapping = config.get("period_time_mapping", {})
        time_str = period_mapping.get(str(period), "08:00")
        return time_str

    def _build_template_context(
        self,
        absence: Absence,
        lessons: List[AffectedLesson]
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

        # Extract lesson-derived data
        lessons_time_start = self._extract_time_from_lessons(lessons, "start")
        lessons_time_end = self._extract_time_from_lessons(lessons, "end")

        # Combine subjects and rooms
        subjects = list(set([l.subject for l in lessons if l.subject]))
        rooms = list(set([l.room for l in lessons if l.room]))
        lessons_subjects_combined = ", ".join(subjects) if subjects else ""
        lessons_rooms_combined = ", ".join(rooms) if rooms else ""

        context = {
            "absence": {
                "teacher": {
                    "full_name": absence.teacher.full_name if absence.teacher else "",
                    "first_name": absence.teacher.first_name if absence.teacher else "",
                    "last_name": absence.teacher.last_name if absence.teacher else "",
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

    def generate_filled_pdf(
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
        context = self._build_template_context(absence, lessons)

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

    def _merge_fdf_with_pdf(self, pdf_path: Path, filled_fields: Dict[str, str]) -> bytes:
        """
        Merge FDF data with PDF template

        Args:
            pdf_path: Path to PDF template
            filled_fields: Dict of field name -> value

        Returns:
            Filled PDF bytes
        """
        try:
            from fdfgen import forge_fdf
            from PyPDF2 import PdfReader, PdfWriter
        except ImportError as e:
            logger.error(f"PDF libraries not available: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="PDF processing libraries not installed"
            )

        # Generate FDF
        fdf_data = forge_fdf("", filled_fields.items(), [], [], [])

        # Read original PDF
        reader = PdfReader(str(pdf_path))
        writer = PdfWriter()

        # Copy all pages
        for page in reader.pages:
            writer.add_page(page)

        # Update form fields
        if writer.get_fields():
            for field_name, field_value in filled_fields.items():
                try:
                    writer.update_page_form_field_values(
                        writer.pages[0],  # Assume form fields on first page (will update all pages)
                        {field_name: field_value}
                    )
                except Exception as e:
                    logger.warning(f"Could not fill field '{field_name}': {e}")

        # Write to bytes
        output = BytesIO()
        writer.write(output)
        pdf_bytes = output.getvalue()

        return pdf_bytes


# Singleton instance
pdf_service = PDFService()
