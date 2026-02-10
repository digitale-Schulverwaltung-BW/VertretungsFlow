"""
Unit tests for api/users.py

Four endpoints (no @limiter.limit, so no unwrap needed):
- GET  /users          → list_users          (admin only)
- GET  /users/{id}     → get_user
- PATCH /users/{id}    → update_user         (admin only)
- GET  /users/search/{username} → search_user_by_username (admin only)
"""

import pytest
from unittest.mock import Mock

from fastapi import HTTPException

from app.api.users import get_user, list_users, search_user_by_username, update_user
from app.models.models import UserRole


def make_mock_user(user_id=1, role=UserRole.TEACHER, username="testuser"):
    user = Mock()
    user.id = user_id
    user.username = username
    user.role = role
    return user


def make_list_mock_db(users=None):
    """DB mock for list_users: supports query→filter→offset→limit→all chain."""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.offset.return_value = q
    q.limit.return_value = q
    q.all.return_value = users or []
    db.query.return_value = q
    return db


def make_single_mock_db(user=None):
    """DB mock for single-user lookups: query→filter→first."""
    db = Mock()
    q = Mock()
    q.filter.return_value = q
    q.first.return_value = user
    db.query.return_value = q
    return db


# ---------------------------------------------------------------------------
# TestListUsers
# ---------------------------------------------------------------------------


class TestListUsers:
    @pytest.mark.asyncio
    async def test_returns_all_users_without_filter(self):
        users = [make_mock_user(1), make_mock_user(2)]
        db = make_list_mock_db(users=users)
        admin = make_mock_user(role=UserRole.ADMIN)

        result = await list_users(
            skip=0, limit=100, role=None, db=db, current_user=admin
        )

        assert result == users

    @pytest.mark.asyncio
    async def test_filter_applied_when_role_provided(self):
        db = make_list_mock_db(users=[])
        admin = make_mock_user(role=UserRole.ADMIN)

        await list_users(
            skip=0, limit=100, role=UserRole.TEACHER, db=db, current_user=admin
        )

        # filter() must have been called (role != None branch)
        db.query.return_value.filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_filter_when_role_is_none(self):
        db = make_list_mock_db(users=[])
        admin = make_mock_user(role=UserRole.ADMIN)

        await list_users(skip=0, limit=100, role=None, db=db, current_user=admin)

        db.query.return_value.filter.assert_not_called()


# ---------------------------------------------------------------------------
# TestGetUser
# ---------------------------------------------------------------------------


class TestGetUser:
    @pytest.mark.asyncio
    async def test_non_admin_viewing_other_profile_raises_403(self):
        db = make_single_mock_db()
        teacher = make_mock_user(user_id=1, role=UserRole.TEACHER)

        with pytest.raises(HTTPException) as exc_info:
            await get_user(user_id=99, db=db, current_user=teacher)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self):
        db = make_single_mock_db(user=None)
        # Admin may look up anyone, but user doesn't exist
        admin = make_mock_user(user_id=1, role=UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            await get_user(user_id=99, db=db, current_user=admin)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_user_can_view_own_profile(self):
        target = make_mock_user(user_id=5, role=UserRole.TEACHER)
        db = make_single_mock_db(user=target)
        # Same user_id → allowed
        requester = make_mock_user(user_id=5, role=UserRole.TEACHER)

        result = await get_user(user_id=5, db=db, current_user=requester)

        assert result == target

    @pytest.mark.asyncio
    async def test_admin_can_view_any_profile(self):
        target = make_mock_user(user_id=7, role=UserRole.TEACHER)
        db = make_single_mock_db(user=target)
        admin = make_mock_user(user_id=1, role=UserRole.ADMIN)

        result = await get_user(user_id=7, db=db, current_user=admin)

        assert result == target


# ---------------------------------------------------------------------------
# TestUpdateUser
# ---------------------------------------------------------------------------


class TestUpdateUser:
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self):
        db = make_single_mock_db(user=None)
        admin = make_mock_user(role=UserRole.ADMIN)
        user_data = Mock()
        user_data.dict.return_value = {}

        with pytest.raises(HTTPException) as exc_info:
            await update_user(
                user_id=99, user_data=user_data, db=db, current_user=admin
            )

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_updates_fields_on_user_object(self):
        user = make_mock_user(user_id=3)
        db = make_single_mock_db(user=user)
        admin = make_mock_user(role=UserRole.ADMIN)
        user_data = Mock()
        user_data.dict.return_value = {
            "email": "new@example.com",
            "username": "newname",
        }

        await update_user(user_id=3, user_data=user_data, db=db, current_user=admin)

        assert user.email == "new@example.com"
        assert user.username == "newname"

    @pytest.mark.asyncio
    async def test_commit_and_refresh_called(self):
        user = make_mock_user(user_id=3)
        db = make_single_mock_db(user=user)
        admin = make_mock_user(role=UserRole.ADMIN)
        user_data = Mock()
        user_data.dict.return_value = {}

        await update_user(user_id=3, user_data=user_data, db=db, current_user=admin)

        db.commit.assert_called_once()
        db.refresh.assert_called_once_with(user)


# ---------------------------------------------------------------------------
# TestSearchUserByUsername
# ---------------------------------------------------------------------------


class TestSearchUserByUsername:
    @pytest.mark.asyncio
    async def test_user_not_found_raises_404(self):
        db = make_single_mock_db(user=None)
        admin = make_mock_user(role=UserRole.ADMIN)

        with pytest.raises(HTTPException) as exc_info:
            await search_user_by_username(username="ghost", db=db, current_user=admin)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_matching_user(self):
        user = make_mock_user(username="jdoe")
        db = make_single_mock_db(user=user)
        admin = make_mock_user(role=UserRole.ADMIN)

        result = await search_user_by_username(
            username="jdoe", db=db, current_user=admin
        )

        assert result == user
