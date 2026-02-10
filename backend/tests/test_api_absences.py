"""
Unit Tests für app/api/absences.py

Getestet (Route-Logik, nicht Service-Logik):
- create_absence()       - Reine Delegation an absence_service
- list_absences()        - Rollen-basiertes Filtern (Teacher vs. Planner/Admin)
- get_absence()          - 404/403-Checks + Delegation
- update_lesson_notes()  - 404 (Absence+Lesson), 403-Check, DB-Update
- approve_absence()      - 404/403-Checks + Delegation
- complete_absence()     - 403-Check (inkl. Custom-Header) + Delegation
- delete_absence()       - 404/403-Checks + Delegation

Strategie: Direkte Funktionsaufrufe (kein TestClient/HTTP).
Services werden via @patch gemockt – Service-Logik ist in test_absence_service.py.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from fastapi import HTTPException

from app.api.absences import (
    create_absence,
    list_absences,
    get_absence,
    update_lesson_notes,
    approve_absence,
    complete_absence,
    delete_absence,
)
from app.models.models import Absence, AffectedLesson, AbsenceStatus, UserRole


# ============================================================================
# Helpers & Fixtures
# ============================================================================


def make_mock_user(role=UserRole.TEACHER, user_id=1):
    user = Mock()
    user.id = user_id
    user.role = role
    user.is_active = True
    return user


def make_mock_absence(absence_id=1, teacher_id=1, status=AbsenceStatus.SUBMITTED):
    absence = Mock(spec=Absence)
    absence.id = absence_id
    absence.teacher_id = teacher_id
    absence.status = status
    return absence


def make_mock_lesson(lesson_id=10, absence_id=1):
    lesson = Mock(spec=AffectedLesson)
    lesson.id = lesson_id
    lesson.absence_id = absence_id
    lesson.notes = None
    return lesson


def make_mock_db(absence=None):
    """DB mock for simple query().options().filter().first() chains"""
    db = Mock()
    q = Mock()
    q.options.return_value = q
    q.filter.return_value = q
    q.first.return_value = absence
    db.query.return_value = q
    return db


def make_list_mock_db(absences=None):
    """DB mock for query chains with options/filter/order_by/offset/limit/all"""
    db = Mock()
    q = Mock()
    q.options.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.all.return_value = absences or []
    db.query.return_value = q
    return db


def make_two_query_db(absence=None, lesson=None):
    """DB mock returning different query results for Absence vs AffectedLesson"""
    db = Mock()

    absence_q = Mock()
    absence_q.filter.return_value = absence_q
    absence_q.first.return_value = absence

    lesson_q = Mock()
    lesson_q.filter.return_value = lesson_q
    lesson_q.first.return_value = lesson

    def side_effect(model):
        if model is Absence:
            return absence_q
        return lesson_q

    db.query.side_effect = side_effect
    return db


def make_mock_request(dept_heads_can_complete="0"):
    """Mock FastAPI Request mit headers"""
    request = Mock()
    request.headers.get.return_value = dept_heads_can_complete
    return request


# slowapi's @limiter.limit() wraps all route functions and requires a real
# starlette.requests.Request instance. In unit tests we bypass the decorator
# via __wrapped__ (set by functools.wraps) to call the original function directly.
def unwrap(func):
    """Return the original function, bypassing slowapi @limiter.limit() decorator"""
    return func.__wrapped__


@pytest.fixture
def teacher():
    return make_mock_user(role=UserRole.TEACHER, user_id=1)


@pytest.fixture
def planner():
    return make_mock_user(role=UserRole.PLANNER, user_id=2)


@pytest.fixture
def admin():
    return make_mock_user(role=UserRole.ADMIN, user_id=3)


# ============================================================================
# Tests: create_absence()
# ============================================================================


class TestCreateAbsence:
    """create_absence ist eine reine Delegation – korrekte Weiterleitung prüfen"""

    @pytest.mark.asyncio
    async def test_delegates_to_absence_service(self, teacher):
        """Route gibt Ergebnis von absence_service.create_absence zurück"""
        mock_absence_data = Mock()
        mock_result = Mock()
        db = make_mock_db()
        request = make_mock_request()

        with patch(
            "app.api.absences.absence_service.create_absence",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_create:
            result = await unwrap(create_absence)(
                request=request,
                absence=mock_absence_data,
                current_user=teacher,
                db=db,
            )

        mock_create.assert_called_once_with(mock_absence_data, teacher, db)
        assert result is mock_result


# ============================================================================
# Tests: list_absences()
# ============================================================================


class TestListAbsences:
    """list_absences hat Route-eigene Logik: rollen-basiertes Filtern"""

    @pytest.mark.asyncio
    async def test_teacher_filter_applied(self, teacher):
        """Teacher-Query wird nach teacher_id gefiltert"""
        mock_absence = make_mock_absence(teacher_id=teacher.id)
        db = make_list_mock_db(absences=[mock_absence])
        request = make_mock_request()

        result = await unwrap(list_absences)(
            request=request,
            skip=0,
            limit=100,
            status=None,
            current_user=teacher,
            db=db,
        )

        # filter() wurde aufgerufen (für teacher_id-Einschränkung)
        db.query.return_value.options.return_value.filter.assert_called()
        assert result == [mock_absence]

    @pytest.mark.asyncio
    async def test_planner_sees_all_absences(self, planner):
        """Planner bekommt alle Absenzen ohne teacher_id-Filter"""
        mock_absences = [
            make_mock_absence(absence_id=1, teacher_id=1),
            make_mock_absence(absence_id=2, teacher_id=2),
        ]
        db = make_list_mock_db(absences=mock_absences)
        request = make_mock_request()

        result = await unwrap(list_absences)(
            request=request,
            skip=0,
            limit=100,
            status=None,
            current_user=planner,
            db=db,
        )

        assert result == mock_absences

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_absences(self, teacher):
        """Leere Liste wenn keine Absenzen vorhanden"""
        db = make_list_mock_db(absences=[])
        request = make_mock_request()

        result = await unwrap(list_absences)(
            request=request,
            skip=0,
            limit=100,
            status=None,
            current_user=teacher,
            db=db,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_status_filter_applied_when_provided(self, planner):
        """Status-Parameter führt zu weiterem filter()-Aufruf"""
        mock_absence = make_mock_absence(status=AbsenceStatus.SUBMITTED)
        db = make_list_mock_db(absences=[mock_absence])
        request = make_mock_request()

        result = await unwrap(list_absences)(
            request=request,
            skip=0,
            limit=100,
            status=AbsenceStatus.SUBMITTED,
            current_user=planner,
            db=db,
        )

        db.query.return_value.options.return_value.filter.assert_called()
        assert result == [mock_absence]


# ============================================================================
# Tests: get_absence()
# ============================================================================


class TestGetAbsence:
    """get_absence: 404-Check, Permission-Check, Rückgabe"""

    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self, teacher):
        """404 wenn Absenz nicht in DB"""
        db = make_mock_db(absence=None)
        request = make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(get_absence)(
                request=request,
                absence_id=999,
                current_user=teacher,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """403 wenn can_view_absence=False"""
        mock_absence = make_mock_absence()
        db = make_mock_db(absence=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_view_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(get_absence)(
                    request=request,
                    absence_id=1,
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_returns_absence_when_authorized(self, teacher):
        """Absenz wird zurückgegeben wenn Berechtigung vorhanden"""
        mock_absence = make_mock_absence()
        db = make_mock_db(absence=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_view_absence",
            return_value=True,
        ):
            result = await unwrap(get_absence)(
                request=request,
                absence_id=1,
                current_user=teacher,
                db=db,
            )

        assert result is mock_absence


# ============================================================================
# Tests: update_lesson_notes()
# ============================================================================


class TestUpdateLessonNotes:
    """update_lesson_notes: 2x 404-Check, 403-Check, DB-Update"""

    @pytest.mark.asyncio
    async def test_raises_404_when_absence_not_found(self, teacher):
        """404 wenn Absenz nicht gefunden"""
        db = make_two_query_db(absence=None, lesson=None)
        request = make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(update_lesson_notes)(
                request=request,
                absence_id=999,
                lesson_id=1,
                lesson_update=Mock(notes="neue Notiz"),
                current_user=teacher,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """403 wenn can_edit_absence=False"""
        mock_absence = make_mock_absence()
        db = make_two_query_db(absence=mock_absence, lesson=None)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_edit_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(update_lesson_notes)(
                    request=request,
                    absence_id=1,
                    lesson_id=1,
                    lesson_update=Mock(notes="neue Notiz"),
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_raises_404_when_lesson_not_found(self, planner):
        """404 wenn Stunde nicht in DB"""
        mock_absence = make_mock_absence()
        db = make_two_query_db(absence=mock_absence, lesson=None)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_edit_absence",
            return_value=True,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(update_lesson_notes)(
                    request=request,
                    absence_id=1,
                    lesson_id=999,
                    lesson_update=Mock(notes="neue Notiz"),
                    current_user=planner,
                    db=db,
                )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_updates_notes_and_commits(self, planner):
        """Notizen werden gesetzt und DB committed"""
        mock_absence = make_mock_absence()
        mock_lesson = make_mock_lesson()
        db = make_two_query_db(absence=mock_absence, lesson=mock_lesson)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_edit_absence",
            return_value=True,
        ):
            result = await unwrap(update_lesson_notes)(
                request=request,
                absence_id=1,
                lesson_id=10,
                lesson_update=Mock(notes="neue Notiz"),
                current_user=planner,
                db=db,
            )

        assert mock_lesson.notes == "neue Notiz"
        db.commit.assert_called_once()
        assert result is mock_lesson

    @pytest.mark.asyncio
    async def test_notes_unchanged_when_update_is_none(self, planner):
        """Bestehende Notiz bleibt erhalten wenn lesson_update.notes=None"""
        mock_absence = make_mock_absence()
        mock_lesson = make_mock_lesson()
        mock_lesson.notes = "bestehende Notiz"
        db = make_two_query_db(absence=mock_absence, lesson=mock_lesson)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_edit_absence",
            return_value=True,
        ):
            await unwrap(update_lesson_notes)(
                request=request,
                absence_id=1,
                lesson_id=10,
                lesson_update=Mock(notes=None),
                current_user=planner,
                db=db,
            )

        assert mock_lesson.notes == "bestehende Notiz"


# ============================================================================
# Tests: approve_absence()
# ============================================================================


class TestApproveAbsence:
    """approve_absence: 404/403-Checks + Delegation an Service"""

    @pytest.mark.asyncio
    async def test_raises_404_when_absence_not_found(self, planner):
        """404 wenn Absenz nicht in DB"""
        db = make_mock_db(absence=None)
        request = make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(approve_absence)(
                request=request,
                absence_id=999,
                approval=Mock(approved=True),
                current_user=planner,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """Lehrkraft darf nicht genehmigen → 403"""
        mock_absence = make_mock_absence()
        db = make_mock_db(absence=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_approve_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(approve_absence)(
                    request=request,
                    absence_id=1,
                    approval=Mock(approved=True),
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delegates_to_service_and_returns_message(self, planner):
        """Bei Berechtigung → absence_service.approve_absence aufgerufen"""
        mock_absence = make_mock_absence()
        db = make_mock_db(absence=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_approve_absence",
            return_value=True,
        ):
            with patch(
                "app.api.absences.absence_service.approve_absence",
                new_callable=AsyncMock,
                return_value="Absenz genehmigt",
            ) as mock_approve:
                result = await unwrap(approve_absence)(
                    request=request,
                    absence_id=1,
                    approval=Mock(approved=True),
                    current_user=planner,
                    db=db,
                )

        mock_approve.assert_called_once()
        assert result == {"message": "Absenz genehmigt"}


# ============================================================================
# Tests: complete_absence()
# ============================================================================


class TestCompleteAbsence:
    """complete_absence: 403-Check (inkl. Custom-Header-Auswertung) + Delegation"""

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """Lehrkraft ohne Berechtigung → 403"""
        request = make_mock_request(dept_heads_can_complete="0")
        db = make_mock_db()

        with patch(
            "app.api.absences.permission_service.can_complete_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(complete_absence)(
                    request=request,
                    absence_id=1,
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_header_value_passed_to_permission_check(self, planner):
        """X-WordPress-Dept-Heads-Can-Complete=1 → can_complete_absence(user, True)"""
        request = make_mock_request(dept_heads_can_complete="1")
        db = make_mock_db()

        with patch(
            "app.api.absences.permission_service.can_complete_absence",
            return_value=True,
        ) as mock_perm:
            with patch(
                "app.api.absences.absence_service.complete_absence",
                new_callable=AsyncMock,
                return_value="Erledigt",
            ):
                await unwrap(complete_absence)(
                    request=request,
                    absence_id=1,
                    current_user=planner,
                    db=db,
                )

        mock_perm.assert_called_once_with(planner, True)

    @pytest.mark.asyncio
    async def test_delegates_to_service_and_returns_message(self, planner):
        """Bei Berechtigung → absence_service.complete_absence aufgerufen"""
        request = make_mock_request(dept_heads_can_complete="0")
        db = make_mock_db()

        with patch(
            "app.api.absences.permission_service.can_complete_absence",
            return_value=True,
        ):
            with patch(
                "app.api.absences.absence_service.complete_absence",
                new_callable=AsyncMock,
                return_value="Absenz erledigt",
            ) as mock_complete:
                result = await unwrap(complete_absence)(
                    request=request,
                    absence_id=1,
                    current_user=planner,
                    db=db,
                )

        mock_complete.assert_called_once()
        assert result == {"message": "Absenz erledigt"}


# ============================================================================
# Tests: delete_absence()
# ============================================================================


class TestDeleteAbsence:
    """delete_absence: 404/403-Checks + Delegation"""

    @pytest.mark.asyncio
    async def test_raises_404_when_absence_not_found(self, teacher):
        """404 wenn Absenz nicht in DB"""
        db = make_mock_db(absence=None)
        request = make_mock_request()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(delete_absence)(
                request=request,
                absence_id=999,
                current_user=teacher,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_403_when_no_permission(self, teacher):
        """can_delete_absence=False → 403"""
        mock_absence = make_mock_absence()
        db = make_mock_db(absence=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_delete_absence",
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await unwrap(delete_absence)(
                    request=request,
                    absence_id=1,
                    current_user=teacher,
                    db=db,
                )

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_delegates_to_service_and_returns_message(self, teacher):
        """Bei Berechtigung → absence_service.delete_absence aufgerufen"""
        mock_absence = make_mock_absence()
        db = make_mock_db(absence=mock_absence)
        request = make_mock_request()

        with patch(
            "app.api.absences.permission_service.can_delete_absence",
            return_value=True,
        ):
            with patch(
                "app.api.absences.absence_service.delete_absence",
                return_value="Absenz gelöscht",
            ) as mock_delete:
                result = await unwrap(delete_absence)(
                    request=request,
                    absence_id=1,
                    current_user=teacher,
                    db=db,
                )

        mock_delete.assert_called_once_with(1, db)
        assert result == {"message": "Absenz gelöscht"}
