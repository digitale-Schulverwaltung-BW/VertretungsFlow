"""
Unit Tests für app/api/webuntis.py

Getestet (Route-Logik):
- fetch_lessons_from_webuntis() - Validierung, WebUntis-Abruf, Perioden-Filterung

Die Route hat echte Filterlogik:
1. validate_date_range()              - Delegiert an Utils (kann 400 werfen)
2. webuntis_service.get_timetable()   - Holt alle Stunden im Zeitraum
3. is_lesson_in_period()              - Filtert auf angegebene Perioden
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from fastapi import HTTPException

from app.api.webuntis import fetch_lessons_from_webuntis
from app.models.models import UserRole


# ============================================================================
# Helpers & Fixtures
# ============================================================================


def make_mock_user(username="max.mustermann", webuntis_code="MUS"):
    user = Mock()
    user.id = 1
    user.username = username
    user.webuntis_teacher_code = webuntis_code
    user.role = UserRole.TEACHER
    return user


def make_fetch_request(start_date=None, end_date=None, start_period=1, end_period=6):
    """Mock für FetchLessonsRequest mit sinnvollen Standardwerten"""
    req = Mock()
    req.start_date = start_date or datetime(2026, 2, 10, 0, 0)
    req.end_date = end_date or datetime(2026, 2, 10, 0, 0)
    req.start_period = start_period
    req.end_period = end_period
    return req


def make_mock_lesson(period=2):
    lesson = Mock()
    lesson.period = period
    lesson.date = datetime(2026, 2, 10, 0, 0)
    return lesson


def make_mock_db():
    return Mock()


def unwrap(func):
    """Bypass slowapi @limiter.limit() decorator (nutzt functools.wraps)"""
    return func.__wrapped__


@pytest.fixture
def teacher():
    return make_mock_user()


# ============================================================================
# Tests: fetch_lessons_from_webuntis()
# ============================================================================


class TestFetchLessonsFromWebuntis:
    """fetch_lessons_from_webuntis: Validierung → WebUntis → Perioden-Filterung"""

    @pytest.mark.asyncio
    async def test_raises_400_when_date_range_invalid(self, teacher):
        """HTTPException von validate_date_range wird weitergereicht"""
        db = make_mock_db()
        fetch_req = make_fetch_request()

        with patch(
            "app.api.webuntis.validate_date_range",
            side_effect=HTTPException(status_code=400, detail="Invalid date range"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(fetch_lessons_from_webuntis)(
                    request=Mock(),
                    fetch_request=fetch_req,
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_webuntis_has_no_lessons(self, teacher):
        """Leere Liste wenn WebUntis keine Stunden zurückgibt"""
        db = make_mock_db()
        fetch_req = make_fetch_request()

        with patch("app.api.webuntis.validate_date_range"):
            with patch(
                "app.api.webuntis.webuntis_service.get_timetable_for_teacher",
                new_callable=AsyncMock,
                return_value=[],
            ):
                result = await unwrap(fetch_lessons_from_webuntis)(
                    request=Mock(),
                    fetch_request=fetch_req,
                    current_user=teacher,
                    db=db,
                )

        assert result == []

    @pytest.mark.asyncio
    async def test_filters_out_lessons_not_in_period(self, teacher):
        """Stunden außerhalb der Perioden werden herausgefiltert"""
        db = make_mock_db()
        fetch_req = make_fetch_request(start_period=1, end_period=6)
        lessons = [make_mock_lesson(period=2), make_mock_lesson(period=5)]

        # Erste Stunde passt, zweite nicht
        with patch("app.api.webuntis.validate_date_range"):
            with patch(
                "app.api.webuntis.webuntis_service.get_timetable_for_teacher",
                new_callable=AsyncMock,
                return_value=lessons,
            ):
                with patch(
                    "app.api.webuntis.is_lesson_in_period",
                    side_effect=[True, False],
                ):
                    result = await unwrap(fetch_lessons_from_webuntis)(
                        request=Mock(),
                        fetch_request=fetch_req,
                        current_user=teacher,
                        db=db,
                    )

        assert result == [lessons[0]]

    @pytest.mark.asyncio
    async def test_returns_all_lessons_when_all_match_period(self, teacher):
        """Alle Stunden zurückgegeben wenn alle Perioden-Check bestehen"""
        db = make_mock_db()
        fetch_req = make_fetch_request()
        lessons = [
            make_mock_lesson(period=1),
            make_mock_lesson(period=3),
            make_mock_lesson(period=5),
        ]

        with patch("app.api.webuntis.validate_date_range"):
            with patch(
                "app.api.webuntis.webuntis_service.get_timetable_for_teacher",
                new_callable=AsyncMock,
                return_value=lessons,
            ):
                with patch(
                    "app.api.webuntis.is_lesson_in_period",
                    return_value=True,
                ):
                    result = await unwrap(fetch_lessons_from_webuntis)(
                        request=Mock(),
                        fetch_request=fetch_req,
                        current_user=teacher,
                        db=db,
                    )

        assert result == lessons

    @pytest.mark.asyncio
    async def test_passes_username_and_webuntis_code_to_service(self, teacher):
        """Korrekte User-Parameter werden an webuntis_service übergeben"""
        db = make_mock_db()
        fetch_req = make_fetch_request()

        with patch("app.api.webuntis.validate_date_range"):
            with patch(
                "app.api.webuntis.webuntis_service.get_timetable_for_teacher",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_timetable:
                await unwrap(fetch_lessons_from_webuntis)(
                    request=Mock(),
                    fetch_request=fetch_req,
                    current_user=teacher,
                    db=db,
                )

        mock_timetable.assert_called_once_with(
            teacher.username,
            fetch_req.start_date,
            fetch_req.end_date,
            db=db,
            webuntis_code=teacher.webuntis_teacher_code,
        )
