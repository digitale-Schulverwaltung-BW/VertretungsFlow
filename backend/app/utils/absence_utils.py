"""
Absence Utilities
Pure functions for absence validation and lesson filtering
"""

from datetime import date, datetime, timedelta
from fastapi import HTTPException, status

from app.models.models import UserRole
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


def validate_min_advance(start_date: datetime, min_days: int, role: UserRole) -> None:
    """
    Validates that the absence starts at least min_days calendar days ahead

    Planners and admins are exempt. min_days <= 0 disables the check.

    Args:
        start_date: Start date of the absence
        min_days: Minimum advance notice in calendar days
        role: Role of the user creating the absence

    Raises:
        HTTPException: If the absence starts too soon
    """
    if min_days <= 0 or role in (UserRole.ADMIN, UserRole.PLANNER):
        return

    earliest = date.today() + timedelta(days=min_days)
    if start_date.date() < earliest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Abwesenheiten müssen mindestens {min_days} Tage im Voraus gemeldet "
                "werden. Bei kurzfristigen Meldungen wenden Sie sich bitte "
                "persönlich an das Vertretungsplanungs-Team."
            ),
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

    # For merged lesson blocks, use end_period for overlap checks so that a block
    # starting before start_period is still included when it extends into the range.
    lesson_end = lesson.end_period if lesson.end_period is not None else lesson.period

    # Filter nach Periode
    if start_date.date() == end_date.date():
        # Eintägige Abwesenheit: Block muss den angefragten Bereich überlappen
        return lesson.period <= end_period and lesson_end >= start_period
    elif lesson.date.date() == start_date.date():
        # Erster Tag: Block endet nach oder bei start_period
        return lesson_end >= start_period
    elif lesson.date.date() == end_date.date():
        # Letzter Tag
        return lesson.period <= end_period
    else:
        # Tage dazwischen
        return True


def clip_lesson_to_period(
    lesson: WebUntisLesson,
    start_date: datetime,
    end_date: datetime,
    start_period: int,
    end_period: int,
) -> WebUntisLesson:
    """
    Clips a merged lesson block to the intersection with the requested period range.

    A block spanning periods 1-4 requested from 2-8 becomes period=2, end_period=4.
    Single-period lessons and blocks already within range are returned unchanged.
    start_time/end_time are cleared when the respective boundary is clipped to
    avoid storing times that no longer match the actual periods shown.
    """
    lesson_end = lesson.end_period if lesson.end_period is not None else lesson.period

    new_start = lesson.period
    new_end = lesson_end

    if start_date.date() == end_date.date():
        new_start = max(lesson.period, start_period)
        new_end = min(lesson_end, end_period)
    elif lesson.date.date() == start_date.date():
        new_start = max(lesson.period, start_period)
    elif lesson.date.date() == end_date.date():
        new_end = min(lesson_end, end_period)

    if new_start == lesson.period and new_end == lesson_end:
        return lesson

    return WebUntisLesson(
        date=lesson.date,
        period=new_start,
        end_period=new_end if new_end != new_start else None,
        start_time=lesson.start_time if new_start == lesson.period else None,
        end_time=lesson.end_time if new_end == lesson_end else None,
        subject=lesson.subject,
        class_name=lesson.class_name,
        room=lesson.room,
    )
