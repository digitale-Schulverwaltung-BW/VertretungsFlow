"""
Unit tests for api/admin.py

8 endpoints (all have @limiter.limit → unwrap needed):
- GET  /admin/users                    → list_users
- POST /admin/users/{id}/role          → assign_role
- GET  /admin/dashboard                → get_dashboard_stats
- GET  /admin/absences/pending         → list_pending_absences
- GET  /admin/absences/by-date         → list_absences_by_date
- POST /admin/webuntis-cache/refresh   → refresh_webuntis_cache
- GET  /admin/webuntis-cache/status    → get_cache_status
- POST /admin/cleanup-old-absences     → trigger_cleanup
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from fastapi import HTTPException

from app.api.admin import (
    assign_role,
    get_cache_status,
    get_dashboard_stats,
    list_absences_by_date,
    list_pending_absences,
    list_users,
    refresh_webuntis_cache,
    trigger_cleanup,
)
from app.models.models import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def unwrap(func):
    """Bypass @limiter.limit() decorator (functools.wraps → __wrapped__)."""
    return func.__wrapped__


def make_mock_request():
    req = Mock()
    req.client = Mock()
    req.client.host = "127.0.0.1"
    return req


def make_mock_user(username: str = "admin", role: UserRole = UserRole.ADMIN) -> Mock:
    user = Mock()
    user.username = username
    user.role = role
    return user


def make_list_db(items=None) -> Mock:
    """DB mock for offset → limit → all chains."""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.all.return_value = items or []
    db.query.return_value = q
    return db


def make_single_db(user=None) -> Mock:
    """DB mock for filter → first chains."""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.first.return_value = user
    db.query.return_value = q
    return db


def make_count_db(counts: list) -> Mock:
    """DB mock where each scalar() call returns the next value from counts."""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.join.return_value = q
    q.scalar.side_effect = counts
    db.query.return_value = q
    return db


# ---------------------------------------------------------------------------
# TestListUsers
# ---------------------------------------------------------------------------


class TestListUsers:
    @pytest.mark.asyncio
    async def test_returns_users_from_db(self):
        users = [make_mock_user("alice"), make_mock_user("bob")]
        db = make_list_db(items=users)
        current_user = make_mock_user()

        result = await unwrap(list_users)(
            request=make_mock_request(),
            skip=0,
            limit=100,
            current_user=current_user,
            db=db,
        )

        assert result == users

    @pytest.mark.asyncio
    async def test_applies_skip_and_limit(self):
        db = make_list_db(items=[])
        current_user = make_mock_user()

        await unwrap(list_users)(
            request=make_mock_request(),
            skip=10,
            limit=5,
            current_user=current_user,
            db=db,
        )

        db.query.return_value.offset.assert_called_once_with(10)
        db.query.return_value.offset.return_value.limit.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# TestAssignRole
# ---------------------------------------------------------------------------


class TestAssignRole:
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self):
        db = make_single_db(user=None)
        current_user = make_mock_user()
        role_assignment = Mock()
        role_assignment.role = UserRole.TEACHER

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(assign_role)(
                request=make_mock_request(),
                user_id=99,
                role_assignment=role_assignment,
                current_user=current_user,
                db=db,
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sets_role_commits_and_refreshes(self):
        user = make_mock_user(username="teacher_user", role=UserRole.TEACHER)
        db = make_single_db(user=user)
        current_user = make_mock_user()
        role_assignment = Mock()
        role_assignment.role = UserRole.DEPARTMENT_HEAD

        result = await unwrap(assign_role)(
            request=make_mock_request(),
            user_id=1,
            role_assignment=role_assignment,
            current_user=current_user,
            db=db,
        )

        assert user.role == UserRole.DEPARTMENT_HEAD
        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(user)
        assert result is user


# ---------------------------------------------------------------------------
# TestGetDashboardStats
# ---------------------------------------------------------------------------


class TestGetDashboardStats:
    @pytest.mark.asyncio
    async def test_returns_correct_counts_from_db(self):
        # scalar() called 4 times: pending, approved, completed, total_lessons
        db = make_count_db(counts=[5, 3, 12, 47])
        current_user = make_mock_user()

        result = await unwrap(get_dashboard_stats)(
            request=make_mock_request(), current_user=current_user, db=db
        )

        assert result.pending_absences == 5
        assert result.approved_absences == 3
        assert result.completed_absences == 12
        assert result.total_affected_lessons == 47

    @pytest.mark.asyncio
    async def test_zero_counts_when_db_returns_zeros(self):
        db = make_count_db(counts=[0, 0, 0, 0])
        current_user = make_mock_user()

        result = await unwrap(get_dashboard_stats)(
            request=make_mock_request(), current_user=current_user, db=db
        )

        assert result.pending_absences == 0
        assert result.total_affected_lessons == 0


# ---------------------------------------------------------------------------
# TestListPendingAbsences
# ---------------------------------------------------------------------------


class TestListPendingAbsences:
    @pytest.mark.asyncio
    async def test_returns_absences_from_db(self):
        absences = [Mock(), Mock()]
        db = make_list_db(items=absences)
        current_user = make_mock_user()

        result = await unwrap(list_pending_absences)(
            request=make_mock_request(),
            skip=0,
            limit=100,
            current_user=current_user,
            db=db,
        )

        assert result == absences

    @pytest.mark.asyncio
    async def test_applies_ordering_by_start_date(self):
        db = make_list_db(items=[])
        current_user = make_mock_user()

        await unwrap(list_pending_absences)(
            request=make_mock_request(),
            skip=0,
            limit=100,
            current_user=current_user,
            db=db,
        )

        db.query.return_value.filter.return_value.order_by.assert_called_once()


# ---------------------------------------------------------------------------
# TestListAbsencesByDate
# ---------------------------------------------------------------------------


class TestListAbsencesByDate:
    @pytest.mark.asyncio
    async def test_invalid_from_date_raises_400(self):
        db = make_list_db()
        current_user = make_mock_user()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(list_absences_by_date)(
                request=make_mock_request(),
                from_date="not-a-date",
                to_date="2026-01-31",
                current_user=current_user,
                db=db,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_to_date_raises_400(self):
        db = make_list_db()
        current_user = make_mock_user()

        with pytest.raises(HTTPException) as exc_info:
            await unwrap(list_absences_by_date)(
                request=make_mock_request(),
                from_date="2026-01-01",
                to_date="31/01/2026",  # wrong format
                current_user=current_user,
                db=db,
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_dates_return_filtered_absences(self):
        absences = [Mock()]
        db = make_list_db(items=absences)
        current_user = make_mock_user()

        result = await unwrap(list_absences_by_date)(
            request=make_mock_request(),
            from_date="2026-01-01",
            to_date="2026-01-31",
            current_user=current_user,
            db=db,
        )

        assert result == absences


# ---------------------------------------------------------------------------
# TestRefreshWebuntisCache
# ---------------------------------------------------------------------------


class TestRefreshWebuntisCache:
    def _make_mock_service(self):
        svc = Mock()
        svc._subjects_cache = None
        svc._classes_cache = None
        svc._rooms_cache = None
        svc._timegrid_cache = None
        return svc

    @pytest.mark.asyncio
    async def test_clears_db_cache_and_commits(self):
        db = Mock()
        q = Mock()
        db.query.return_value = q
        current_user = make_mock_user()

        # The function does `from app.services.webuntis import webuntis_service`
        # at call-time, so patch the module attribute before the call.
        with patch("app.services.webuntis.webuntis_service", self._make_mock_service()):
            await unwrap(refresh_webuntis_cache)(
                request=make_mock_request(), current_user=current_user, db=db
            )

        q.delete.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_message_and_timestamp(self):
        db = Mock()
        db.query.return_value = Mock()
        current_user = make_mock_user()

        with patch("app.services.webuntis.webuntis_service", self._make_mock_service()):
            result = await unwrap(refresh_webuntis_cache)(
                request=make_mock_request(), current_user=current_user, db=db
            )

        assert "message" in result
        assert "timestamp" in result


# ---------------------------------------------------------------------------
# TestGetCacheStatus
# ---------------------------------------------------------------------------


class TestGetCacheStatus:
    def _make_mock_service(self, **kwargs):
        svc = Mock()
        svc._subjects_cache = kwargs.get("subjects", None)
        svc._classes_cache = kwargs.get("classes", None)
        svc._rooms_cache = kwargs.get("rooms", None)
        svc._timegrid_cache = kwargs.get("timegrid", None)
        return svc

    @pytest.mark.asyncio
    async def test_returns_in_memory_cache_flags(self):
        db = Mock()
        q = Mock()
        q.all.return_value = []
        db.query.return_value = q
        current_user = make_mock_user()

        with patch(
            "app.services.webuntis.webuntis_service",
            self._make_mock_service(subjects=["data"], rooms=None),
        ):
            result = await unwrap(get_cache_status)(
                request=make_mock_request(), current_user=current_user, db=db
            )

        assert "in_memory_cache" in result
        assert result["in_memory_cache"]["subjects"] is True  # not None
        assert result["in_memory_cache"]["rooms"] is False  # None

    @pytest.mark.asyncio
    async def test_returns_cached_keys_list(self):
        entry = Mock()
        entry.cache_key = "teachers_20260101"
        entry.created_at = datetime(2026, 1, 1, 10, 0, 0)
        entry.expires_at = None
        entry.cache_data = {"items": [1, 2, 3]}

        db = Mock()
        q = Mock()
        q.all.return_value = [entry]
        db.query.return_value = q
        current_user = make_mock_user()

        with patch("app.services.webuntis.webuntis_service", self._make_mock_service()):
            result = await unwrap(get_cache_status)(
                request=make_mock_request(), current_user=current_user, db=db
            )

        assert len(result["cached_keys"]) == 1
        assert result["cached_keys"][0]["key"] == "teachers_20260101"


# ---------------------------------------------------------------------------
# TestTriggerCleanup
# ---------------------------------------------------------------------------


class TestTriggerCleanup:
    @pytest.mark.asyncio
    async def test_delegates_to_absence_service_and_returns_result(self):
        db = Mock()
        current_user = make_mock_user(username="admin_user")
        mock_cleanup_result = {"deleted": 5, "details": "5 absences removed"}

        mock_service = Mock()
        mock_service.cleanup_old_absences.return_value = mock_cleanup_result

        with patch("app.services.absence_service.absence_service", mock_service):
            result = await unwrap(trigger_cleanup)(
                request=make_mock_request(), current_user=current_user, db=db
            )

        assert result["result"] == mock_cleanup_result
        assert result["triggered_by"] == "admin_user"
        assert "timestamp" in result
