"""
Konfiguration für AbsenzFlow
Lädt Umgebungsvariablen aus .env
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Union
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application Settings"""

    # Application
    APP_NAME: str = "AbsenzFlow"
    FRONTEND_URL: str = (
        "http://localhost:3000"  # WordPress page with [absenzflow] shortcode
    )
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Database
    DATABASE_URL: str = "postgresql://absenzflow:changeme@localhost:5432/absenzflow"

    # LDAP Configuration
    LDAP_SERVER: str = "ldap.schule.local"
    LDAP_PORT: int = 389
    LDAP_BASE_DN: str = "dc=schule,dc=local"
    LDAP_BIND_DN: str = "cn=absenzflow,ou=services,dc=schule,dc=local"
    LDAP_BIND_PASSWORD: str = ""
    LDAP_USE_SSL: bool = False

    # WebUntis API
    WEBUNTIS_USERNAME: str = ""
    WEBUNTIS_PASSWORD: str = ""
    WEBUNTIS_SERVER: str = "neilo.webuntis.com"

    # SMTP Configuration
    SMTP_HOST: str = "smtp.schule.local"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "absenzflow@schule.de"
    SMTP_USE_TLS: bool = True

    # WebUntis Cache Configuration
    WEBUNTIS_CACHE_TTL_HOURS: int = 168  # 7 Tage (7 * 24h)
    WEBUNTIS_CACHE_ENABLED: bool = True

    # File Upload Configuration
    # Default: backend/uploads (außerhalb webroot, im Projekt-Tree)
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "uploads")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # JWT Token
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 Stunden
    ALGORITHM: str = "HS256"

    # Authentication Mode
    AUTH_MODE: str = "wordpress"  # "wordpress" oder "standalone"

    # WordPress Proxy Authentication
    WORDPRESS_PROXY_SECRET: str = "change-this-shared-secret-in-production"

    # Absence Auto-Deletion Configuration
    ABSENCE_RETENTION_DAYS: int = 90

    # Mindestvorlauf für neue Absenzmeldungen in Kalendertagen (0 = deaktiviert)
    # Gilt nicht für Planer/Admins
    ABSENCE_MIN_ADVANCE_DAYS: int = 0
    ABSENCE_AUTO_DELETE_ENABLED: bool = True

    # Notification Configuration
    NOTIFY_DEPT_HEADS_ON_SUBMISSION: bool = True

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


def _parse_cors_origins(cors_origins: Union[List[str], str]) -> List[str]:
    """
    Parse CORS_ORIGINS from string or list format

    Args:
        cors_origins: CORS origins as list or comma-separated string

    Returns:
        List of origins
    """
    if isinstance(cors_origins, str):
        return [origin.strip() for origin in cors_origins.split(",")]
    return cors_origins


def _validate_secret_key(settings_instance: Settings) -> Union[str, None]:
    """
    Validate SECRET_KEY is not default value

    Args:
        settings_instance: Settings to validate

    Returns:
        Error message if invalid, None if valid
    """
    if settings_instance.SECRET_KEY == "your-secret-key-change-in-production":
        return (
            "❌ SECRET_KEY is still set to default value!\n"
            "   Generate a secure secret: openssl rand -hex 32\n"
            "   Set it in .env: SECRET_KEY=<generated-secret>"
        )
    return None


def _validate_wordpress_proxy_secret(settings_instance: Settings) -> Union[str, None]:
    """
    Validate WORDPRESS_PROXY_SECRET (only in WordPress auth mode)

    Args:
        settings_instance: Settings to validate

    Returns:
        Error message if invalid, None if valid
    """
    if settings_instance.AUTH_MODE == "wordpress":
        if (
            settings_instance.WORDPRESS_PROXY_SECRET
            == "change-this-shared-secret-in-production"
        ):
            return (
                "❌ WORDPRESS_PROXY_SECRET is still set to default value!\n"
                "   Generate a secure secret: openssl rand -hex 32\n"
                "   Set it in .env: WORDPRESS_PROXY_SECRET=<generated-secret>\n"
                "   IMPORTANT: Also update this secret in WordPress Admin settings!"
            )
    return None


def _validate_database_password(settings_instance: Settings) -> Union[str, None]:
    """
    Validate DATABASE_URL doesn't contain default password

    Args:
        settings_instance: Settings to validate

    Returns:
        Error message if invalid, None if valid
    """
    if "changeme" in settings_instance.DATABASE_URL.lower():
        return (
            "❌ DATABASE_URL contains default password 'changeme'!\n"
            "   Set a secure password in .env: DATABASE_URL=postgresql://user:secure_password@host/db"
        )
    return None


def _validate_debug_mode(settings_instance: Settings) -> Union[str, None]:
    """
    Warn if DEBUG mode is enabled in production

    Args:
        settings_instance: Settings to validate

    Returns:
        Warning message if DEBUG=true in production, None otherwise
    """
    if settings_instance.DEBUG and os.getenv("ENVIRONMENT", "").lower() == "production":
        return (
            "⚠️  DEBUG mode is enabled in PRODUCTION environment!\n"
            "   Set DEBUG=false in .env for production deployment"
        )
    return None


def _validate_secret_key_length(settings_instance: Settings) -> Union[str, None]:
    """
    Validate SECRET_KEY is long enough (minimum 32 chars)

    Args:
        settings_instance: Settings to validate

    Returns:
        Error message if invalid, None if valid
    """
    if len(settings_instance.SECRET_KEY) < 32:
        return (
            "❌ SECRET_KEY is too short (minimum 32 characters)!\n"
            "   Generate a secure secret: openssl rand -hex 32"
        )
    return None


def _validate_cors_localhost(settings_instance: Settings) -> Union[str, None]:
    """
    Validate CORS doesn't contain localhost in production

    Args:
        settings_instance: Settings to validate

    Returns:
        Error message if invalid, None if valid
    """
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
    if not is_production:
        return None

    origins_list = _parse_cors_origins(settings_instance.CORS_ORIGINS)

    # Check for localhost origins in production
    localhost_origins = [
        origin
        for origin in origins_list
        if "localhost" in origin.lower() or "127.0.0.1" in origin
    ]
    if localhost_origins:
        return (
            "❌ CORS_ORIGINS contains localhost URLs in PRODUCTION!\n"
            f"   Found: {', '.join(localhost_origins)}\n"
            "   Set CORS_ORIGINS to production domains only in .env:\n"
            "   CORS_ORIGINS=https://your-domain.com"
        )
    return None


def _validate_cors_wildcard(settings_instance: Settings) -> Union[str, None]:
    """
    Validate CORS doesn't contain wildcard in production

    Args:
        settings_instance: Settings to validate

    Returns:
        Error message if invalid, None if valid
    """
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
    if not is_production:
        return None

    origins_list = _parse_cors_origins(settings_instance.CORS_ORIGINS)

    # Check for wildcard origin in production
    if "*" in origins_list:
        return (
            "❌ CORS_ORIGINS contains wildcard '*' in PRODUCTION!\n"
            "   This allows requests from ANY domain - major security risk!\n"
            "   Set CORS_ORIGINS to specific production domains only"
        )
    return None


def _validate_cors_empty(settings_instance: Settings) -> Union[str, None]:
    """
    Warn if CORS is empty in production (might be intentional)

    Args:
        settings_instance: Settings to validate

    Returns:
        Warning message if CORS is empty, None otherwise
    """
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
    if not is_production:
        return None

    origins_list = _parse_cors_origins(settings_instance.CORS_ORIGINS)

    # Warn if CORS is empty in production
    if not origins_list or origins_list == [""]:
        return (
            "⚠️  CORS_ORIGINS is empty in PRODUCTION!\n"
            "   This will block all cross-origin requests.\n"
            "   If using WordPress integration, set:\n"
            "   CORS_ORIGINS=https://your-wordpress-domain.com"
        )
    return None


def validate_production_secrets(settings_instance: Settings) -> None:
    """
    Validates that production secrets have been changed from defaults.
    Called at application startup to fail-fast if insecure defaults are detected.

    Args:
        settings_instance: Settings instance to validate

    Raises:
        ValueError: If any default/insecure secrets are detected
    """
    # Run all validators
    validators = [
        _validate_secret_key,
        _validate_wordpress_proxy_secret,
        _validate_database_password,
        _validate_debug_mode,
        _validate_secret_key_length,
        _validate_cors_localhost,
        _validate_cors_wildcard,
        _validate_cors_empty,
    ]

    errors = []
    for validator in validators:
        error = validator(settings_instance)
        if error:
            errors.append(error)

    # If any errors found, raise exception with all details
    if errors:
        error_message = (
            "\n\n" + "=" * 70 + "\n"
            "🚨 SECURITY CONFIGURATION ERROR - STARTUP ABORTED 🚨\n"
            + "=" * 70
            + "\n\n"
            + "\n\n".join(errors)
            + "\n\n"
            + "=" * 70
            + "\n"
            "Fix these issues in your .env file before starting the application.\n"
            "See .env.example for reference.\n" + "=" * 70 + "\n"
        )
        raise ValueError(error_message)


# Globale Settings-Instanz
settings = Settings()

# Validate secrets at startup (can be disabled with SKIP_SECURITY_VALIDATION=true)
if not os.getenv("SKIP_SECURITY_VALIDATION", "").lower() == "true":
    validate_production_secrets(settings)
