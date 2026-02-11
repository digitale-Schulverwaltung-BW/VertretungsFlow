"""
Unit tests for schemas/schemas.py

sanitize_text_input:
- None, empty string, non-string input → returns None / str(value)
- HTML tags stripped
- Dangerous control characters removed
- Max length enforced
- allow_newlines=False vs True

AffectedLessonBase.parse_date:
- Date-only string → T00:00:00 appended
- Datetime string passes through unchanged
- datetime object passes through unchanged

AbsenceBase field validators:
- validate_excursion_classes: required when reason='excursion', sanitized, optional otherwise
- validate_personal_reason: required when reason in ['personal', 'other'], optional otherwise
- validate_admin_notes: sanitized (no conditional logic)

AffectedLessonUpdate.validate_notes:
- Sanitized, None passthrough

AbsenceUpdate.parse_date:
- None passthrough
- Date-only string → T00:00:00 appended
"""

import pytest
from pydantic import ValidationError

from app.schemas.schemas import (
    AffectedLessonBase,
    AffectedLessonUpdate,
    AbsenceBase,
    AbsenceUpdate,
    sanitize_text_input,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_absence(**overrides):
    """Minimal valid AbsenceBase data dict."""
    data = {
        "reason": "sick",
        "start_date": "2026-02-11T08:00:00",
        "end_date": "2026-02-11T16:00:00",
        "start_period": 1,
        "end_period": 5,
    }
    data.update(overrides)
    return data


def make_lesson(**overrides):
    """Minimal valid AffectedLessonBase data dict."""
    data = {"date": "2026-02-11T08:00:00", "period": 1}
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# TestSanitizeTextInput
# ---------------------------------------------------------------------------


class TestSanitizeTextInput:
    def test_none_returns_none(self):
        assert sanitize_text_input(None) is None

    def test_empty_string_returns_none(self):
        assert sanitize_text_input("") is None

    def test_whitespace_only_returns_none(self):
        assert sanitize_text_input("   ") is None

    def test_non_string_converted_to_str(self):
        result = sanitize_text_input(42)  # type: ignore[arg-type]
        assert result == "42"

    def test_strips_leading_trailing_whitespace(self):
        result = sanitize_text_input("  hello  ")
        assert result == "hello"

    def test_removes_html_tags(self):
        result = sanitize_text_input("<script>alert('xss')</script>hello")
        assert result is not None
        assert "<script>" not in result
        assert "hello" in result

    def test_removes_html_tag_with_attributes(self):
        result = sanitize_text_input('<img src="x" onerror="alert(1)">text')
        assert result is not None
        assert "<img" not in result
        assert "text" in result

    def test_removes_dangerous_control_characters(self):
        # \x01 is a control char (not newline/tab)
        result = sanitize_text_input("hello\x01world")
        assert result is not None
        assert "\x01" not in result
        assert "helloworld" in result

    def test_keeps_newlines_when_allow_newlines_true(self):
        result = sanitize_text_input("line1\nline2", allow_newlines=True)
        assert result is not None
        assert "\n" in result

    def test_removes_newlines_when_allow_newlines_false(self):
        result = sanitize_text_input("line1\nline2", allow_newlines=False)
        assert result is not None
        assert "\n" not in result
        assert "line1line2" in result

    def test_enforces_max_length(self):
        long_input = "a" * 200
        result = sanitize_text_input(long_input, max_length=50)
        assert len(result) == 50

    def test_normal_text_passes_through(self):
        result = sanitize_text_input("Normale Bemerkung mit Umlauten: äöü")
        assert result == "Normale Bemerkung mit Umlauten: äöü"

    def test_removes_null_bytes(self):
        result = sanitize_text_input("hel\x00lo")
        assert result is not None
        assert "\x00" not in result


# ---------------------------------------------------------------------------
# TestAffectedLessonBaseParsDate
# ---------------------------------------------------------------------------


class TestAffectedLessonBaseParsDate:
    def test_date_only_string_gets_time_appended(self):
        lesson = AffectedLessonBase(**make_lesson(date="2026-02-11"))
        # After parsing, the date should have time component
        assert lesson.date.hour == 0
        assert lesson.date.minute == 0

    def test_datetime_string_passes_through(self):
        lesson = AffectedLessonBase(**make_lesson(date="2026-02-11T08:30:00"))
        assert lesson.date.hour == 8
        assert lesson.date.minute == 30

    def test_datetime_object_passes_through(self):
        from datetime import datetime

        dt = datetime(2026, 2, 11, 9, 0, 0)
        lesson = AffectedLessonBase(**make_lesson(date=dt))
        assert lesson.date == dt


# ---------------------------------------------------------------------------
# TestAbsenceBaseValidateExcursionClasses
# ---------------------------------------------------------------------------


class TestAbsenceBaseValidateExcursionClasses:
    def test_excursion_without_classes_raises_validation_error(self):
        with pytest.raises(ValidationError) as exc_info:
            AbsenceBase(**make_absence(reason="excursion", excursion_classes=None))
        assert "Pflichtfeld" in str(exc_info.value)

    def test_excursion_with_empty_string_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AbsenceBase(**make_absence(reason="excursion", excursion_classes="   "))

    def test_excursion_with_valid_classes_accepted(self):
        absence = AbsenceBase(
            **make_absence(reason="excursion", excursion_classes="10A, 10B")
        )
        assert absence.excursion_classes == "10A, 10B"

    def test_non_excursion_reason_does_not_require_classes(self):
        # sick reason → excursion_classes may be None
        absence = AbsenceBase(**make_absence(reason="sick", excursion_classes=None))
        assert absence.excursion_classes is None

    def test_excursion_classes_html_is_stripped(self):
        absence = AbsenceBase(
            **make_absence(reason="excursion", excursion_classes="<b>10A</b>")
        )
        assert absence.excursion_classes is not None
        assert "<b>" not in absence.excursion_classes
        assert "10A" in absence.excursion_classes


# ---------------------------------------------------------------------------
# TestAbsenceBaseValidatePersonalReason
# ---------------------------------------------------------------------------


class TestAbsenceBaseValidatePersonalReason:
    def test_personal_reason_without_text_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            AbsenceBase(**make_absence(reason="personal", personal_reason=None))
        assert "Pflichtfeld" in str(exc_info.value)

    def test_other_reason_without_text_raises_error(self):
        with pytest.raises(ValidationError):
            AbsenceBase(**make_absence(reason="other", personal_reason=None))

    def test_personal_reason_with_text_accepted(self):
        absence = AbsenceBase(
            **make_absence(reason="personal", personal_reason="Persönlicher Grund")
        )
        assert absence.personal_reason == "Persönlicher Grund"

    def test_sick_reason_does_not_require_personal_reason(self):
        absence = AbsenceBase(**make_absence(reason="sick", personal_reason=None))
        assert absence.personal_reason is None

    def test_personal_reason_sanitized(self):
        absence = AbsenceBase(
            **make_absence(reason="personal", personal_reason="<script>x</script>Grund")
        )
        assert absence.personal_reason is not None
        assert "<script>" not in absence.personal_reason
        assert "Grund" in absence.personal_reason


# ---------------------------------------------------------------------------
# TestAbsenceBaseValidateAdminNotes
# ---------------------------------------------------------------------------


class TestAbsenceBaseValidateAdminNotes:
    def test_admin_notes_none_stays_none(self):
        absence = AbsenceBase(**make_absence(admin_notes=None))
        assert absence.admin_notes is None

    def test_admin_notes_html_stripped(self):
        absence = AbsenceBase(**make_absence(admin_notes="<b>Bold</b> note"))
        assert absence.admin_notes is not None
        assert "<b>" not in absence.admin_notes
        assert "Bold" in absence.admin_notes

    def test_admin_notes_whitespace_becomes_none(self):
        absence = AbsenceBase(**make_absence(admin_notes="   "))
        assert absence.admin_notes is None


# ---------------------------------------------------------------------------
# TestAffectedLessonUpdateValidateNotes
# ---------------------------------------------------------------------------


class TestAffectedLessonUpdateValidateNotes:
    def test_notes_none_stays_none(self):
        update = AffectedLessonUpdate(notes=None)
        assert update.notes is None

    def test_notes_html_stripped(self):
        update = AffectedLessonUpdate(notes="<em>Hinweis</em>")
        assert update.notes is not None
        assert "<em>" not in update.notes
        assert "Hinweis" in update.notes

    def test_notes_normal_text_passes_through(self):
        update = AffectedLessonUpdate(notes="Stunde kann entfallen")
        assert update.notes == "Stunde kann entfallen"


# ---------------------------------------------------------------------------
# TestAbsenceUpdateParseDate
# ---------------------------------------------------------------------------


class TestAbsenceUpdateParseDate:
    def test_none_passes_through(self):
        update = AbsenceUpdate(start_date=None, start_period=None, end_period=None)
        assert update.start_date is None

    def test_date_only_string_gets_time_appended(self):
        update = AbsenceUpdate(start_date="2026-02-11", start_period=None, end_period=None)
        assert update.start_date is not None
        assert update.start_date.hour == 0
        assert update.start_date.minute == 0

    def test_datetime_string_passes_through(self):
        update = AbsenceUpdate(start_date="2026-02-11T09:30:00", start_period=None, end_period=None)
        assert update.start_date is not None
        assert update.start_date.hour == 9
        assert update.start_date.minute == 30
