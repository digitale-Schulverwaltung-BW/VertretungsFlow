"""
Unit tests for core/security.py

Pure crypto/JWT functions:
- verify_password / get_password_hash
- create_access_token
- decode_access_token
"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)

TEST_SECRET = "test-secret-key-for-unit-tests"
TEST_ALGO = "HS256"


# ---------------------------------------------------------------------------
# TestVerifyPassword
# ---------------------------------------------------------------------------


class TestVerifyPassword:
    def test_correct_password_returns_true(self):
        # Unit test: verify_password delegates to bcrypt.checkpw
        with patch("app.core.security.bcrypt") as mock_bcrypt:
            mock_bcrypt.checkpw.return_value = True
            result = verify_password("mypassword", "$2b$12$fakehash")

        assert result is True
        mock_bcrypt.checkpw.assert_called_once_with(b"mypassword", b"$2b$12$fakehash")

    def test_wrong_password_returns_false(self):
        with patch("app.core.security.bcrypt") as mock_bcrypt:
            mock_bcrypt.checkpw.return_value = False
            result = verify_password("wrongpassword", "$2b$12$fakehash")

        assert result is False


# ---------------------------------------------------------------------------
# TestGetPasswordHash
# ---------------------------------------------------------------------------


class TestGetPasswordHash:
    def test_delegates_to_bcrypt(self):
        fake_salt = b"$2b$12$fakesalt"
        fake_hash = b"$2b$12$fakehashedvalue"
        with patch("app.core.security.bcrypt") as mock_bcrypt:
            mock_bcrypt.gensalt.return_value = fake_salt
            mock_bcrypt.hashpw.return_value = fake_hash
            result = get_password_hash("secret123")

        assert result == "$2b$12$fakehashedvalue"
        mock_bcrypt.gensalt.assert_called_once()
        mock_bcrypt.hashpw.assert_called_once_with(b"secret123", fake_salt)

    def test_returns_string(self):
        with patch("app.core.security.bcrypt") as mock_bcrypt:
            mock_bcrypt.gensalt.return_value = b"$2b$12$salt"
            mock_bcrypt.hashpw.return_value = b"$2b$12$somebcrypthash"
            result = get_password_hash("anypassword")

        assert isinstance(result, str)
        assert result == "$2b$12$somebcrypthash"


# ---------------------------------------------------------------------------
# TestCreateAccessToken
# ---------------------------------------------------------------------------


class TestCreateAccessToken:
    def test_returns_jwt_string(self):
        with patch.object(settings, "SECRET_KEY", TEST_SECRET):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    token = create_access_token({"sub": "user1"})

        assert isinstance(token, str)
        assert token.count(".") == 2  # valid JWT has two dots

    def test_payload_subject_preserved(self):
        with patch.object(settings, "SECRET_KEY", TEST_SECRET):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    token = create_access_token({"sub": "testuser"})

        payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGO])
        assert payload["sub"] == "testuser"

    def test_token_contains_expiry(self):
        with patch.object(settings, "SECRET_KEY", TEST_SECRET):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    token = create_access_token({"sub": "u"})

        payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGO])
        assert "exp" in payload

    def test_custom_expires_delta_is_used(self):
        with patch.object(settings, "SECRET_KEY", TEST_SECRET):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                before = datetime.utcnow()
                token = create_access_token(
                    {"sub": "u"}, expires_delta=timedelta(minutes=5)
                )
                after = datetime.utcnow()

        payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGO])
        exp = datetime.utcfromtimestamp(payload["exp"])
        assert exp > before + timedelta(minutes=4)
        assert exp < after + timedelta(minutes=6)

    def test_default_expiry_uses_settings_value(self):
        with patch.object(settings, "SECRET_KEY", TEST_SECRET):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 60):
                    before = datetime.utcnow()
                    token = create_access_token({"sub": "u"})
                    after = datetime.utcnow()

        payload = jwt.decode(token, TEST_SECRET, algorithms=[TEST_ALGO])
        exp = datetime.utcfromtimestamp(payload["exp"])
        assert exp > before + timedelta(minutes=59)
        assert exp < after + timedelta(minutes=61)


# ---------------------------------------------------------------------------
# TestDecodeAccessToken
# ---------------------------------------------------------------------------


class TestDecodeAccessToken:
    def test_valid_token_returns_payload(self):
        with patch.object(settings, "SECRET_KEY", TEST_SECRET):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    token = create_access_token({"sub": "user42"})
                    result = decode_access_token(token)

        assert result is not None
        assert result["sub"] == "user42"

    def test_invalid_token_string_returns_none(self):
        with patch.object(settings, "SECRET_KEY", TEST_SECRET):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                result = decode_access_token("not.a.jwt")

        assert result is None

    def test_token_signed_with_wrong_key_returns_none(self):
        with patch.object(settings, "SECRET_KEY", "key-a"):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                with patch.object(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 30):
                    token = create_access_token({"sub": "u"})

        with patch.object(settings, "SECRET_KEY", "key-b"):
            with patch.object(settings, "ALGORITHM", TEST_ALGO):
                result = decode_access_token(token)

        assert result is None
