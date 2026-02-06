"""
Absence Utilities
Pure functions for absence validation and lesson filtering
"""

from datetime import datetime
from fastapi import HTTPException, status

from app.schemas.schemas import WebUntisLesson


def validate_date_range(
    start_date: datetime, end_date: datetime, start_period: int, end_period: int
) -> None:
    """
    Validates date range and periods

    Args:
        start_date: Start date
        end_date: End date
        start_period: Start period
        end_period: End period

    Raises:
        HTTPException: If validation fails

    Example:
        >>> validate_date_range(
        ...     datetime(2024, 3, 15),
        ...     datetime(2024, 3, 17),
        ...     1, 6
        ... )
        # No exception = valid
    """
    # Validierung: end_date >= start_date
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after or equal to start date",
        )

    # Validierung: end_period >= start_period bei gleichen Tagen
    if start_date.date() == end_date.date():
        if end_period < start_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End period must be after or equal to start period",
            )


def is_lesson_in_period(
    lesson: WebUntisLesson,
    start_date: datetime,
    end_date: datetime,
    start_period: int,
    end_period: int,
) -> bool:
    """
    Checks if lesson is within the specified period

    Args:
        lesson: Lesson to check
        start_date: Start date
        end_date: End date
        start_period: Start period
        end_period: End period

    Returns:
        True if lesson is in period, False otherwise

    Example:
        >>> lesson = WebUntisLesson(date=datetime(2024, 3, 15), period=3, ...)
        >>> is_lesson_in_period(
        ...     lesson,
        ...     datetime(2024, 3, 15),
        ...     datetime(2024, 3, 15),
        ...     1, 6
        ... )
        True
    """
    # Check if lesson is within date range
    if not (start_date.date() <= lesson.date.date() <= end_date.date()):
        return False

    # Filter nach Periode
    if start_date.date() == end_date.date():
        # Eintägige Abwesenheit
        return start_period <= lesson.period <= end_period
    elif lesson.date.date() == start_date.date():
        # Erster Tag
        return lesson.period >= start_period
    elif lesson.date.date() == end_date.date():
        # Letzter Tag
        return lesson.period <= end_period
    else:
        # Tage dazwischen
        return True
