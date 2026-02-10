"""
Tests for absence_utils.py
Tests absence validation and lesson filtering logic
"""

from datetime import datetime

import pytest
from fastapi import HTTPException

from app.schemas.schemas import WebUntisLesson
from app.utils.absence_utils import is_lesson_in_period, validate_date_range


# ============================================================================
# Test validate_date_range()
# ============================================================================


class TestValidateDateRange:
    """Test date range validation"""

    def test_valid_single_day_same_period(self):
        """Test valid single-day absence with same period"""
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 9, 0)
        # Should not raise exception
        validate_date_range(start, end, start_period=1, end_period=1)

    def test_valid_single_day_multiple_periods(self):
        """Test valid single-day absence with multiple periods"""
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)
        # Should not raise exception
        validate_date_range(start, end, start_period=1, end_period=6)

    def test_valid_multi_day_absence(self):
        """Test valid multi-day absence"""
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)
        # Should not raise exception
        validate_date_range(start, end, start_period=1, end_period=6)

    def test_valid_same_date_end_after_start(self):
        """Test valid case where end_date equals start_date"""
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 8, 0)
        # Should not raise exception
        validate_date_range(start, end, start_period=1, end_period=1)

    def test_invalid_end_date_before_start_date(self):
        """Test that end_date before start_date raises exception (VALIDATION!)"""
        start = datetime(2024, 3, 17, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)  # 2 days earlier!

        with pytest.raises(HTTPException) as exc_info:
            validate_date_range(start, end, start_period=1, end_period=6)

        assert exc_info.value.status_code == 400
        assert "End date must be after or equal to start date" in str(
            exc_info.value.detail
        )

    def test_invalid_end_period_before_start_period_same_day(self):
        """Test that end_period < start_period on same day raises exception (VALIDATION!)"""
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)

        with pytest.raises(HTTPException) as exc_info:
            validate_date_range(start, end, start_period=6, end_period=1)  # 6 > 1!

        assert exc_info.value.status_code == 400
        assert "End period must be after or equal to start period" in str(
            exc_info.value.detail
        )

    def test_valid_different_days_any_periods(self):
        """Test that period order doesn't matter for different days"""
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # Even if end_period < start_period, it's valid because different days
        # (first day starts at period 6, last day ends at period 1)
        validate_date_range(start, end, start_period=6, end_period=1)


# ============================================================================
# Test is_lesson_in_period()
# ============================================================================


class TestIsLessonInPeriod:
    """Test lesson period filtering"""

    def test_lesson_in_single_day_period(self):
        """Test lesson within single-day period"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 8, 0),
            period=3,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)

        # Lesson period 3 is within [1, 6]
        assert is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)

    def test_lesson_at_start_boundary_single_day(self):
        """Test lesson at start boundary of single-day period"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 8, 0),
            period=1,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)

        # Lesson period 1 equals start_period
        assert is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)

    def test_lesson_at_end_boundary_single_day(self):
        """Test lesson at end boundary of single-day period"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 12, 0),
            period=6,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)

        # Lesson period 6 equals end_period
        assert is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)

    def test_lesson_before_period_single_day(self):
        """Test lesson before period on single day"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 7, 30),
            period=0,  # Before period 1
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)

        # Lesson period 0 < start_period 1
        assert not is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)

    def test_lesson_after_period_single_day(self):
        """Test lesson after period on single day"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 14, 0),
            period=8,  # After period 6
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)

        # Lesson period 8 > end_period 6
        assert not is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)

    def test_lesson_on_first_day_multi_day(self):
        """Test lesson on first day of multi-day period"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 10, 0),
            period=5,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # On first day, lesson must be >= start_period (3)
        assert is_lesson_in_period(lesson, start, end, start_period=3, end_period=2)

    def test_lesson_before_start_period_on_first_day(self):
        """Test lesson before start_period on first day of multi-day period"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 8, 0),
            period=2,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # On first day, period 2 < start_period 3
        assert not is_lesson_in_period(lesson, start, end, start_period=3, end_period=6)

    def test_lesson_on_last_day_multi_day(self):
        """Test lesson on last day of multi-day period"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 17, 10, 0),
            period=2,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # On last day, lesson must be <= end_period (4)
        assert is_lesson_in_period(lesson, start, end, start_period=1, end_period=4)

    def test_lesson_after_end_period_on_last_day(self):
        """Test lesson after end_period on last day of multi-day period"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 17, 14, 0),
            period=6,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # On last day, period 6 > end_period 4
        assert not is_lesson_in_period(lesson, start, end, start_period=1, end_period=4)

    def test_lesson_on_middle_day_multi_day(self):
        """Test lesson on middle day of multi-day period (any period is valid)"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 16, 10, 0),
            period=5,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # Middle day = all lessons included regardless of period
        assert is_lesson_in_period(lesson, start, end, start_period=1, end_period=2)

    def test_lesson_on_middle_day_any_period(self):
        """Test that any period is valid on middle days"""
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 20, 12, 0)

        # Middle days (16, 17, 18, 19) should accept all periods
        for day in [16, 17, 18, 19]:
            for period in [1, 5, 10]:
                lesson = WebUntisLesson(
                    date=datetime(2024, 3, day, 10, 0),
                    period=period,
                    subject="Math",
                    class_name="10A",
                )
                assert is_lesson_in_period(
                    lesson, start, end, start_period=3, end_period=4
                )

    def test_lesson_before_date_range(self):
        """Test lesson before date range"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 14, 10, 0),  # Day before
            period=3,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # Lesson date before start date
        assert not is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)

    def test_lesson_after_date_range(self):
        """Test lesson after date range"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 18, 10, 0),  # Day after
            period=3,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 17, 12, 0)

        # Lesson date after end date
        assert not is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)

    def test_lesson_with_time_fields_populated(self):
        """Test that time fields don't affect filtering (only date/period matter)"""
        lesson = WebUntisLesson(
            date=datetime(2024, 3, 15, 8, 0),
            period=3,
            start_time=800,
            end_time=845,
            subject="Math",
            class_name="10A",
        )
        start = datetime(2024, 3, 15, 8, 0)
        end = datetime(2024, 3, 15, 12, 0)

        # Filtering is based on period, not start_time/end_time
        assert is_lesson_in_period(lesson, start, end, start_period=1, end_period=6)
