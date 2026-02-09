"""
Tests for template_service.py
Tests template variable processing and substitution logic
"""

from datetime import datetime

import pytest

from app.services.template_service import TemplateService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def template_service():
    """Create TemplateService instance"""
    return TemplateService()


@pytest.fixture
def sample_context():
    """Create sample context with nested data"""
    return {
        "absence": {
            "id": 123,
            "reason": "sick",
            "start_date": datetime(2024, 3, 15, 8, 0),
            "end_date": datetime(2024, 3, 17, 12, 0),
            "teacher": {
                "full_name": "Max Mustermann",
                "email": "max@example.com",
                "webuntis_code": "MUS",
            },
        },
        "school": {
            "name": "Beispielschule",
            "address": "Hauptstraße 1",
        },
        "plain_value": "Test Value",
    }


# ============================================================================
# Test get_nested_value()
# ============================================================================


class TestGetNestedValue:
    """Test nested value extraction with dot notation"""

    def test_get_simple_value(self, template_service, sample_context):
        """Test getting simple top-level value"""
        result = template_service.get_nested_value(sample_context, "plain_value")
        assert result == "Test Value"

    def test_get_nested_value_level_1(self, template_service, sample_context):
        """Test getting value nested one level deep"""
        result = template_service.get_nested_value(sample_context, "absence.reason")
        assert result == "sick"

    def test_get_nested_value_level_2(self, template_service, sample_context):
        """Test getting value nested two levels deep"""
        result = template_service.get_nested_value(
            sample_context, "absence.teacher.full_name"
        )
        assert result == "Max Mustermann"

    def test_get_nested_value_level_3(self, template_service):
        """Test getting value nested three levels deep"""
        context = {"a": {"b": {"c": {"d": "deep_value"}}}}
        result = template_service.get_nested_value(context, "a.b.c.d")
        assert result == "deep_value"

    def test_get_datetime_value(self, template_service, sample_context):
        """Test getting datetime value"""
        result = template_service.get_nested_value(sample_context, "absence.start_date")
        assert isinstance(result, datetime)
        assert result == datetime(2024, 3, 15, 8, 0)

    def test_get_integer_value(self, template_service, sample_context):
        """Test getting integer value"""
        result = template_service.get_nested_value(sample_context, "absence.id")
        assert result == 123

    def test_missing_key_returns_none(self, template_service, sample_context):
        """Test that missing key returns None"""
        result = template_service.get_nested_value(sample_context, "absence.nonexistent")
        assert result is None

    def test_missing_nested_key_returns_none(self, template_service, sample_context):
        """Test that missing nested key returns None"""
        result = template_service.get_nested_value(
            sample_context, "absence.teacher.nonexistent.key"
        )
        assert result is None

    def test_path_through_non_dict_returns_none(self, template_service):
        """Test that path through non-dict value returns None"""
        context = {"value": "string_value"}
        # Try to access "value.key" where "value" is not a dict
        result = template_service.get_nested_value(context, "value.key")
        assert result is None

    def test_empty_context(self, template_service):
        """Test with empty context"""
        result = template_service.get_nested_value({}, "any.path")
        assert result is None


# ============================================================================
# Test apply_filter()
# ============================================================================


class TestApplyFilter:
    """Test filter application"""

    def test_format_date_filter_german_format(self, template_service):
        """Test format_date filter with German date format"""
        date_value = datetime(2024, 3, 15, 10, 30)
        result = template_service.apply_filter(date_value, "format_date('%d.%m.%Y')")
        assert result == "15.03.2024"

    def test_format_date_filter_iso_format(self, template_service):
        """Test format_date filter with ISO format"""
        date_value = datetime(2024, 3, 15, 10, 30)
        result = template_service.apply_filter(date_value, "format_date('%Y-%m-%d')")
        assert result == "2024-03-15"

    def test_format_date_filter_with_time(self, template_service):
        """Test format_date filter including time"""
        date_value = datetime(2024, 3, 15, 10, 30)
        result = template_service.apply_filter(
            date_value, "format_date('%d.%m.%Y %H:%M')"
        )
        assert result == "15.03.2024 10:30"

    def test_format_date_filter_short_format(self, template_service):
        """Test format_date filter with short format"""
        date_value = datetime(2024, 3, 15, 10, 30)
        result = template_service.apply_filter(date_value, "format_date('%d.%m.%y')")
        assert result == "15.03.24"

    def test_format_date_with_double_quotes(self, template_service):
        """Test format_date filter with double quotes"""
        date_value = datetime(2024, 3, 15, 10, 30)
        result = template_service.apply_filter(date_value, 'format_date("%d.%m.%Y")')
        assert result == "15.03.2024"

    def test_format_date_on_non_datetime_returns_string(self, template_service):
        """Test format_date filter on non-datetime value returns string representation"""
        result = template_service.apply_filter("not a date", "format_date('%d.%m.%Y')")
        assert result == "not a date"

    def test_format_date_on_none_returns_empty(self, template_service):
        """Test format_date filter on None returns empty string"""
        result = template_service.apply_filter(None, "format_date('%d.%m.%Y')")
        assert result == ""

    def test_unknown_filter_returns_string(self, template_service):
        """Test unknown filter returns string representation of value"""
        result = template_service.apply_filter("test_value", "unknown_filter('arg')")
        assert result == "test_value"

    def test_unknown_filter_on_none_returns_empty(self, template_service):
        """Test unknown filter on None returns empty string"""
        result = template_service.apply_filter(None, "unknown_filter('arg')")
        assert result == ""

    def test_invalid_filter_expression_returns_string(self, template_service):
        """Test invalid filter expression returns string representation"""
        result = template_service.apply_filter("test_value", "invalid expression")
        assert result == "test_value"

    def test_filter_without_parentheses_returns_string(self, template_service):
        """Test filter without parentheses returns string representation"""
        result = template_service.apply_filter("test_value", "format_date")
        assert result == "test_value"

    def test_filter_with_integer_value(self, template_service):
        """Test filter with integer value"""
        result = template_service.apply_filter(123, "unknown_filter('arg')")
        assert result == "123"


# ============================================================================
# Test process_template_variable()
# ============================================================================


class TestProcessTemplateVariable:
    """Test template variable processing"""

    def test_process_simple_variable_with_brackets(
        self, template_service, sample_context
    ):
        """Test processing simple variable with {{ }} brackets"""
        result = template_service.process_template_variable(
            "{{ plain_value }}", sample_context
        )
        assert result == "Test Value"

    def test_process_simple_variable_without_brackets(
        self, template_service, sample_context
    ):
        """Test processing simple variable without brackets (returns as plain text)"""
        result = template_service.process_template_variable(
            "plain_value", sample_context
        )
        # Without {{ }}, it's treated as plain text and returned as-is
        assert result == "plain_value"

    def test_process_nested_variable(self, template_service, sample_context):
        """Test processing nested variable"""
        result = template_service.process_template_variable(
            "{{ absence.teacher.full_name }}", sample_context
        )
        assert result == "Max Mustermann"

    def test_process_variable_with_filter(self, template_service, sample_context):
        """Test processing variable with format_date filter"""
        result = template_service.process_template_variable(
            "{{ absence.start_date | format_date('%d.%m.%Y') }}", sample_context
        )
        assert result == "15.03.2024"

    def test_process_variable_with_filter_no_spaces(
        self, template_service, sample_context
    ):
        """Test processing variable with filter without spaces"""
        result = template_service.process_template_variable(
            "{{absence.start_date|format_date('%d.%m.%Y')}}", sample_context
        )
        assert result == "15.03.2024"

    def test_process_variable_with_filter_extra_spaces(
        self, template_service, sample_context
    ):
        """Test processing variable with filter and extra spaces"""
        result = template_service.process_template_variable(
            "{{  absence.start_date  |  format_date('%d.%m.%Y')  }}", sample_context
        )
        assert result == "15.03.2024"

    def test_process_missing_variable_returns_empty(
        self, template_service, sample_context
    ):
        """Test processing missing variable returns empty string"""
        result = template_service.process_template_variable(
            "{{ nonexistent.path }}", sample_context
        )
        assert result == ""

    def test_process_plain_text_returns_as_is(self, template_service, sample_context):
        """Test that plain text without brackets returns as-is"""
        result = template_service.process_template_variable(
            "Just plain text", sample_context
        )
        assert result == "Just plain text"

    def test_process_empty_string_returns_empty(
        self, template_service, sample_context
    ):
        """Test processing empty string returns empty"""
        result = template_service.process_template_variable("", sample_context)
        assert result == ""

    def test_process_none_returns_empty(self, template_service, sample_context):
        """Test processing None returns empty string"""
        result = template_service.process_template_variable(None, sample_context)
        assert result == ""

    def test_process_non_string_returns_empty(self, template_service, sample_context):
        """Test processing non-string value returns empty string"""
        result = template_service.process_template_variable(123, sample_context)
        assert result == ""

    def test_process_integer_value(self, template_service, sample_context):
        """Test processing variable that contains integer"""
        result = template_service.process_template_variable(
            "{{ absence.id }}", sample_context
        )
        assert result == "123"

    def test_process_nested_datetime_with_filter(
        self, template_service, sample_context
    ):
        """Test processing nested datetime with filter"""
        result = template_service.process_template_variable(
            "{{ absence.end_date | format_date('%Y-%m-%d') }}", sample_context
        )
        assert result == "2024-03-17"

    def test_process_variable_multiple_levels_deep(
        self, template_service, sample_context
    ):
        """Test processing variable with multiple nesting levels"""
        result = template_service.process_template_variable(
            "{{ absence.teacher.webuntis_code }}", sample_context
        )
        assert result == "MUS"

    def test_process_only_opening_bracket(self, template_service, sample_context):
        """Test that incomplete brackets return as-is"""
        result = template_service.process_template_variable(
            "{{ plain_value", sample_context
        )
        assert result == "{{ plain_value"

    def test_process_only_closing_bracket(self, template_service, sample_context):
        """Test that incomplete brackets return as-is"""
        result = template_service.process_template_variable(
            "plain_value }}", sample_context
        )
        assert result == "plain_value }}"


# ============================================================================
# Test process_field_mappings()
# ============================================================================


class TestProcessFieldMappings:
    """Test batch field mapping processing"""

    def test_process_simple_mappings(self, template_service, sample_context):
        """Test processing simple field mappings"""
        mappings = {
            "field_1": "{{ plain_value }}",
            "field_2": "{{ absence.reason }}",
            "field_3": "{{ school.name }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        assert result == {
            "field_1": "Test Value",
            "field_2": "sick",
            "field_3": "Beispielschule",
        }

    def test_process_mappings_with_filters(self, template_service, sample_context):
        """Test processing mappings with filters"""
        mappings = {
            "start_date": "{{ absence.start_date | format_date('%d.%m.%Y') }}",
            "end_date": "{{ absence.end_date | format_date('%d.%m.%Y') }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        assert result == {
            "start_date": "15.03.2024",
            "end_date": "17.03.2024",
        }

    def test_process_mappings_skip_comments(self, template_service, sample_context):
        """Test that comment fields (starting with _) are skipped"""
        mappings = {
            "real_field": "{{ plain_value }}",
            "_comment": "This is a comment field",
            "_note": "Another comment",
            "another_field": "{{ absence.reason }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        # Comment fields should be excluded
        assert result == {
            "real_field": "Test Value",
            "another_field": "sick",
        }
        assert "_comment" not in result
        assert "_note" not in result

    def test_process_nested_mappings(self, template_service, sample_context):
        """Test processing nested variable mappings"""
        mappings = {
            "teacher_name": "{{ absence.teacher.full_name }}",
            "teacher_email": "{{ absence.teacher.email }}",
            "teacher_code": "{{ absence.teacher.webuntis_code }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        assert result == {
            "teacher_name": "Max Mustermann",
            "teacher_email": "max@example.com",
            "teacher_code": "MUS",
        }

    def test_process_mappings_with_missing_values(
        self, template_service, sample_context
    ):
        """Test processing mappings with missing values (should return empty strings)"""
        mappings = {
            "exists": "{{ plain_value }}",
            "missing": "{{ nonexistent.path }}",
            "also_missing": "{{ absence.teacher.phone }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        assert result == {
            "exists": "Test Value",
            "missing": "",
            "also_missing": "",
        }

    def test_process_empty_mappings(self, template_service, sample_context):
        """Test processing empty mappings dict"""
        result = template_service.process_field_mappings({}, sample_context)
        assert result == {}

    def test_process_mappings_with_plain_text(self, template_service, sample_context):
        """Test processing mappings with plain text (no template variables)"""
        mappings = {
            "static_field": "Static Value",
            "another_static": "Another Static",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        assert result == {
            "static_field": "Static Value",
            "another_static": "Another Static",
        }

    def test_process_mixed_mappings(self, template_service, sample_context):
        """Test processing mix of template variables, filters, and plain text"""
        mappings = {
            "template_var": "{{ plain_value }}",
            "with_filter": "{{ absence.start_date | format_date('%d.%m.%Y') }}",
            "plain_text": "Just text",
            "_comment": "Skip this",
            "nested": "{{ absence.teacher.full_name }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        assert result == {
            "template_var": "Test Value",
            "with_filter": "15.03.2024",
            "plain_text": "Just text",
            "nested": "Max Mustermann",
        }
        assert "_comment" not in result

    def test_process_mappings_preserves_order(self, template_service, sample_context):
        """Test that field mapping order is preserved (Python 3.7+)"""
        mappings = {
            "field_z": "{{ plain_value }}",
            "field_a": "{{ absence.reason }}",
            "field_m": "{{ school.name }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        # Dict order is preserved in Python 3.7+
        assert list(result.keys()) == ["field_z", "field_a", "field_m"]

    def test_process_mappings_with_integer_values(
        self, template_service, sample_context
    ):
        """Test processing mappings with integer values"""
        mappings = {
            "absence_id": "{{ absence.id }}",
        }
        result = template_service.process_field_mappings(mappings, sample_context)

        assert result == {
            "absence_id": "123",
        }


# ============================================================================
# Integration Tests - Real-world scenarios
# ============================================================================


class TestRealWorldScenarios:
    """Test realistic template processing scenarios"""

    def test_pdf_form_filling_scenario(self, template_service):
        """Test typical PDF form filling scenario"""
        context = {
            "absence": {
                "teacher": {"full_name": "Anna Schmidt", "webuntis_code": "SCH"},
                "start_date": datetime(2024, 3, 15),
                "end_date": datetime(2024, 3, 15),
                "reason": "Fortbildung",
                "description": "Python Workshop",
            },
            "school": {"name": "Gymnasium Beispiel", "principal": "Dr. Müller"},
        }

        mappings = {
            "Name": "{{ absence.teacher.full_name }}",
            "Kuerzel": "{{ absence.teacher.webuntis_code }}",
            "Von": "{{ absence.start_date | format_date('%d.%m.%Y') }}",
            "Bis": "{{ absence.end_date | format_date('%d.%m.%Y') }}",
            "Grund": "{{ absence.reason }}",
            "Beschreibung": "{{ absence.description }}",
            "Schule": "{{ school.name }}",
            "_hinweis": "Dies ist ein Kommentar",
        }

        result = template_service.process_field_mappings(mappings, context)

        assert result == {
            "Name": "Anna Schmidt",
            "Kuerzel": "SCH",
            "Von": "15.03.2024",
            "Bis": "15.03.2024",
            "Grund": "Fortbildung",
            "Beschreibung": "Python Workshop",
            "Schule": "Gymnasium Beispiel",
        }

    def test_complex_nested_data_scenario(self, template_service):
        """Test complex nested data extraction"""
        context = {
            "absence": {
                "teacher": {
                    "personal": {
                        "first_name": "Max",
                        "last_name": "Mustermann",
                    },
                    "contact": {
                        "email": "max@example.com",
                        "phone": "+49123456789",
                    },
                },
            }
        }

        # Extract deeply nested values
        first_name = template_service.process_template_variable(
            "{{ absence.teacher.personal.first_name }}", context
        )
        email = template_service.process_template_variable(
            "{{ absence.teacher.contact.email }}", context
        )

        assert first_name == "Max"
        assert email == "max@example.com"

    def test_multiple_date_formats_scenario(self, template_service):
        """Test handling multiple date formats in one context"""
        date_value = datetime(2024, 12, 25, 14, 30)
        context = {"date": date_value}

        formats = {
            "german": "{{ date | format_date('%d.%m.%Y') }}",
            "iso": "{{ date | format_date('%Y-%m-%d') }}",
            "with_time": "{{ date | format_date('%d.%m.%Y %H:%M') }}",
            "short": "{{ date | format_date('%d.%m.%y') }}",
        }

        result = template_service.process_field_mappings(formats, context)

        assert result == {
            "german": "25.12.2024",
            "iso": "2024-12-25",
            "with_time": "25.12.2024 14:30",
            "short": "25.12.24",
        }
