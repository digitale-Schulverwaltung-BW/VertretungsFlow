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
    API_URL: str = "http://localhost:8000"
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
    WEBUNTIS_SCHOOL: str = ""
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

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


def validate_production_secrets(settings_instance: Settings) -> None:
    """
    Validates that production secrets have been changed from defaults.
    Called at application startup to fail-fast if insecure defaults are detected.

    Args:
        settings_instance: Settings instance to validate

    Raises:
        ValueError: If any default/insecure secrets are detected
    """
    errors = []

    # Check SECRET_KEY
    if settings_instance.SECRET_KEY == "your-secret-key-change-in-production":
        errors.append(
            "❌ SECRET_KEY is still set to default value!\n"
            "   Generate a secure secret: openssl rand -hex 32\n"
            "   Set it in .env: SECRET_KEY=<generated-secret>"
        )

    # Check WORDPRESS_PROXY_SECRET (only if WordPress auth mode)
    if settings_instance.AUTH_MODE == "wordpress":
        if (
            settings_instance.WORDPRESS_PROXY_SECRET
            == "change-this-shared-secret-in-production"
        ):
            errors.append(
                "❌ WORDPRESS_PROXY_SECRET is still set to default value!\n"
                "   Generate a secure secret: openssl rand -hex 32\n"
                "   Set it in .env: WORDPRESS_PROXY_SECRET=<generated-secret>\n"
                "   IMPORTANT: Also update this secret in WordPress Admin settings!"
            )

    # Check DATABASE_URL for default password
    if "changeme" in settings_instance.DATABASE_URL.lower():
        errors.append(
            "❌ DATABASE_URL contains default password 'changeme'!\n"
            "   Set a secure password in .env: DATABASE_URL=postgresql://user:secure_password@host/db"
        )

    # Warning for DEBUG mode in production
    if settings_instance.DEBUG and os.getenv("ENVIRONMENT", "").lower() == "production":
        errors.append(
            "⚠️  DEBUG mode is enabled in PRODUCTION environment!\n"
            "   Set DEBUG=false in .env for production deployment"
        )

    # Check if SECRET_KEY is too short (less than 32 chars)
    if len(settings_instance.SECRET_KEY) < 32:
        errors.append(
            "❌ SECRET_KEY is too short (minimum 32 characters)!\n"
            "   Generate a secure secret: openssl rand -hex 32"
        )

    # Check CORS configuration in production
    is_production = os.getenv("ENVIRONMENT", "").lower() == "production"
    if is_production:
        cors_origins = settings_instance.CORS_ORIGINS

        # Convert to list if string
        if isinstance(cors_origins, str):
            origins_list = [origin.strip() for origin in cors_origins.split(",")]
        else:
            origins_list = cors_origins

        # Check for localhost origins in production
        localhost_origins = [
            origin
            for origin in origins_list
            if "localhost" in origin.lower() or "127.0.0.1" in origin
        ]
        if localhost_origins:
            errors.append(
                "❌ CORS_ORIGINS contains localhost URLs in PRODUCTION!\n"
                f"   Found: {', '.join(localhost_origins)}\n"
                "   Set CORS_ORIGINS to production domains only in .env:\n"
                "   CORS_ORIGINS=https://your-domain.com"
            )

        # Check for wildcard origin in production
        if "*" in origins_list:
            errors.append(
                "❌ CORS_ORIGINS contains wildcard '*' in PRODUCTION!\n"
                "   This allows requests from ANY domain - major security risk!\n"
                "   Set CORS_ORIGINS to specific production domains only"
            )

        # Warn if CORS is empty in production (might be intentional)
        if not origins_list or origins_list == [""]:
            errors.append(
                "⚠️  CORS_ORIGINS is empty in PRODUCTION!\n"
                "   This will block all cross-origin requests.\n"
                "   If using WordPress integration, set:\n"
                "   CORS_ORIGINS=https://your-wordpress-domain.com"
            )

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
