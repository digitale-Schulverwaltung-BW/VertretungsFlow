"""
Unit Tests für app/api/auth.py

Getestet:
- map_wordpress_role()              - WordPress → AbsenzFlow role mapping
- _decode_wordpress_name()          - URL-decode header names
- _update_wordpress_user_fields()   - Smart update logic (nur bei Änderungen)
- _handle_wordpress_proxy_user()    - Create/Update flow (neue vs. bestehende User)
- get_wordpress_proxy_user()        - Secret-Validierung + Auth-Flow
- get_current_user()                - JWT decode → DB lookup → return user
- get_current_active_user()         - is_active check
- require_role()                    - role-based access control factory
- _create_wordpress_user()          - DB persist + audit_log
- _create_ldap_user()               - DB persist from LDAP info + audit_log
- _handle_ldap_proxy_user()         - LDAP auth flow (existing/create/not found)
- read_users_me()                   - /me endpoint
- logout()                          - /logout endpoint
"""

import pytest
from datetime import timedelta
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import quote

from fastapi import HTTPException
import jwt as jose_jwt
from jwt.exceptions import PyJWTError as JWTError

from app.api.auth import (
    _create_ldap_user,
    _create_wordpress_user,
    _decode_wordpress_name,
    _handle_ldap_proxy_user,
    _handle_wordpress_proxy_user,
    _update_wordpress_user_fields,
    create_access_token,
    get_current_active_user,
    get_current_user,
    get_wordpress_proxy_user,
    logout,
    map_wordpress_role,
    read_users_me,
    require_role,
)
from app.models.models import User, UserRole
from app.core.config import settings


def unwrap(func):
    """Bypass @limiter.limit() decorator via __wrapped__."""
    return func.__wrapped__


def make_mock_request():
    req = Mock()
    req.client = Mock()
    req.client.host = "127.0.0.1"
    return req


# ============================================================================
# Helpers & Fixtures
# ============================================================================

TEST_SECRET = "test-secret-abc123-for-unit-tests"


def make_mock_db(existing_user=None):
    """Create mock DB session that returns given user on .query().filter().first()"""
    db = Mock()
    mock_query = Mock()
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = existing_user
    db.query.return_value = mock_query
    return db


def make_mock_user(role=UserRole.TEACHER, is_active=True):
    """Create mock User with sensible defaults"""
    user = Mock(spec=User)
    user.id = 1
    user.username = "max.mustermann"
    user.email = "max@schule.de"
    user.full_name = "Max Mustermann"
    user.first_name = "Max"
    user.last_name = "Mustermann"
    user.role = role
    user.webuntis_teacher_code = "MUS"
    user.is_active = is_active
    return user


# ============================================================================
# Tests: map_wordpress_role()
# ============================================================================


class TestMapWordpressRole:
    """Tests for WordPress → AbsenzFlow role mapping"""

    def test_admin(self):
        assert map_wordpress_role("admin") == UserRole.ADMIN

    def test_teacher(self):
        assert map_wordpress_role("teacher") == UserRole.TEACHER

    def test_dept_head(self):
        assert map_wordpress_role("dept_head") == UserRole.DEPARTMENT_HEAD

    def test_planner(self):
        assert map_wordpress_role("planner") == UserRole.PLANNER

    def test_unknown_role_defaults_to_teacher(self):
        """Unbekannte Rollen (z.B. 'student') fallen auf TEACHER zurück"""
        assert map_wordpress_role("student") == UserRole.TEACHER

    def test_uppercase_normalized(self):
        """Uppercase-Rollen werden korrekt gemappt"""
        assert map_wordpress_role("ADMIN") == UserRole.ADMIN


# ============================================================================
# Tests: _decode_wordpress_name()
# ============================================================================


class TestDecodeWordpressName:
    """Tests for URL-decoding of WordPress header name values"""

    def test_none_returns_none(self):
        assert _decode_wordpress_name(None) is None

    def test_plain_name_unchanged(self):
        assert _decode_wordpress_name("Max Mustermann") == "Max Mustermann"

    def test_url_encoded_umlaut_decoded(self):
        """URL-kodierte Umlaute werden korrekt dekodiert"""
        encoded = quote("Müller")
        assert _decode_wordpress_name(encoded) == "Müller"

    def test_strips_leading_trailing_whitespace(self):
        assert _decode_wordpress_name("  Max  ") == "Max"


# ============================================================================
# Tests: _update_wordpress_user_fields()
# ============================================================================


class TestUpdateWordpressUserFields:
    """Tests for smart update logic – updates only changed fields"""

    def _make_user(self):
        """User-Mock mit Standardwerten für Vergleichstests"""
        user = Mock(spec=User)
        user.email = "max@schule.de"
        user.full_name = "Max Mustermann"
        user.first_name = "Max"
        user.last_name = "Mustermann"
        user.role = UserRole.TEACHER
        user.webuntis_teacher_code = "MUS"
        return user

    def test_no_changes_returns_false_and_empty_details(self):
        """Kein Update nötig wenn alle Felder identisch"""
        user = self._make_user()
        needs_update, details = _update_wordpress_user_fields(
            user,
            email="max@schule.de",
            full_name="Max Mustermann",
            first_name="Max",
            last_name="Mustermann",
            role=UserRole.TEACHER,
            webuntis_code="MUS",
        )
        assert needs_update is False
        assert details == {}

    def test_email_change_detected(self):
        """Geänderte E-Mail → needs_update=True, alte+neue E-Mail in details"""
        user = self._make_user()
        needs_update, details = _update_wordpress_user_fields(
            user,
            email="neu@schule.de",
            full_name="Max Mustermann",
            first_name="Max",
            last_name="Mustermann",
            role=UserRole.TEACHER,
            webuntis_code="MUS",
        )
        assert needs_update is True
        assert details["old_email"] == "max@schule.de"
        assert details["new_email"] == "neu@schule.de"
        assert user.email == "neu@schule.de"

    def test_role_change_detected(self):
        """Geänderte Rolle → needs_update=True, User-Rolle wird aktualisiert"""
        user = self._make_user()
        needs_update, details = _update_wordpress_user_fields(
            user,
            email="max@schule.de",
            full_name="Max Mustermann",
            first_name="Max",
            last_name="Mustermann",
            role=UserRole.ADMIN,
            webuntis_code="MUS",
        )
        assert needs_update is True
        assert details["old_role"] == "teacher"
        assert details["new_role"] == "admin"
        assert user.role == UserRole.ADMIN

    def test_full_name_change_detected(self):
        """Geänderter Anzeigename → needs_update=True"""
        user = self._make_user()
        needs_update, details = _update_wordpress_user_fields(
            user,
            email="max@schule.de",
            full_name="Dr. Max Mustermann",
            first_name="Max",
            last_name="Mustermann",
            role=UserRole.TEACHER,
            webuntis_code="MUS",
        )
        assert needs_update is True
        assert "old_name" in details
        assert "new_name" in details

    def test_webuntis_code_change_detected(self):
        """Geändertes WebUntis-Kürzel → needs_update=True, User wird aktualisiert"""
        user = self._make_user()
        needs_update, details = _update_wordpress_user_fields(
            user,
            email="max@schule.de",
            full_name="Max Mustermann",
            first_name="Max",
            last_name="Mustermann",
            role=UserRole.TEACHER,
            webuntis_code="NEW",
        )
        assert needs_update is True
        assert details["old_webuntis_code"] == "MUS"
        assert details["new_webuntis_code"] == "NEW"
        assert user.webuntis_teacher_code == "NEW"

    def test_first_name_change_detected(self):
        """Geänderter Vorname → needs_update=True (kein Eintrag in details)"""
        user = self._make_user()
        needs_update, _ = _update_wordpress_user_fields(
            user,
            email="max@schule.de",
            full_name="Max Mustermann",
            first_name="Maximilian",
            last_name="Mustermann",
            role=UserRole.TEACHER,
            webuntis_code="MUS",
        )
        assert needs_update is True
        assert user.first_name == "Maximilian"

    def test_last_name_change_detected(self):
        """Geänderter Nachname → needs_update=True, user.last_name aktualisiert"""
        user = self._make_user()
        needs_update, _ = _update_wordpress_user_fields(
            user,
            email="max@schule.de",
            full_name="Max Mustermann",
            first_name="Max",
            last_name="Muster-Mann",
            role=UserRole.TEACHER,
            webuntis_code="MUS",
        )
        assert needs_update is True
        assert user.last_name == "Muster-Mann"

    def test_multiple_changes_all_tracked(self):
        """Email + Rolle gleichzeitig geändert → beide in details"""
        user = self._make_user()
        needs_update, details = _update_wordpress_user_fields(
            user,
            email="neu@schule.de",
            full_name="Max Mustermann",
            first_name="Max",
            last_name="Mustermann",
            role=UserRole.PLANNER,
            webuntis_code="MUS",
        )
        assert needs_update is True
        assert "old_email" in details
        assert "old_role" in details


# ============================================================================
# Tests: _handle_wordpress_proxy_user()
# ============================================================================


class TestHandleWordpressProxyUser:
    """Tests for the WordPress proxy user create/update flow"""

    def test_creates_new_user_when_not_in_db(self):
        """Neuer User wird per _create_wordpress_user angelegt wenn user=None"""
        db = make_mock_db(existing_user=None)
        with patch("app.api.auth._create_wordpress_user") as mock_create:
            mock_create.return_value = make_mock_user()
            result = _handle_wordpress_proxy_user(
                user=None,
                db=db,
                username="new.user",
                email="new@schule.de",
                display_name="New User",
                first_name="New",
                last_name="User",
                role="teacher",
                webuntis_code="NEW",
            )
        mock_create.assert_called_once()
        assert result is not None

    def test_updates_existing_user_when_changed(self):
        """Bestehender User wird committed wenn sich Felder geändert haben"""
        existing_user = make_mock_user()
        db = make_mock_db(existing_user=existing_user)
        with patch("app.api.auth._update_wordpress_user_fields") as mock_update:
            with patch("app.api.auth.audit_log"):
                mock_update.return_value = (True, {"old_email": "old@schule.de"})
                result = _handle_wordpress_proxy_user(
                    user=existing_user,
                    db=db,
                    username="max.mustermann",
                    email="new@schule.de",
                    display_name="Max Mustermann",
                    first_name="Max",
                    last_name="Mustermann",
                    role="teacher",
                    webuntis_code="MUS",
                )
        mock_update.assert_called_once()
        db.commit.assert_called_once()
        assert result is existing_user

    def test_no_db_commit_when_nothing_changed(self):
        """Kein DB-Commit wenn keine Felder geändert wurden"""
        existing_user = make_mock_user()
        db = make_mock_db(existing_user=existing_user)
        with patch("app.api.auth._update_wordpress_user_fields") as mock_update:
            mock_update.return_value = (False, {})
            _handle_wordpress_proxy_user(
                user=existing_user,
                db=db,
                username="max.mustermann",
                email="max@schule.de",
                display_name="Max Mustermann",
                first_name="Max",
                last_name="Mustermann",
                role="teacher",
                webuntis_code="MUS",
            )
        db.commit.assert_not_called()

    def test_url_encoded_names_decoded_before_create(self):
        """URL-kodierte Vor-/Nachnamen werden vor User-Erstellung dekodiert"""
        db = make_mock_db(existing_user=None)
        encoded_first = quote("Jörg")
        encoded_last = quote("Müller")
        with patch("app.api.auth._create_wordpress_user") as mock_create:
            mock_create.return_value = make_mock_user()
            _handle_wordpress_proxy_user(
                user=None,
                db=db,
                username="joerg.mueller",
                email="joerg@schule.de",
                display_name="Jörg Müller",
                first_name=encoded_first,
                last_name=encoded_last,
                role="teacher",
                webuntis_code=None,
            )
        # _create_wordpress_user(db, username, email, full_name, first_name, last_name, ...)
        call_args = mock_create.call_args.args
        assert call_args[4] == "Jörg"  # first_name_decoded
        assert call_args[5] == "Müller"  # last_name_decoded

    def test_full_name_composed_from_first_and_last_name(self):
        """full_name wird aus first_name + last_name zusammengesetzt wenn beide vorhanden"""
        db = make_mock_db(existing_user=None)
        with patch("app.api.auth._create_wordpress_user") as mock_create:
            mock_create.return_value = make_mock_user()
            _handle_wordpress_proxy_user(
                user=None,
                db=db,
                username="joerg.seyfried",
                email="joerg@schule.de",
                display_name="joerg.seyfried",  # WP default: login name
                first_name="Jörg",
                last_name="Seyfried",
                role="teacher",
                webuntis_code=None,
            )
        # _create_wordpress_user(db, username, email, full_name, ...)
        call_args = mock_create.call_args.args
        assert call_args[3] == "Jörg Seyfried"  # full_name = first + last

    def test_full_name_falls_back_to_display_name_when_first_last_missing(self):
        """Fallback auf display_name wenn first_name oder last_name fehlt"""
        db = make_mock_db(existing_user=None)
        with patch("app.api.auth._create_wordpress_user") as mock_create:
            mock_create.return_value = make_mock_user()
            _handle_wordpress_proxy_user(
                user=None,
                db=db,
                username="anna.schmidt",
                email="anna@schule.de",
                display_name="Anna Schmidt",
                first_name=None,
                last_name=None,
                role="teacher",
                webuntis_code=None,
            )
        call_args = mock_create.call_args.args
        assert call_args[3] == "Anna Schmidt"  # full_name = display_name

    def test_webuntis_code_whitespace_stripped(self):
        """Leerzeichen im WebUntis-Kürzel werden vor User-Erstellung entfernt"""
        db = make_mock_db(existing_user=None)
        with patch("app.api.auth._create_wordpress_user") as mock_create:
            mock_create.return_value = make_mock_user()
            _handle_wordpress_proxy_user(
                user=None,
                db=db,
                username="max.mustermann",
                email="max@schule.de",
                display_name="Max Mustermann",
                first_name="Max",
                last_name="Mustermann",
                role="teacher",
                webuntis_code="  MUS  ",
            )
        # _create_wordpress_user(..., webuntis_code) ist das letzte Argument (Index 7)
        call_args = mock_create.call_args.args
        assert call_args[7] == "MUS"  # webuntis_code_clean


# ============================================================================
# Tests: get_wordpress_proxy_user() - Secret-Validierung
# ============================================================================


class TestGetWordpressProxyUser:
    """Tests for the top-level auth dependency: secret validation + routing"""

    @pytest.mark.asyncio
    async def test_missing_secret_raises_401(self):
        """Kein Secret-Header → 401 Not authenticated"""
        db = make_mock_db()
        with pytest.raises(HTTPException) as exc_info:
            await get_wordpress_proxy_user(
                x_wordpress_secret=None,
                x_wordpress_user="testuser",
                x_wordpress_email=None,
                x_wordpress_name=None,
                x_wordpress_first_name=None,
                x_wordpress_last_name=None,
                x_wordpress_role=None,
                x_wordpress_webuntis_code=None,
                db=db,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_missing_username_raises_401(self):
        """Kein Username-Header → 401 Not authenticated"""
        db = make_mock_db()
        with pytest.raises(HTTPException) as exc_info:
            await get_wordpress_proxy_user(
                x_wordpress_secret=TEST_SECRET,
                x_wordpress_user=None,
                x_wordpress_email=None,
                x_wordpress_name=None,
                x_wordpress_first_name=None,
                x_wordpress_last_name=None,
                x_wordpress_role=None,
                x_wordpress_webuntis_code=None,
                db=db,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_wrong_secret_raises_401_with_message(self):
        """Falsches Secret → 401 'Invalid proxy secret'"""
        db = make_mock_db()
        with patch.object(settings, "WORDPRESS_PROXY_SECRET", TEST_SECRET):
            with pytest.raises(HTTPException) as exc_info:
                await get_wordpress_proxy_user(
                    x_wordpress_secret="wrong-secret",
                    x_wordpress_user="testuser",
                    x_wordpress_email=None,
                    x_wordpress_name=None,
                    x_wordpress_first_name=None,
                    x_wordpress_last_name=None,
                    x_wordpress_role=None,
                    x_wordpress_webuntis_code=None,
                    db=db,
                )
        assert exc_info.value.status_code == 401
        assert "Invalid proxy secret" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_inactive_user_raises_400(self):
        """User mit is_active=False → 400 Inactive user"""
        inactive_user = make_mock_user(is_active=False)
        db = make_mock_db()
        with patch.object(settings, "WORDPRESS_PROXY_SECRET", TEST_SECRET):
            with patch.object(settings, "AUTH_MODE", "wordpress"):
                with patch("app.api.auth._handle_wordpress_proxy_user") as mock_handle:
                    mock_handle.return_value = inactive_user
                    with pytest.raises(HTTPException) as exc_info:
                        await get_wordpress_proxy_user(
                            x_wordpress_secret=TEST_SECRET,
                            x_wordpress_user="testuser",
                            x_wordpress_email="test@schule.de",
                            x_wordpress_name="Test User",
                            x_wordpress_first_name="Test",
                            x_wordpress_last_name="User",
                            x_wordpress_role="teacher",
                            x_wordpress_webuntis_code=None,
                            db=db,
                        )
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_request_returns_active_user(self):
        """Korrektes Secret + aktiver User → User-Objekt zurückgegeben"""
        active_user = make_mock_user(is_active=True)
        db = make_mock_db()
        with patch.object(settings, "WORDPRESS_PROXY_SECRET", TEST_SECRET):
            with patch.object(settings, "AUTH_MODE", "wordpress"):
                with patch("app.api.auth._handle_wordpress_proxy_user") as mock_handle:
                    mock_handle.return_value = active_user
                    result = await get_wordpress_proxy_user(
                        x_wordpress_secret=TEST_SECRET,
                        x_wordpress_user="testuser",
                        x_wordpress_email="test@schule.de",
                        x_wordpress_name="Test User",
                        x_wordpress_first_name="Test",
                        x_wordpress_last_name="User",
                        x_wordpress_role="teacher",
                        x_wordpress_webuntis_code=None,
                        db=db,
                    )
        assert result is active_user


# ============================================================================
# Tests: get_current_user() - JWT-Version in auth.py
# ============================================================================


class TestGetCurrentUserJWT:
    """Tests for auth.py JWT-based get_current_user (different from deps.py)"""

    @pytest.mark.asyncio
    async def test_jwt_error_raises_401(self):
        """JWTError during decode → 401"""
        db = make_mock_db()
        with patch("app.api.auth.jwt.decode", side_effect=JWTError("bad token")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="invalid.token", db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_payload_without_sub_raises_401(self):
        """Payload without 'sub' claim → 401"""
        db = make_mock_db()
        with patch("app.api.auth.jwt.decode", return_value={"role": "admin"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="some.token", db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_user_not_in_db_raises_401(self):
        """Valid token but user not in DB → 401"""
        db = make_mock_db(existing_user=None)
        with patch("app.api.auth.jwt.decode", return_value={"sub": "ghost.user"}):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(token="some.token", db=db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_and_user_returns_user(self):
        """Valid token + existing user → user returned"""
        user = make_mock_user()
        db = make_mock_db(existing_user=user)
        with patch("app.api.auth.jwt.decode", return_value={"sub": "max.mustermann"}):
            result = await get_current_user(token="valid.token", db=db)
        assert result is user


# ============================================================================
# Tests: get_current_active_user()
# ============================================================================


class TestGetCurrentActiveUser:
    @pytest.mark.asyncio
    async def test_active_user_returned(self):
        user = make_mock_user(is_active=True)
        result = await get_current_active_user(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_inactive_user_raises_400(self):
        user = make_mock_user(is_active=False)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(current_user=user)
        assert exc_info.value.status_code == 400


# ============================================================================
# Tests: require_role()
# ============================================================================


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_allowed_role_returns_user(self):
        user = make_mock_user(role=UserRole.ADMIN)
        checker = require_role([UserRole.ADMIN, UserRole.PLANNER])
        result = await checker(current_user=user)
        assert result is user

    @pytest.mark.asyncio
    async def test_forbidden_role_raises_403(self):
        user = make_mock_user(role=UserRole.TEACHER)
        checker = require_role([UserRole.ADMIN])
        with pytest.raises(HTTPException) as exc_info:
            await checker(current_user=user)
        assert exc_info.value.status_code == 403


# ============================================================================
# Tests: _create_wordpress_user()
# ============================================================================


class TestCreateWordpressUser:
    def _make_db(self):
        db = Mock()
        db.refresh = Mock()
        return db

    def test_adds_commits_refreshes_and_returns_user(self):
        db = self._make_db()
        with patch("app.api.auth.audit_log"):
            result = _create_wordpress_user(
                db=db,
                username="new.user",
                email="new@schule.de",
                full_name="New User",
                first_name="New",
                last_name="User",
                role=UserRole.TEACHER,
                webuntis_code="NEW",
            )
        db.add.assert_called_once()
        db.commit.assert_called_once()
        db.refresh.assert_called_once()
        assert result is not None

    def test_audit_log_called_with_user_created_action(self):
        db = self._make_db()
        with patch("app.api.auth.audit_log") as mock_audit:
            _create_wordpress_user(
                db=db,
                username="new.user",
                email="new@schule.de",
                full_name="New User",
                first_name=None,
                last_name=None,
                role=UserRole.TEACHER,
                webuntis_code=None,
            )
        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["action"] == "user_created"

    def test_user_has_correct_username_and_role(self):
        db = self._make_db()
        with patch("app.api.auth.audit_log"):
            result = _create_wordpress_user(
                db=db,
                username="anna.schmidt",
                email="anna@schule.de",
                full_name="Anna Schmidt",
                first_name="Anna",
                last_name="Schmidt",
                role=UserRole.DEPARTMENT_HEAD,
                webuntis_code="SCH",
            )
        assert result.username == "anna.schmidt"
        assert result.role == UserRole.DEPARTMENT_HEAD
        assert result.is_active is True


# ============================================================================
# Tests: _create_ldap_user()
# ============================================================================


class TestCreateLdapUser:
    def _make_db(self):
        db = Mock()
        db.refresh = Mock()
        return db

    def test_creates_user_from_ldap_info(self):
        db = self._make_db()
        ldap_info = {"email": "ldap@schule.de", "full_name": "LDAP User"}
        with patch("app.api.auth.audit_log"):
            result = _create_ldap_user(db=db, username="ldap.user", ldap_info=ldap_info)
        assert result.username == "ldap.user"
        assert result.email == "ldap@schule.de"
        assert result.full_name == "LDAP User"
        assert result.role == UserRole.TEACHER
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_falls_back_to_username_when_full_name_missing(self):
        db = self._make_db()
        with patch("app.api.auth.audit_log"):
            result = _create_ldap_user(
                db=db, username="bare.user", ldap_info={"email": "bare@schule.de"}
            )
        assert result.full_name == "bare.user"


# ============================================================================
# Tests: _handle_ldap_proxy_user()
# ============================================================================


class TestHandleLdapProxyUser:
    @pytest.mark.asyncio
    async def test_existing_user_returned_directly(self):
        """If user already in DB, return without LDAP lookup"""
        existing = make_mock_user()
        db = Mock()
        result = await _handle_ldap_proxy_user(
            user=existing, db=db, username="max.mustermann"
        )
        assert result is existing

    @pytest.mark.asyncio
    async def test_ldap_service_none_raises_500(self):
        """ldap_service=None (non-standalone mode) → 500"""
        db = Mock()
        with patch("app.api.auth.ldap_service", None):
            with pytest.raises(HTTPException) as exc_info:
                await _handle_ldap_proxy_user(user=None, db=db, username="ghost.user")
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_user_not_in_ldap_raises_404(self):
        """User exists in secret but not in LDAP → 404"""
        db = Mock()
        mock_ldap = Mock()
        mock_ldap.get_user_info.return_value = None
        with patch("app.api.auth.ldap_service", mock_ldap):
            with pytest.raises(HTTPException) as exc_info:
                await _handle_ldap_proxy_user(user=None, db=db, username="unknown.user")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_ldap_user_found_creates_and_returns(self):
        """LDAP returns info → create user and return"""
        db = Mock()
        db.refresh = Mock()
        ldap_info = {"email": "new@schule.de", "full_name": "New LDAP User"}
        mock_ldap = Mock()
        mock_ldap.get_user_info.return_value = ldap_info
        with patch("app.api.auth.ldap_service", mock_ldap):
            with patch("app.api.auth.audit_log"):
                result = await _handle_ldap_proxy_user(
                    user=None, db=db, username="new.ldap.user"
                )
        assert result.username == "new.ldap.user"
        assert result.email == "new@schule.de"


# ============================================================================
# Tests: get_wordpress_proxy_user() – LDAP Mode
# ============================================================================


class TestGetWordpressProxyUserLdapMode:
    @pytest.mark.asyncio
    async def test_ldap_mode_routes_to_ldap_handler(self):
        """AUTH_MODE != 'wordpress' → _handle_ldap_proxy_user called"""
        active_user = make_mock_user(is_active=True)
        db = make_mock_db()
        with patch.object(settings, "WORDPRESS_PROXY_SECRET", TEST_SECRET):
            with patch.object(settings, "AUTH_MODE", "standalone"):
                with patch(
                    "app.api.auth._handle_ldap_proxy_user",
                    new_callable=lambda: lambda: AsyncMock(return_value=active_user),
                ):
                    with patch(
                        "app.api.auth._handle_ldap_proxy_user",
                        new=AsyncMock(return_value=active_user),
                    ):
                        result = await get_wordpress_proxy_user(
                            x_wordpress_secret=TEST_SECRET,
                            x_wordpress_user="testuser",
                            x_wordpress_email=None,
                            x_wordpress_name=None,
                            x_wordpress_first_name=None,
                            x_wordpress_last_name=None,
                            x_wordpress_role=None,
                            x_wordpress_webuntis_code=None,
                            db=db,
                        )
        assert result is active_user


# ============================================================================
# Tests: read_users_me() and logout() endpoints
# ============================================================================


class TestReadUsersMe:
    @pytest.mark.asyncio
    async def test_returns_current_user(self):
        user = make_mock_user()
        result = await unwrap(read_users_me)(
            request=make_mock_request(), current_user=user
        )
        assert result is user


class TestLogout:
    @pytest.mark.asyncio
    async def test_returns_success_message(self):
        user = make_mock_user()
        result = await unwrap(logout)(request=make_mock_request(), current_user=user)
        assert result == {"message": "Successfully logged out"}


# ============================================================================
# Tests: create_access_token()
# ============================================================================

JWT_TEST_SECRET = "test-secret-key-for-jwt-unit-tests-min32ch"


class TestCreateAccessToken:
    """Tests for JWT token creation defined in auth.py (used by login endpoint)"""

    def test_returns_jwt_string(self):
        """create_access_token returns a non-empty string"""
        with patch.object(settings, "SECRET_KEY", JWT_TEST_SECRET):
            with patch.object(settings, "ALGORITHM", "HS256"):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    token = create_access_token({"sub": "testuser"})
        assert isinstance(token, str)
        assert len(token) > 0

    def test_payload_contains_sub_and_exp(self):
        """Token payload contains 'sub' claim and 'exp' expiry claim"""
        with patch.object(settings, "SECRET_KEY", JWT_TEST_SECRET):
            with patch.object(settings, "ALGORITHM", "HS256"):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    token = create_access_token({"sub": "max.mustermann"})
        payload = jose_jwt.decode(token, JWT_TEST_SECRET, algorithms=["HS256"])
        assert payload["sub"] == "max.mustermann"
        assert "exp" in payload

    def test_custom_expires_delta_overrides_default(self):
        """When expires_delta is provided, it is used instead of settings default"""
        with patch.object(settings, "SECRET_KEY", JWT_TEST_SECRET):
            with patch.object(settings, "ALGORITHM", "HS256"):
                token = create_access_token(
                    {"sub": "testuser"}, expires_delta=timedelta(hours=2)
                )
        assert isinstance(token, str)
        payload = jose_jwt.decode(token, JWT_TEST_SECRET, algorithms=["HS256"])
        assert "exp" in payload
