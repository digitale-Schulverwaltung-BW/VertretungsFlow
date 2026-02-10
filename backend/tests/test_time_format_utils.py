"""
Tests for time_format_utils.py
Tests WebUntis time conversion and period calculations
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.utils.time_format_utils import (
    _calculate_end_time,
    _load_time_from_config,
    format_webuntis_time,
    get_time_for_period,
    get_time_from_period,
)


# ============================================================================
# Test format_webuntis_time()
# ============================================================================


class TestFormatWebuntisTime:
    """Test WebUntis time format conversion"""

    def test_format_morning_time(self):
        """Test conversion of morning time (7:30)"""
        assert format_webuntis_time(730) == "07:30"

    def test_format_afternoon_time(self):
        """Test conversion of afternoon time (15:45)"""
        assert format_webuntis_time(1545) == "15:45"

    def test_format_quarter_past(self):
        """Test conversion with 15-minute mark"""
        assert format_webuntis_time(815) == "08:15"

    def test_format_full_hour(self):
        """Test conversion of full hour (8:00)"""
        assert format_webuntis_time(800) == "08:00"

    def test_format_midday(self):
        """Test conversion of midday time (12:00)"""
        assert format_webuntis_time(1200) == "12:00"

    def test_format_single_digit_minute(self):
        """Test conversion with single-digit minute (8:05)"""
        assert format_webuntis_time(805) == "08:05"

    def test_format_zero_time(self):
        """Test conversion of midnight (0:00)"""
        assert format_webuntis_time(0) == "00:00"


# ============================================================================
# Test _calculate_end_time()
# ============================================================================


class TestCalculateEndTime:
    """Test 45-minute end time calculation"""

    def test_calculate_without_overflow(self):
        """Test calculation when no hour overflow (8:00 -> 8:45)"""
        assert _calculate_end_time(800) == "08:45"

    def test_calculate_with_overflow(self):
        """Test calculation with hour overflow (8:30 -> 9:15)"""
        assert _calculate_end_time(830) == "09:15"

    def test_calculate_near_noon(self):
        """Test calculation near noon (11:45 -> 12:30)"""
        assert _calculate_end_time(1145) == "12:30"

    def test_calculate_afternoon(self):
        """Test calculation in afternoon (14:15 -> 15:00)"""
        assert _calculate_end_time(1415) == "15:00"

    def test_calculate_edge_case_15_min(self):
        """Test edge case with 15 min start (7:15 -> 8:00)"""
        assert _calculate_end_time(715) == "08:00"

    def test_calculate_edge_case_30_min(self):
        """Test edge case with 30 min start (9:30 -> 10:15)"""
        assert _calculate_end_time(930) == "10:15"


# ============================================================================
# Test _load_time_from_config()
# ============================================================================


class TestLoadTimeFromConfig:
    """Test loading period times from config file"""

    def test_load_start_time_from_config(self, tmp_path):
        """Test loading start time from config file"""
        # Create temporary config file
        config = {
            "period_time_mapping": {
                "1": "08:00",
                "2": "08:50",
                "5": "11:30",
            }
        }
        config_path = tmp_path / "pdf_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        # Test loading
        assert _load_time_from_config(config_path, 1, "start") == "08:00"
        assert _load_time_from_config(config_path, 2, "start") == "08:50"
        assert _load_time_from_config(config_path, 5, "start") == "11:30"

    def test_load_end_time_from_config(self, tmp_path):
        """Test loading end time from config file"""
        config = {
            "period_end_time_mapping": {
                "1": "08:45",
                "2": "09:35",
                "5": "12:15",
            }
        }
        config_path = tmp_path / "pdf_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        # Test loading
        assert _load_time_from_config(config_path, 1, "end") == "08:45"
        assert _load_time_from_config(config_path, 2, "end") == "09:35"
        assert _load_time_from_config(config_path, 5, "end") == "12:15"

    def test_load_missing_period_returns_none(self, tmp_path):
        """Test that missing period returns None"""
        config = {
            "period_time_mapping": {
                "1": "08:00",
            }
        }
        config_path = tmp_path / "pdf_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        # Period 2 doesn't exist
        assert _load_time_from_config(config_path, 2, "start") is None

    def test_load_invalid_json_returns_none(self, tmp_path):
        """Test that invalid JSON returns None"""
        config_path = tmp_path / "invalid.json"
        config_path.write_text("{ invalid json", encoding="utf-8")

        # Should return None without crashing
        assert _load_time_from_config(config_path, 1, "start") is None

    def test_load_missing_file_returns_none(self, tmp_path):
        """Test that missing file returns None"""
        config_path = tmp_path / "nonexistent.json"

        # Should return None without crashing
        assert _load_time_from_config(config_path, 1, "start") is None


# ============================================================================
# Test get_time_from_period()
# ============================================================================


class TestGetTimeFromPeriod:
    """Test reverse lookup of time from period"""

    @pytest.fixture
    def sample_timegrid(self):
        """Sample timegrid for testing"""
        return {
            800: 1,  # Period 1 starts at 8:00
            850: 2,  # Period 2 starts at 8:50
            955: 3,  # Period 3 starts at 9:55
            1045: 4,  # Period 4 starts at 10:45
            1130: 5,  # Period 5 starts at 11:30
        }

    def test_get_start_time_from_timegrid(self, sample_timegrid):
        """Test getting start time from timegrid"""
        result = get_time_from_period(sample_timegrid, 1, "start")
        assert result == "08:00"

        result = get_time_from_period(sample_timegrid, 3, "start")
        assert result == "09:55"

    def test_get_end_time_from_timegrid(self, sample_timegrid):
        """Test getting end time (calculated) from timegrid"""
        # Period 1 starts at 8:00, should end at 8:45
        result = get_time_from_period(sample_timegrid, 1, "end")
        assert result == "08:45"

        # Period 2 starts at 8:50, should end at 9:35
        result = get_time_from_period(sample_timegrid, 2, "end")
        assert result == "09:35"

    def test_timegrid_with_string_periods(self):
        """Test timegrid with string values (JSONB conversion)"""
        timegrid = {
            800: "1",  # String instead of int
            850: "2",
        }
        result = get_time_from_period(timegrid, 1, "start")
        assert result == "08:00"

    def test_missing_period_uses_config_fallback(self, tmp_path):
        """Test that missing period falls back to config"""
        timegrid = {800: 1, 850: 2}
        config = {
            "period_time_mapping": {"10": "14:00"},
            "period_end_time_mapping": {"10": "14:45"},
        }
        config_path = tmp_path / "pdf_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        # Period 10 not in timegrid, should use config
        result = get_time_from_period(timegrid, 10, "start", config_path)
        assert result == "14:00"

        result = get_time_from_period(timegrid, 10, "end", config_path)
        assert result == "14:45"

    def test_missing_period_ultimate_fallback(self):
        """Test ultimate fallback when timegrid and config fail"""
        timegrid = {800: 1}

        # No config provided, period not in timegrid
        result = get_time_from_period(timegrid, 99, "start")
        assert result == "08:00"  # Ultimate fallback

        result = get_time_from_period(timegrid, 99, "end")
        assert result == "15:45"  # Ultimate fallback

    def test_empty_timegrid_uses_fallback(self):
        """Test that empty timegrid uses ultimate fallback"""
        result = get_time_from_period({}, 1, "start")
        assert result == "08:00"

        result = get_time_from_period({}, 1, "end")
        assert result == "15:45"


# ============================================================================
# Test get_time_for_period()
# ============================================================================


class TestGetTimeForPeriod:
    """Test getting time for period with lesson data priority"""

    @pytest.fixture
    def sample_timegrid(self):
        """Sample timegrid for testing"""
        return {
            800: 1,
            850: 2,
            955: 3,
        }

    @pytest.fixture
    def mock_lessons(self):
        """Create mock AffectedLesson objects"""
        lesson1 = Mock()
        lesson1.period = 1
        lesson1.start_time = 800
        lesson1.end_time = 845

        lesson2 = Mock()
        lesson2.period = 2
        lesson2.start_time = 850
        lesson2.end_time = 935

        lesson3 = Mock()
        lesson3.period = 5
        lesson3.start_time = None  # No time data
        lesson3.end_time = None

        return [lesson1, lesson2, lesson3]

    def test_get_start_time_from_lesson(self, mock_lessons, sample_timegrid):
        """Test that lesson start time is preferred over timegrid"""
        result = get_time_for_period(mock_lessons, 1, "start", sample_timegrid)
        assert result == "08:00"

        result = get_time_for_period(mock_lessons, 2, "start", sample_timegrid)
        assert result == "08:50"

    def test_get_end_time_from_lesson(self, mock_lessons, sample_timegrid):
        """Test that lesson end time is preferred over timegrid"""
        result = get_time_for_period(mock_lessons, 1, "end", sample_timegrid)
        assert result == "08:45"

        result = get_time_for_period(mock_lessons, 2, "end", sample_timegrid)
        assert result == "09:35"

    def test_fallback_to_timegrid_when_no_lesson_data(
        self, mock_lessons, sample_timegrid
    ):
        """Test fallback to timegrid when lesson has no time data"""
        # Period 5 has no time data in lesson, should use timegrid fallback
        # Since period 5 is not in timegrid, ultimate fallback is used
        result = get_time_for_period(mock_lessons, 5, "start", sample_timegrid)
        assert result == "08:00"  # Ultimate fallback

    def test_fallback_to_timegrid_when_period_not_in_lessons(
        self, mock_lessons, sample_timegrid
    ):
        """Test fallback to timegrid when period not in lessons at all"""
        # Period 3 not in lessons, should use timegrid
        result = get_time_for_period(mock_lessons, 3, "start", sample_timegrid)
        assert result == "09:55"  # From timegrid

        # Calculated end time (9:55 + 45min = 10:40)
        result = get_time_for_period(mock_lessons, 3, "end", sample_timegrid)
        assert result == "10:40"

    def test_empty_lessons_list_uses_timegrid(self, sample_timegrid):
        """Test that empty lessons list falls back to timegrid"""
        result = get_time_for_period([], 1, "start", sample_timegrid)
        assert result == "08:00"

    def test_with_config_fallback(self, tmp_path):
        """Test full fallback chain: lessons -> timegrid -> config -> ultimate"""
        config = {
            "period_time_mapping": {"10": "14:00"},
            "period_end_time_mapping": {"10": "14:45"},
        }
        config_path = tmp_path / "pdf_config.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")

        timegrid = {800: 1}
        lessons: list = []

        # Period 10 not in lessons or timegrid, should use config
        result = get_time_for_period(lessons, 10, "start", timegrid, config_path)
        assert result == "14:00"

        result = get_time_for_period(lessons, 10, "end", timegrid, config_path)
        assert result == "14:45"
