"""
Unit tests for api/deps.py

FastAPI dependency functions for authentication and authorization:
- get_current_user: JWT decode → DB lookup → active check
- get_current_teacher: role guard (teacher/dept_head/planner/admin)
- get_current_department_head: role guard (dept_head/admin)
- get_current_planner: role guard (planner/admin)
- get_current_admin: role guard (admin only)
"""

import pytest
from unittest.mock import Mock, patch

from fastapi import HTTPException

from app.api.deps import (
    get_current_admin,
    get_current_department_head,
    get_current_planner,
    get_current_teacher,
    get_current_user,
)
from app.models.models import UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_mock_credentials(token: str = "valid.jwt.token") -> Mock:
    creds = Mock()
    creds.credentials = token
    return creds


def make_mock_db(user=None) -> Mock:
    """DB mock: query → filter → first."""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.first.return_value = user
    db.query.return_value = q
    return db


def make_mock_user(role: UserRole = UserRole.TEACHER, is_active: bool = True) -> Mock:
    user = Mock()
    user.role = role
    user.is_active = is_active
    user.username = "testuser"
    return user


# ---------------------------------------------------------------------------
# TestGetCurrentUser
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self):
        creds = make_mock_credentials("bad.token")
        db = make_mock_db()

        with patch("app.api.deps.decode_access_token", return_value=None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_payload_without_sub_raises_401(self):
        creds = make_mock_credentials()
        db = make_mock_db()

        with patch("app.api.deps.decode_access_token", return_value={"role": "admin"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_in_db_raises_401(self):
        creds = make_mock_credentials()
        db = make_mock_db(user=None)

        with patch(
            "app.api.deps.decode_access_token",
            return_value={"sub": "ghostuser"},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=db)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self):
        user = make_mock_user(is_active=False)
        creds = make_mock_credentials()
        db = make_mock_db(user=user)

        with patch(
            "app.api.deps.decode_access_token",
            return_value={"sub": "testuser"},
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials=creds, db=db)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_valid_token_and_active_user_returns_user(self):
        user = make_mock_user(is_active=True)
        creds = make_mock_credentials()
        db = make_mock_db(user=user)

        with patch(
            "app.api.deps.decode_access_token",
            return_value={"sub": "testuser"},
        ):
            result = await get_current_user(credentials=creds, db=db)

        assert result is user


# ---------------------------------------------------------------------------
# TestGetCurrentTeacher
# ---------------------------------------------------------------------------


class TestGetCurrentTeacher:
    @pytest.mark.asyncio
    async def test_teacher_role_is_allowed(self):
        user = make_mock_user(role=UserRole.TEACHER)
        result = await get_current_teacher(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_department_head_role_is_allowed(self):
        user = make_mock_user(role=UserRole.DEPARTMENT_HEAD)
        result = await get_current_teacher(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_planner_role_is_allowed(self):
        user = make_mock_user(role=UserRole.PLANNER)
        result = await get_current_teacher(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_admin_role_is_allowed(self):
        user = make_mock_user(role=UserRole.ADMIN)
        result = await get_current_teacher(current_user=user)
        assert result is user


# ---------------------------------------------------------------------------
# TestGetCurrentDepartmentHead
# ---------------------------------------------------------------------------


class TestGetCurrentDepartmentHead:
    @pytest.mark.asyncio
    async def test_department_head_is_allowed(self):
        user = make_mock_user(role=UserRole.DEPARTMENT_HEAD)
        result = await get_current_department_head(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_admin_is_allowed(self):
        user = make_mock_user(role=UserRole.ADMIN)
        result = await get_current_department_head(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_teacher_raises_403(self):
        user = make_mock_user(role=UserRole.TEACHER)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_department_head(current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_planner_raises_403(self):
        user = make_mock_user(role=UserRole.PLANNER)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_department_head(current_user=user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# TestGetCurrentPlanner
# ---------------------------------------------------------------------------


class TestGetCurrentPlanner:
    @pytest.mark.asyncio
    async def test_planner_is_allowed(self):
        user = make_mock_user(role=UserRole.PLANNER)
        result = await get_current_planner(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_admin_is_allowed(self):
        user = make_mock_user(role=UserRole.ADMIN)
        result = await get_current_planner(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_teacher_raises_403(self):
        user = make_mock_user(role=UserRole.TEACHER)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_planner(current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_department_head_raises_403(self):
        user = make_mock_user(role=UserRole.DEPARTMENT_HEAD)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_planner(current_user=user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# TestGetCurrentAdmin
# ---------------------------------------------------------------------------


class TestGetCurrentAdmin:
    @pytest.mark.asyncio
    async def test_admin_is_allowed(self):
        user = make_mock_user(role=UserRole.ADMIN)
        result = await get_current_admin(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_teacher_raises_403(self):
        user = make_mock_user(role=UserRole.TEACHER)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_department_head_raises_403(self):
        user = make_mock_user(role=UserRole.DEPARTMENT_HEAD)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(current_user=user)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_planner_raises_403(self):
        user = make_mock_user(role=UserRole.PLANNER)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_admin(current_user=user)
        assert exc_info.value.status_code == 403
