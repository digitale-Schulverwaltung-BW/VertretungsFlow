"""
Unit Tests für PDFService

Getestet:
- _load_pdf_config() - JSON Config Loading mit Caching & Error Handling
- get_available_forms() - Formular-Filterung nach Abwesenheitsgrund
- _build_template_context() - Kontext-Aufbau (Name-Parsing, Dauer, Stunden)
- generate_filled_pdf() - Orchestrierung + Fehlerbehandlung
- _fix_pdf_encoding() - Encoding-Handling für PDF-Felder
"""

import json
import sys
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, mock_open

from fastapi import HTTPException

from app.services.pdf_service import PDFService


# ============================================================================
# Sample Config für Tests
# ============================================================================

SAMPLE_CONFIG = {
    "forms": {
        "excursion_form": {
            "display_name": "Exkursionsformular",
            "pdf_filename": "excursion.pdf",
            "applicable_reasons": ["excursion"],
            "field_mappings": {
                "TeacherName": "{{ absence.teacher.full_name }}",
                "_comment": "This is ignored",
            },
        },
        "sick_form": {
            "display_name": "Krankheitsformular",
            "pdf_filename": "sick.pdf",
            "applicable_reasons": ["sick", "personal"],
            "field_mappings": {},
        },
    },
    "defaults": {
        "school_name": "Testschule",
    },
}


# ============================================================================
# Helpers & Fixtures
# ============================================================================


@pytest.fixture
def service():
    """Fresh PDFService instance with config pre-loaded (no file I/O)"""
    svc = PDFService()
    svc.config = SAMPLE_CONFIG  # bypass file loading
    return svc


@pytest.fixture
def mock_absence():
    """Mock absence with teacher and lessons"""
    teacher = Mock()
    teacher.full_name = "Max Mustermann"
    teacher.first_name = None
    teacher.last_name = None
    teacher.email = "max@schule.de"

    absence = Mock()
    absence.id = 42
    absence.reason = "excursion"
    absence.start_date = datetime(2026, 2, 10)
    absence.end_date = datetime(2026, 2, 12)
    absence.start_period = 1
    absence.end_period = 4
    absence.excursion_classes = "5A, 5B"
    absence.admin_notes = ""
    absence.teacher = teacher
    absence.affected_lessons = []
    return absence


@pytest.fixture
def mock_db():
    return Mock()


# ============================================================================
# Test _load_pdf_config()
# ============================================================================


class TestLoadPdfConfig:
    """Test JSON config loading with caching and error handling"""

    def test_loads_config_from_file(self, tmp_path):
        """Test that config is loaded from JSON file"""
        config_file = tmp_path / "pdf_form_mappings.json"
        config_file.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")

        svc = PDFService()
        svc.config = None  # ensure fresh load
        svc.config_path = config_file

        result = svc._load_pdf_config()

        assert result["forms"]["excursion_form"]["display_name"] == "Exkursionsformular"
        assert "sick_form" in result["forms"]

    def test_returns_cached_config_on_second_call(self, tmp_path):
        """Test that config is only read once (caching works)"""
        config_file = tmp_path / "pdf_form_mappings.json"
        config_file.write_text(json.dumps(SAMPLE_CONFIG), encoding="utf-8")

        svc = PDFService()
        svc.config = None
        svc.config_path = config_file

        first = svc._load_pdf_config()
        # Modify the file after first load
        config_file.write_text(json.dumps({"forms": {}}), encoding="utf-8")
        second = svc._load_pdf_config()

        # Should return same cached object, not re-read
        assert first is second
        assert "excursion_form" in second["forms"]

    def test_raises_500_when_file_not_found(self, tmp_path):
        """Test that missing config file raises HTTPException 500"""
        svc = PDFService()
        svc.config = None
        svc.config_path = tmp_path / "nonexistent.json"

        with pytest.raises(HTTPException) as exc_info:
            svc._load_pdf_config()

        assert exc_info.value.status_code == 500
        # Inner 500 is caught and re-raised as generic "Failed to load PDF configuration"
        assert "configuration" in exc_info.value.detail.lower()

    def test_raises_500_on_invalid_json(self, tmp_path):
        """Test that invalid JSON raises HTTPException 500"""
        config_file = tmp_path / "pdf_form_mappings.json"
        config_file.write_text("{ invalid json !!!", encoding="utf-8")

        svc = PDFService()
        svc.config = None
        svc.config_path = config_file

        with pytest.raises(HTTPException) as exc_info:
            svc._load_pdf_config()

        assert exc_info.value.status_code == 500
        assert "invalid" in exc_info.value.detail.lower()


# ============================================================================
# Test get_available_forms()
# ============================================================================


class TestGetAvailableForms:
    """Test filtering available PDF forms by absence reason"""

    def test_returns_matching_form(self, service, mock_absence):
        """Test that forms matching absence reason are returned"""
        mock_absence.reason = "excursion"

        result = service.get_available_forms(mock_absence)

        assert len(result) == 1
        assert result[0]["type"] == "excursion_form"
        assert result[0]["label"] == "Exkursionsformular"
        assert result[0]["pdf_filename"] == "excursion.pdf"

    def test_returns_multiple_matching_forms(self, service, mock_absence):
        """Test that reason matching multiple forms returns all of them"""
        mock_absence.reason = "sick"  # matches sick_form (sick + personal)

        result = service.get_available_forms(mock_absence)

        assert len(result) == 1
        assert result[0]["type"] == "sick_form"

    def test_returns_empty_for_no_match(self, service, mock_absence):
        """Test that unmatched reason returns empty list"""
        mock_absence.reason = "training"  # not in any form

        result = service.get_available_forms(mock_absence)

        assert result == []

    def test_form_info_has_required_keys(self, service, mock_absence):
        """Test that returned form dicts have type, label, pdf_filename"""
        mock_absence.reason = "excursion"

        result = service.get_available_forms(mock_absence)

        form = result[0]
        assert "type" in form
        assert "label" in form
        assert "pdf_filename" in form


# ============================================================================
# Test _build_template_context()
# ============================================================================


class TestBuildTemplateContext:
    """Test context building for PDF template variable substitution"""

    @pytest.mark.asyncio
    async def test_parses_full_name_into_first_last(
        self, service, mock_absence, mock_db
    ):
        """Test that 'Max Mustermann' is split into first_name='Max', last_name='Mustermann'"""
        mock_absence.teacher.first_name = None
        mock_absence.teacher.last_name = None
        mock_absence.teacher.full_name = "Max Mustermann"
        service.webuntis_service._load_timegrid = AsyncMock(return_value={})

        context = await service._build_template_context(mock_absence, [], mock_db)

        assert context["absence"]["teacher"]["first_name"] == "Max"
        assert context["absence"]["teacher"]["last_name"] == "Mustermann"

    @pytest.mark.asyncio
    async def test_prefers_explicit_first_last_name(
        self, service, mock_absence, mock_db
    ):
        """Test that explicit first_name/last_name from WordPress overrides parsing"""
        mock_absence.teacher.first_name = "Maximilian"
        mock_absence.teacher.last_name = "Musterfrau"
        mock_absence.teacher.full_name = "Max Mustermann"
        service.webuntis_service._load_timegrid = AsyncMock(return_value={})

        context = await service._build_template_context(mock_absence, [], mock_db)

        # capitalize() is applied: "Maximilian" → "Maximilian", "Musterfrau" → "Musterfrau"
        assert context["absence"]["teacher"]["first_name"] == "Maximilian"
        assert context["absence"]["teacher"]["last_name"] == "Musterfrau"

    @pytest.mark.asyncio
    async def test_calculates_duration_days_correctly(
        self, service, mock_absence, mock_db
    ):
        """Test that duration_days is calculated inclusive (end - start + 1)"""
        mock_absence.start_date = datetime(2026, 2, 10)
        mock_absence.end_date = datetime(2026, 2, 12)  # 3 days
        service.webuntis_service._load_timegrid = AsyncMock(return_value={})

        context = await service._build_template_context(mock_absence, [], mock_db)

        assert context["absence"]["duration_days"] == 3

    @pytest.mark.asyncio
    async def test_single_day_duration_is_one(self, service, mock_absence, mock_db):
        """Test that single-day absence has duration_days=1"""
        mock_absence.start_date = datetime(2026, 2, 10)
        mock_absence.end_date = datetime(2026, 2, 10)
        service.webuntis_service._load_timegrid = AsyncMock(return_value={})

        context = await service._build_template_context(mock_absence, [], mock_db)

        assert context["absence"]["duration_days"] == 1

    @pytest.mark.asyncio
    async def test_combines_subjects_from_lessons(self, service, mock_absence, mock_db):
        """Test that lesson subjects are deduplicated and combined"""
        lesson1 = Mock()
        lesson1.subject = "Mathematik"
        lesson1.room = "101"
        lesson2 = Mock()
        lesson2.subject = "Mathematik"  # duplicate
        lesson2.room = "102"
        lesson3 = Mock()
        lesson3.subject = "Deutsch"
        lesson3.room = "101"
        service.webuntis_service._load_timegrid = AsyncMock(return_value={})

        context = await service._build_template_context(
            mock_absence, [lesson1, lesson2, lesson3], mock_db
        )

        subjects = context["lessons_subjects_combined"]
        assert "Mathematik" in subjects
        assert "Deutsch" in subjects
        # Deduplicated: "Mathematik" appears only once
        assert subjects.count("Mathematik") == 1

    @pytest.mark.asyncio
    async def test_falls_back_gracefully_on_timegrid_exception(
        self, service, mock_absence, mock_db
    ):
        """Test that timegrid loading exception is handled silently"""
        service.webuntis_service._load_timegrid = AsyncMock(
            side_effect=Exception("WebUntis unavailable")
        )

        # Should NOT raise - falls back to empty timegrid
        context = await service._build_template_context(mock_absence, [], mock_db)

        assert context is not None
        assert "absence" in context

    @pytest.mark.asyncio
    async def test_teacher_none_uses_empty_strings(
        self, service, mock_absence, mock_db
    ):
        """When absence.teacher is None, name/email fields default to empty strings"""
        mock_absence.teacher = None
        service.webuntis_service._load_timegrid = AsyncMock(return_value={})

        context = await service._build_template_context(mock_absence, [], mock_db)

        teacher_ctx = context["absence"]["teacher"]
        assert teacher_ctx["full_name"] == ""
        assert teacher_ctx["first_name"] == ""
        assert teacher_ctx["last_name"] == ""
        assert teacher_ctx["email"] == ""

    @pytest.mark.asyncio
    async def test_single_word_full_name_used_as_last_name(
        self, service, mock_absence, mock_db
    ):
        """A full_name with a single word (no space) is placed into last_name only"""
        mock_absence.teacher.first_name = None
        mock_absence.teacher.last_name = None
        mock_absence.teacher.full_name = "Sokrates"
        service.webuntis_service._load_timegrid = AsyncMock(return_value={})

        context = await service._build_template_context(mock_absence, [], mock_db)

        assert context["absence"]["teacher"]["first_name"] == ""
        assert context["absence"]["teacher"]["last_name"] == "Sokrates"


# ============================================================================
# Test generate_filled_pdf()
# ============================================================================


class TestGenerateFilledPdf:
    """Test PDF generation orchestration and error handling"""

    @pytest.mark.asyncio
    async def test_raises_404_for_unknown_form_type(
        self, service, mock_absence, mock_db
    ):
        """Test that unknown form_type raises HTTPException 404"""
        with pytest.raises(HTTPException) as exc_info:
            await service.generate_filled_pdf(mock_absence, "unknown_form", mock_db)

        assert exc_info.value.status_code == 404
        assert "unknown_form" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_404_when_pdf_template_missing(
        self, service, mock_absence, mock_db, tmp_path
    ):
        """Test that missing PDF template file raises HTTPException 404"""
        service.pdf_dir = tmp_path  # empty dir, no PDF files

        with pytest.raises(HTTPException) as exc_info:
            await service.generate_filled_pdf(mock_absence, "excursion_form", mock_db)

        assert exc_info.value.status_code == 404
        assert "excursion.pdf" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_generates_pdf_successfully(
        self, service, mock_absence, mock_db, tmp_path
    ):
        """Test successful PDF generation returns bytes"""
        # Create a fake PDF template file
        fake_pdf = tmp_path / "excursion.pdf"
        fake_pdf.write_bytes(b"fake pdf content")
        service.pdf_dir = tmp_path

        with patch.object(
            service, "_build_template_context", new_callable=AsyncMock
        ) as mock_ctx:
            mock_ctx.return_value = {}
            with patch.object(service, "_merge_fdf_with_pdf") as mock_merge:
                mock_merge.return_value = b"%PDF-1.4 fake output"
                with patch(
                    "app.services.pdf_service.template_service"
                ) as mock_template:
                    mock_template.process_field_mappings.return_value = {}

                    result = await service.generate_filled_pdf(
                        mock_absence, "excursion_form", mock_db
                    )

        assert result == b"%PDF-1.4 fake output"

    @pytest.mark.asyncio
    async def test_raises_500_on_generation_error(
        self, service, mock_absence, mock_db, tmp_path
    ):
        """Test that PDF merge failure raises HTTPException 500"""
        fake_pdf = tmp_path / "excursion.pdf"
        fake_pdf.write_bytes(b"fake pdf content")
        service.pdf_dir = tmp_path

        with patch.object(
            service, "_build_template_context", new_callable=AsyncMock
        ) as mock_ctx:
            mock_ctx.return_value = {}
            with patch.object(service, "_merge_fdf_with_pdf") as mock_merge:
                mock_merge.side_effect = Exception("pypdf error")
                with patch(
                    "app.services.pdf_service.template_service"
                ) as mock_template:
                    mock_template.process_field_mappings.return_value = {}

                    with pytest.raises(HTTPException) as exc_info:
                        await service.generate_filled_pdf(
                            mock_absence, "excursion_form", mock_db
                        )

        assert exc_info.value.status_code == 500
        assert "failed" in exc_info.value.detail.lower()


# ============================================================================
# Test _fix_pdf_encoding()
# ============================================================================


class TestFixPdfEncoding:
    """Test PDF field encoding handling"""

    def test_empty_string_returned_unchanged(self, service):
        """Test that empty string is returned as-is"""
        assert service._fix_pdf_encoding("") == ""

    def test_none_returned_unchanged(self, service):
        """Test that None is returned as-is"""
        assert service._fix_pdf_encoding(None) is None

    def test_latin1_compatible_text_unchanged(self, service):
        """Test that ASCII/Latin-1 text passes through unchanged"""
        result = service._fix_pdf_encoding("Hello School 123")
        assert result == "Hello School 123"

    def test_german_umlauts_handled(self, service):
        """Test that German umlauts (in Latin-1) are handled"""
        result = service._fix_pdf_encoding("Müller")
        assert result == "Müller"

    def test_bytes_input_decoded(self, service):
        """Test that bytes input is decoded to string"""
        result = service._fix_pdf_encoding(b"Hello")
        assert isinstance(result, str)
        assert result == "Hello"

    def test_invalid_utf8_bytes_decoded_via_latin1_fallback(self, service):
        """Bytes that are not valid UTF-8 are decoded with Latin-1 fallback"""
        # 0x80-0xFF are valid Latin-1 but not valid UTF-8 sequences
        invalid_utf8 = b"\x80\x99\xc3"
        result = service._fix_pdf_encoding(invalid_utf8)
        assert isinstance(result, str)

    def test_non_string_non_bytes_converted_to_str(self, service):
        """Non-string, non-bytes values (e.g. int) are converted via str()"""
        result = service._fix_pdf_encoding(42)
        assert result == "42"

    def test_non_latin1_characters_returned_as_utf8_string(self, service):
        """Characters outside Latin-1 (e.g. emoji, CJK) are returned as UTF-8 string"""
        # These characters cannot be encoded as Latin-1 → UnicodeEncodeError branch
        result = service._fix_pdf_encoding("Hallo 🎓 Welt")
        assert isinstance(result, str)
        assert "🎓" in result


# ============================================================================
# Test _merge_fdf_with_pdf()
# ============================================================================


def _make_mock_pypdf(output_bytes: bytes):
    """Build a pypdf mock module with PdfReader + PdfWriter that writes output_bytes."""
    mock_reader = Mock()
    mock_writer = Mock()
    mock_writer.pages = [Mock()]

    def fake_write(buf):
        buf.write(output_bytes)

    mock_writer.write = fake_write

    mock_pypdf = Mock()
    mock_pypdf.PdfReader = Mock(return_value=mock_reader)
    mock_pypdf.PdfWriter = Mock(return_value=mock_writer)
    return mock_pypdf, mock_reader, mock_writer


class TestMergeFdfWithPdf:
    """Tests for the internal PDF merging logic (previously always mocked)"""

    def test_raises_500_when_pypdf_not_installed(self, service, tmp_path):
        """ImportError during pypdf import raises HTTPException 500"""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"fake content")

        with patch.dict(sys.modules, {"pypdf": None}):
            with pytest.raises(HTTPException) as exc_info:
                service._merge_fdf_with_pdf(fake_pdf, {"Field": "Value"})

        assert exc_info.value.status_code == 500
        assert "not installed" in exc_info.value.detail.lower()

    def test_successful_merge_returns_bytes(self, service, tmp_path):
        """PDF is read, fields are written into the writer, and bytes are returned"""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"fake content")

        output_bytes = b"%PDF-1.4 result"
        mock_pypdf, mock_reader, mock_writer = _make_mock_pypdf(output_bytes)

        with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
            result = service._merge_fdf_with_pdf(fake_pdf, {"Name": "Max"})

        assert result == output_bytes
        mock_pypdf.PdfReader.assert_called_once_with(str(fake_pdf))
        mock_writer.clone_reader_document_root.assert_called_once_with(mock_reader)
        mock_writer.update_page_form_field_values.assert_called_once()

    def test_page_update_failure_logs_warning_and_continues(
        self, service, tmp_path
    ):
        """Exception during page field update is caught and logged; merge still completes"""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"fake content")

        output_bytes = b"%PDF-1.4 warning-path"
        mock_reader = Mock()
        mock_writer = Mock()
        mock_writer.pages = [Mock(), Mock()]  # two pages
        mock_writer.update_page_form_field_values.side_effect = Exception(
            "field update error"
        )

        def fake_write(buf):
            buf.write(output_bytes)

        mock_writer.write = fake_write

        mock_pypdf = Mock()
        mock_pypdf.PdfReader = Mock(return_value=mock_reader)
        mock_pypdf.PdfWriter = Mock(return_value=mock_writer)

        with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
            # Should NOT raise despite page update failures
            result = service._merge_fdf_with_pdf(fake_pdf, {})

        assert result == output_bytes
        # Both pages attempted
        assert mock_writer.update_page_form_field_values.call_count == 2

    def test_non_string_field_values_not_logged_as_string(self, service, tmp_path):
        """Non-string field values are passed through without debug logging (branch coverage)"""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"fake content")

        output_bytes = b"%PDF-1.4"
        mock_pypdf, _, mock_writer = _make_mock_pypdf(output_bytes)

        with patch.dict(sys.modules, {"pypdf": mock_pypdf}):
            # Pass a non-string value to exercise the isinstance(value, str) False branch
            result = service._merge_fdf_with_pdf(fake_pdf, {"Count": 42})

        assert result == output_bytes
