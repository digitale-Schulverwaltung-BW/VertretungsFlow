"""
Unit tests for core/config.py

_parse_cors_origins:
- String → split on comma, strip whitespace
- List → pass through unchanged

_validate_secret_key:
- Default value → returns error string
- Custom value → returns None

_validate_wordpress_proxy_secret:
- wordpress mode + default secret → returns error string
- wordpress mode + custom secret → returns None
- standalone mode → returns None (no check)

_validate_database_password:
- URL contains 'changeme' → returns error string
- URL with secure password → returns None

_validate_debug_mode:
- DEBUG=True + ENVIRONMENT=production → returns warning string
- DEBUG=True + non-production → returns None
- DEBUG=False + production → returns None

_validate_secret_key_length:
- Key shorter than 32 chars → returns error string
- Key with 32+ chars → returns None

_validate_cors_localhost:
- production + localhost in origins → returns error string
- production + only proper origins → returns None
- non-production → returns None always

_validate_cors_wildcard:
- production + wildcard '*' → returns error string
- production + no wildcard → returns None
- non-production → returns None

_validate_cors_empty:
- production + empty origins → returns warning string
- production + valid origins → returns None
- non-production → returns None

validate_production_secrets:
- All valid → no exception raised
- One error → ValueError raised with error details
- Multiple errors → single ValueError with all details combined
"""

import pytest
from unittest.mock import Mock, patch

from app.core.config import (
    Settings,
    _parse_cors_origins,
    _validate_cors_empty,
    _validate_cors_localhost,
    _validate_cors_wildcard,
    _validate_database_password,
    _validate_debug_mode,
    _validate_secret_key,
    _validate_secret_key_length,
    _validate_wordpress_proxy_secret,
    validate_production_secrets,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_settings(**overrides) -> Mock:
    """
    Returns a Mock with sensible secure defaults for Settings attributes.
    Override specific attributes to test validation edge cases.
    """
    defaults = {
        "SECRET_KEY": "a" * 64,  # 64 chars, not default
        "WORDPRESS_PROXY_SECRET": "custom-secure-secret-for-tests",
        "AUTH_MODE": "wordpress",
        "DATABASE_URL": "postgresql://user:secure_pw@localhost:5432/db",
        "DEBUG": False,
        "CORS_ORIGINS": ["https://example.com"],
    }
    defaults.update(overrides)
    mock = Mock(spec=Settings)
    for key, value in defaults.items():
        setattr(mock, key, value)
    return mock


# ---------------------------------------------------------------------------
# TestParseCorsOrigins
# ---------------------------------------------------------------------------


class TestParseCorsOrigins:
    def test_list_passed_through_unchanged(self):
        origins = ["http://localhost:3000", "https://example.com"]
        result = _parse_cors_origins(origins)
        assert result == origins

    def test_comma_separated_string_is_split(self):
        result = _parse_cors_origins("http://localhost:3000,https://example.com")
        assert result == ["http://localhost:3000", "https://example.com"]

    def test_whitespace_around_origins_is_stripped(self):
        result = _parse_cors_origins("  http://a.com , http://b.com  ")
        assert result == ["http://a.com", "http://b.com"]

    def test_single_origin_string_returns_single_element_list(self):
        result = _parse_cors_origins("https://example.com")
        assert result == ["https://example.com"]


# ---------------------------------------------------------------------------
# TestValidateSecretKey
# ---------------------------------------------------------------------------


class TestValidateSecretKey:
    def test_default_value_returns_error_message(self):
        settings = make_settings(SECRET_KEY="your-secret-key-change-in-production")
        result = _validate_secret_key(settings)
        assert result is not None
        assert "SECRET_KEY" in result

    def test_custom_value_returns_none(self):
        settings = make_settings(SECRET_KEY="my-very-own-secure-secret-32-chars")
        result = _validate_secret_key(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateWordpressProxySecret
# ---------------------------------------------------------------------------


class TestValidateWordpressProxySecret:
    def test_wordpress_mode_with_default_secret_returns_error(self):
        settings = make_settings(
            AUTH_MODE="wordpress",
            WORDPRESS_PROXY_SECRET="change-this-shared-secret-in-production",
        )
        result = _validate_wordpress_proxy_secret(settings)
        assert result is not None
        assert "WORDPRESS_PROXY_SECRET" in result

    def test_wordpress_mode_with_custom_secret_returns_none(self):
        settings = make_settings(
            AUTH_MODE="wordpress",
            WORDPRESS_PROXY_SECRET="my-custom-secure-secret",
        )
        result = _validate_wordpress_proxy_secret(settings)
        assert result is None

    def test_standalone_mode_skips_check_returns_none(self):
        settings = make_settings(
            AUTH_MODE="standalone",
            WORDPRESS_PROXY_SECRET="change-this-shared-secret-in-production",
        )
        result = _validate_wordpress_proxy_secret(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateDatabasePassword
# ---------------------------------------------------------------------------


class TestValidateDatabasePassword:
    def test_changeme_in_url_returns_error(self):
        settings = make_settings(
            DATABASE_URL="postgresql://user:changeme@localhost:5432/db"
        )
        result = _validate_database_password(settings)
        assert result is not None
        assert "DATABASE_URL" in result

    def test_changeme_uppercase_also_detected(self):
        settings = make_settings(
            DATABASE_URL="postgresql://user:CHANGEME@localhost:5432/db"
        )
        result = _validate_database_password(settings)
        assert result is not None

    def test_secure_password_returns_none(self):
        settings = make_settings(
            DATABASE_URL="postgresql://user:secure_pw_123@localhost:5432/db"
        )
        result = _validate_database_password(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateDebugMode
# ---------------------------------------------------------------------------


class TestValidateDebugMode:
    def test_debug_true_in_production_returns_warning(self):
        settings = make_settings(DEBUG=True)
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_debug_mode(settings)
        assert result is not None
        assert "DEBUG" in result

    def test_debug_true_non_production_returns_none(self):
        settings = make_settings(DEBUG=True)
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            result = _validate_debug_mode(settings)
        assert result is None

    def test_debug_false_in_production_returns_none(self):
        settings = make_settings(DEBUG=False)
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_debug_mode(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateSecretKeyLength
# ---------------------------------------------------------------------------


class TestValidateSecretKeyLength:
    def test_key_shorter_than_32_chars_returns_error(self):
        settings = make_settings(SECRET_KEY="short-key")
        result = _validate_secret_key_length(settings)
        assert result is not None
        assert "SECRET_KEY" in result

    def test_key_exactly_32_chars_returns_none(self):
        settings = make_settings(SECRET_KEY="a" * 32)
        result = _validate_secret_key_length(settings)
        assert result is None

    def test_key_longer_than_32_chars_returns_none(self):
        settings = make_settings(SECRET_KEY="a" * 64)
        result = _validate_secret_key_length(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateCorsLocalhost
# ---------------------------------------------------------------------------


class TestValidateCorsLocalhost:
    def test_non_production_always_returns_none(self):
        settings = make_settings(CORS_ORIGINS=["http://localhost:3000"])
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            result = _validate_cors_localhost(settings)
        assert result is None

    def test_production_with_localhost_returns_error(self):
        settings = make_settings(CORS_ORIGINS=["http://localhost:3000"])
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_cors_localhost(settings)
        assert result is not None
        assert "localhost" in result

    def test_production_with_127001_returns_error(self):
        settings = make_settings(CORS_ORIGINS=["http://127.0.0.1:8080"])
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_cors_localhost(settings)
        assert result is not None

    def test_production_with_proper_origin_returns_none(self):
        settings = make_settings(CORS_ORIGINS=["https://example.com"])
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_cors_localhost(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateCorsWildcard
# ---------------------------------------------------------------------------


class TestValidateCorsWildcard:
    def test_non_production_returns_none(self):
        settings = make_settings(CORS_ORIGINS=["*"])
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            result = _validate_cors_wildcard(settings)
        assert result is None

    def test_production_with_wildcard_returns_error(self):
        settings = make_settings(CORS_ORIGINS=["*"])
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_cors_wildcard(settings)
        assert result is not None
        assert "*" in result or "wildcard" in result.lower()

    def test_production_without_wildcard_returns_none(self):
        settings = make_settings(CORS_ORIGINS=["https://example.com"])
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_cors_wildcard(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateCorsEmpty
# ---------------------------------------------------------------------------


class TestValidateCorsEmpty:
    def test_non_production_returns_none(self):
        settings = make_settings(CORS_ORIGINS=[])
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}):
            result = _validate_cors_empty(settings)
        assert result is None

    def test_production_with_empty_origins_returns_warning(self):
        settings = make_settings(CORS_ORIGINS=[])
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_cors_empty(settings)
        assert result is not None
        assert "CORS" in result

    def test_production_with_valid_origins_returns_none(self):
        settings = make_settings(CORS_ORIGINS=["https://example.com"])
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}):
            result = _validate_cors_empty(settings)
        assert result is None


# ---------------------------------------------------------------------------
# TestValidateProductionSecrets
# ---------------------------------------------------------------------------


class TestValidateProductionSecrets:
    def test_all_secure_settings_raises_no_exception(self):
        settings = make_settings()
        # Should not raise
        validate_production_secrets(settings)

    def test_default_secret_key_raises_value_error(self):
        settings = make_settings(SECRET_KEY="your-secret-key-change-in-production")
        with pytest.raises(ValueError) as exc_info:
            validate_production_secrets(settings)
        assert "SECRET_KEY" in str(exc_info.value)

    def test_multiple_errors_all_included_in_single_exception(self):
        settings = make_settings(
            SECRET_KEY="your-secret-key-change-in-production",
            DATABASE_URL="postgresql://user:changeme@localhost:5432/db",
        )
        with pytest.raises(ValueError) as exc_info:
            validate_production_secrets(settings)
        error_msg = str(exc_info.value)
        assert "SECRET_KEY" in error_msg
        assert "DATABASE_URL" in error_msg

    def test_error_message_contains_startup_aborted_header(self):
        settings = make_settings(SECRET_KEY="your-secret-key-change-in-production")
        with pytest.raises(ValueError) as exc_info:
            validate_production_secrets(settings)
        assert "STARTUP ABORTED" in str(exc_info.value)
