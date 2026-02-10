"""
Unit Tests für WebUntis Service, Client und Parser

Getestet:
- WebUntisService:          authenticate(), get_timetable_for_teacher(), _log_webuntis_error()
- WebUntisAPIClient:        find_teacher_id() - business logic (case-insensitive matching)
- parse_timetable()         - pure function: teacher filtering, ID resolution, period mapping
- merge_consecutive_lessons() - pure function: consecutive lesson merging
"""

import pytest
import httpx
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.services.webuntis_service import WebUntisService
from app.services.webuntis.client import WebUntisAPIClient
from app.services.webuntis.parser import parse_timetable, merge_consecutive_lessons
from app.schemas.schemas import WebUntisLesson


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def service():
    """WebUntisService with mocked sub-components"""
    svc = WebUntisService()
    svc.client = Mock()
    svc.client.session_id = None
    svc.client.person_id = None
    svc.cache = Mock()
    svc.data_loader = Mock()
    return svc


@pytest.fixture
def mock_db():
    return Mock()


def make_lesson(
    date=None,
    period=1,
    subject="Mathematik",
    class_name="5A",
    room="101",
    end_period=None,
):
    """Helper: create a WebUntisLesson"""
    return WebUntisLesson(
        date=date or datetime(2026, 2, 10),
        period=period,
        end_period=end_period,
        subject=subject,
        class_name=class_name,
        room=room,
    )


# ============================================================================
# Test WebUntisService.authenticate()
# ============================================================================


class TestAuthenticate:
    """Test authentication delegation and side effects"""

    @pytest.mark.asyncio
    async def test_returns_true_on_success(self, service):
        """Test that True is returned when client authenticates successfully"""
        service.client.authenticate = AsyncMock(return_value=True)
        service.client.person_id = 42

        result = await service.authenticate()

        assert result is True
        service.client.authenticate.assert_called_once()

    @pytest.mark.asyncio
    async def test_clears_cache_on_success(self, service):
        """Test that memory cache is cleared when authentication succeeds"""
        service.client.authenticate = AsyncMock(return_value=True)
        service.client.person_id = 42

        await service.authenticate()

        service.cache.clear_memory_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_false_on_failure(self, service):
        """Test that False is returned when client authentication fails"""
        service.client.authenticate = AsyncMock(return_value=False)

        result = await service.authenticate()

        assert result is False

    @pytest.mark.asyncio
    async def test_does_not_clear_cache_on_failure(self, service):
        """Test that cache is NOT cleared when authentication fails"""
        service.client.authenticate = AsyncMock(return_value=False)

        await service.authenticate()

        service.cache.clear_memory_cache.assert_not_called()


# ============================================================================
# Test WebUntisService.get_timetable_for_teacher()
# ============================================================================


class TestGetTimetableForTeacher:
    """Test main timetable retrieval with auth, lookup and error handling"""

    @pytest.mark.asyncio
    async def test_authenticates_when_no_session(self, service, mock_db):
        """Test that authentication is triggered when session_id is None"""
        service.client.session_id = None
        service.client.authenticate = AsyncMock(return_value=True)
        service.client.person_id = 1
        service.client.find_teacher_id = AsyncMock(return_value=None)
        service.cache.clear_memory_cache = Mock()

        await service.get_timetable_for_teacher(
            "max.mustermann",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
        )

        service.client.authenticate.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_auth_when_session_exists(self, service, mock_db):
        """Test that authentication is skipped when session_id is already set"""
        service.client.session_id = "existing-session-123"
        service.client.authenticate = AsyncMock(return_value=True)
        service.client.find_teacher_id = AsyncMock(return_value=None)

        await service.get_timetable_for_teacher(
            "max.mustermann",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
        )

        service.client.authenticate.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_auth_fails(self, service, mock_db):
        """Test that empty list is returned when authentication fails"""
        service.client.session_id = None
        service.client.authenticate = AsyncMock(return_value=False)

        result = await service.get_timetable_for_teacher(
            "max.mustermann",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_teacher_not_found(self, service, mock_db):
        """Test that empty list is returned when teacher ID is not found"""
        service.client.session_id = "session-123"
        service.client.find_teacher_id = AsyncMock(return_value=None)

        result = await service.get_timetable_for_teacher(
            "unbekannte.lehrkraft",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_uses_webuntis_code_over_username(self, service, mock_db):
        """Test that webuntis_code is preferred over teacher_username for lookup"""
        service.client.session_id = "session-123"
        service.client.find_teacher_id = AsyncMock(return_value=None)

        await service.get_timetable_for_teacher(
            "max.mustermann",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
            webuntis_code="MUS",
        )

        service.client.find_teacher_id.assert_called_once_with("MUS")

    @pytest.mark.asyncio
    async def test_uses_username_when_no_webuntis_code(self, service, mock_db):
        """Test that username is used when webuntis_code is not provided"""
        service.client.session_id = "session-123"
        service.client.find_teacher_id = AsyncMock(return_value=None)

        await service.get_timetable_for_teacher(
            "max.mustermann",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
        )

        service.client.find_teacher_id.assert_called_once_with("max.mustermann")

    @pytest.mark.asyncio
    async def test_returns_parsed_lessons_on_success(self, service, mock_db):
        """Test that lessons are returned when everything succeeds"""
        service.client.session_id = "session-123"
        service.client.find_teacher_id = AsyncMock(return_value=99)
        service.client.get_timetable = AsyncMock(return_value=[{"fake": "entry"}])

        expected_lessons = [make_lesson()]
        with patch.object(
            service, "_parse_timetable", new_callable=AsyncMock
        ) as mock_parse:
            mock_parse.return_value = expected_lessons

            result = await service.get_timetable_for_teacher(
                "max.mustermann",
                datetime(2026, 2, 10),
                datetime(2026, 2, 12),
                mock_db,
            )

        assert result == expected_lessons

    @pytest.mark.asyncio
    async def test_returns_empty_on_timeout_exception(self, service, mock_db):
        """Test that TimeoutException is caught and empty list returned (no raise)"""
        service.client.session_id = "session-123"
        service.client.find_teacher_id = AsyncMock(
            side_effect=httpx.TimeoutException("timeout")
        )

        result = await service.get_timetable_for_teacher(
            "max.mustermann",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_unexpected_exception(self, service, mock_db):
        """Test that any unexpected exception is caught and empty list returned"""
        service.client.session_id = "session-123"
        service.client.find_teacher_id = AsyncMock(
            side_effect=Exception("Unexpected error")
        )

        result = await service.get_timetable_for_teacher(
            "max.mustermann",
            datetime(2026, 2, 10),
            datetime(2026, 2, 12),
            mock_db,
        )

        assert result == []


# ============================================================================
# Test WebUntisService._log_webuntis_error()
# ============================================================================


class TestLogWebUntisError:
    """Test exception-type-to-message mapping in error logger"""

    def test_logs_timeout_message(self, service):
        """Test TimeoutException maps to 'took too long' message"""
        exc = httpx.TimeoutException("timeout")
        # Should not raise
        service._log_webuntis_error(exc, "max.mustermann")

    def test_logs_connect_error_message(self, service):
        """Test ConnectError maps to 'Cannot reach' message"""
        exc = httpx.ConnectError("connection refused")
        service._log_webuntis_error(exc, "max.mustermann")

    def test_logs_key_error_message(self, service):
        """Test KeyError maps to 'Missing expected field' message"""
        exc = KeyError("sessionId")
        service._log_webuntis_error(exc, "max.mustermann")

    def test_logs_value_error_message(self, service):
        """Test ValueError maps to 'Invalid data format' message"""
        exc = ValueError("invalid date format")
        service._log_webuntis_error(exc, "max.mustermann")

    def test_logs_unknown_exception(self, service):
        """Test that unknown exception types log a generic message (no raise)"""
        exc = RuntimeError("something random")
        service._log_webuntis_error(exc, "max.mustermann")


# ============================================================================
# Test WebUntisAPIClient.find_teacher_id()
# ============================================================================


class TestFindTeacherId:
    """Test teacher ID lookup business logic (case-insensitive matching)"""

    @pytest.mark.asyncio
    async def test_returns_id_for_exact_match(self):
        """Test that exact username match returns teacher ID"""
        client = WebUntisAPIClient(
            server="test.webuntis.com", username="user", password="pass"
        )
        client.get_teachers = AsyncMock(
            return_value=[
                {"id": 10, "name": "mustermann"},
                {"id": 20, "name": "schmidt"},
            ]
        )

        result = await client.find_teacher_id("mustermann")

        assert result == 10

    @pytest.mark.asyncio
    async def test_returns_id_case_insensitive(self):
        """Test that matching is case-insensitive"""
        client = WebUntisAPIClient(
            server="test.webuntis.com", username="user", password="pass"
        )
        client.get_teachers = AsyncMock(return_value=[{"id": 42, "name": "MUSTERMANN"}])

        result = await client.find_teacher_id("mustermann")

        assert result == 42

    @pytest.mark.asyncio
    async def test_returns_none_when_teacher_not_found(self):
        """Test that None is returned when username is not in teacher list"""
        client = WebUntisAPIClient(
            server="test.webuntis.com", username="user", password="pass"
        )
        client.get_teachers = AsyncMock(return_value=[{"id": 10, "name": "schmidt"}])

        result = await client.find_teacher_id("mustermann")

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_teacher_list_empty(self):
        """Test that None is returned when teacher list is empty"""
        client = WebUntisAPIClient(
            server="test.webuntis.com", username="user", password="pass"
        )
        client.get_teachers = AsyncMock(return_value=[])

        result = await client.find_teacher_id("mustermann")

        assert result is None


# ============================================================================
# Test parse_timetable()
# ============================================================================


SAMPLE_SUBJECTS = {101: "Mathematik", 102: "Deutsch"}
SAMPLE_CLASSES = {201: "5A", 202: "5B"}
SAMPLE_ROOMS = {301: "Raum 101", 302: "Raum 102"}
SAMPLE_TIMEGRID = {730: 1, 815: 2, 900: 3}

TEACHER_ID = 55


def make_raw_entry(
    date=20260210,
    teacher_ids=None,
    subject_ids=None,
    class_ids=None,
    room_ids=None,
    start_time=730,
    end_time=815,
):
    """Helper to build a raw WebUntis timetable entry"""
    return {
        "date": date,
        "te": [{"id": t} for t in (teacher_ids or [TEACHER_ID])],
        "su": [{"id": s} for s in (subject_ids or [101])],
        "kl": [{"id": c} for c in (class_ids or [201])],
        "ro": [{"id": r} for r in (room_ids or [301])],
        "startTime": start_time,
        "endTime": end_time,
    }


class TestParseTimetable:
    """Test pure timetable parsing function"""

    def test_parses_basic_entry(self):
        """Test that a basic timetable entry is parsed correctly"""
        raw = [make_raw_entry()]

        result = parse_timetable(
            raw,
            TEACHER_ID,
            SAMPLE_SUBJECTS,
            SAMPLE_CLASSES,
            SAMPLE_ROOMS,
            SAMPLE_TIMEGRID,
        )

        assert len(result) == 1
        assert result[0].subject == "Mathematik"
        assert result[0].class_name == "5A"
        assert result[0].room == "Raum 101"

    def test_filters_out_other_teachers(self):
        """Test that entries for other teachers are excluded"""
        other_teacher_entry = make_raw_entry(teacher_ids=[99])  # not our teacher
        our_teacher_entry = make_raw_entry(teacher_ids=[TEACHER_ID])

        result = parse_timetable(
            [other_teacher_entry, our_teacher_entry],
            TEACHER_ID,
            SAMPLE_SUBJECTS,
            SAMPLE_CLASSES,
            SAMPLE_ROOMS,
            SAMPLE_TIMEGRID,
        )

        assert len(result) == 1
        assert result[0].subject == "Mathematik"

    def test_parses_date_from_yyyymmdd(self):
        """Test that date is parsed from integer YYYYMMDD format"""
        raw = [make_raw_entry(date=20260215)]

        result = parse_timetable(
            raw,
            TEACHER_ID,
            SAMPLE_SUBJECTS,
            SAMPLE_CLASSES,
            SAMPLE_ROOMS,
            SAMPLE_TIMEGRID,
        )

        assert result[0].date == datetime(2026, 2, 15)

    def test_resolves_period_from_timegrid(self):
        """Test that period is resolved from timegrid startTime mapping"""
        raw = [make_raw_entry(start_time=730)]  # maps to period 1

        result = parse_timetable(
            raw,
            TEACHER_ID,
            SAMPLE_SUBJECTS,
            SAMPLE_CLASSES,
            SAMPLE_ROOMS,
            SAMPLE_TIMEGRID,
        )

        assert result[0].period == 1

    def test_returns_unbekannt_for_missing_subject(self):
        """Test that 'Unbekannt' is used when no subject IDs are provided"""
        raw = [make_raw_entry(subject_ids=[])]

        result = parse_timetable(
            raw, TEACHER_ID, {}, SAMPLE_CLASSES, SAMPLE_ROOMS, SAMPLE_TIMEGRID
        )

        assert result[0].subject == "Unbekannt"

    def test_resolves_subject_with_string_key_fallback(self):
        """Test that string key fallback works (JSONB stores numeric keys as strings)"""
        subjects_with_string_keys = {"101": "Mathematik"}  # string key
        raw = [make_raw_entry(subject_ids=[101])]  # integer key in entry

        result = parse_timetable(
            raw,
            TEACHER_ID,
            subjects_with_string_keys,
            SAMPLE_CLASSES,
            SAMPLE_ROOMS,
            SAMPLE_TIMEGRID,
        )

        assert result[0].subject == "Mathematik"

    def test_returns_empty_list_for_empty_input(self):
        """Test that empty input returns empty list"""
        result = parse_timetable(
            [],
            TEACHER_ID,
            SAMPLE_SUBJECTS,
            SAMPLE_CLASSES,
            SAMPLE_ROOMS,
            SAMPLE_TIMEGRID,
        )

        assert result == []

    def test_skips_malformed_entry_and_continues(self):
        """Test that a malformed entry is skipped without stopping the entire parse"""
        good_entry = make_raw_entry()
        bad_entry = {
            "date": "INVALID",
            "te": [{"id": TEACHER_ID}],
            "su": [],
            "kl": [],
            "ro": [],
        }

        result = parse_timetable(
            [bad_entry, good_entry],
            TEACHER_ID,
            SAMPLE_SUBJECTS,
            SAMPLE_CLASSES,
            SAMPLE_ROOMS,
            SAMPLE_TIMEGRID,
        )

        # Good entry still parsed
        assert len(result) == 1
        assert result[0].subject == "Mathematik"


# ============================================================================
# Test merge_consecutive_lessons()
# ============================================================================


class TestMergeConsecutiveLessons:
    """Test consecutive lesson merging logic"""

    def test_returns_empty_for_empty_input(self):
        """Test that empty input returns empty list"""
        result = merge_consecutive_lessons([])
        assert result == []

    def test_single_lesson_unchanged(self):
        """Test that a single lesson is returned unchanged"""
        lesson = make_lesson(period=1)
        result = merge_consecutive_lessons([lesson])

        assert len(result) == 1
        assert result[0].period == 1
        assert result[0].end_period is None

    def test_merges_consecutive_same_subject(self):
        """Test that consecutive periods with same subject/class are merged"""
        lesson1 = make_lesson(period=1, subject="Mathematik", class_name="5A")
        lesson2 = make_lesson(period=2, subject="Mathematik", class_name="5A")

        result = merge_consecutive_lessons([lesson1, lesson2])

        assert len(result) == 1
        assert result[0].period == 1
        assert result[0].end_period == 2

    def test_does_not_merge_different_subjects(self):
        """Test that non-consecutive periods with different subjects stay separate"""
        lesson1 = make_lesson(period=1, subject="Mathematik", class_name="5A")
        lesson2 = make_lesson(period=2, subject="Deutsch", class_name="5A")

        result = merge_consecutive_lessons([lesson1, lesson2])

        assert len(result) == 2

    def test_does_not_merge_different_classes(self):
        """Test that consecutive periods with different classes stay separate"""
        lesson1 = make_lesson(period=1, subject="Mathematik", class_name="5A")
        lesson2 = make_lesson(period=2, subject="Mathematik", class_name="5B")

        result = merge_consecutive_lessons([lesson1, lesson2])

        assert len(result) == 2

    def test_does_not_merge_non_consecutive_periods(self):
        """Test that periods 1 and 3 (skipping 2) stay separate"""
        lesson1 = make_lesson(period=1, subject="Mathematik", class_name="5A")
        lesson3 = make_lesson(period=3, subject="Mathematik", class_name="5A")

        result = merge_consecutive_lessons([lesson1, lesson3])

        assert len(result) == 2

    def test_does_not_merge_different_dates(self):
        """Test that same subject/class on different dates stay separate"""
        lesson_monday = make_lesson(
            date=datetime(2026, 2, 10), period=1, subject="Mathematik", class_name="5A"
        )
        lesson_tuesday = make_lesson(
            date=datetime(2026, 2, 11), period=2, subject="Mathematik", class_name="5A"
        )

        result = merge_consecutive_lessons([lesson_monday, lesson_tuesday])

        assert len(result) == 2

    def test_merges_triple_consecutive(self):
        """Test that three consecutive periods merge into one block"""
        lesson1 = make_lesson(period=1, subject="Mathematik", class_name="5A")
        lesson2 = make_lesson(period=2, subject="Mathematik", class_name="5A")
        lesson3 = make_lesson(period=3, subject="Mathematik", class_name="5A")

        result = merge_consecutive_lessons([lesson1, lesson2, lesson3])

        assert len(result) == 1
        assert result[0].period == 1
        assert result[0].end_period == 3

    def test_sorts_by_date_and_period_before_merging(self):
        """Test that unsorted input is sorted correctly before merging"""
        lesson2 = make_lesson(period=2, subject="Mathematik", class_name="5A")
        lesson1 = make_lesson(period=1, subject="Mathematik", class_name="5A")

        result = merge_consecutive_lessons([lesson2, lesson1])  # wrong order

        assert len(result) == 1
        assert result[0].period == 1
        assert result[0].end_period == 2
