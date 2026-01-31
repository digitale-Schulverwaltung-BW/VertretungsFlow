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
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:8080"
    ]

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from comma-separated string or list"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
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

    # File Upload Configuration
    # Default: backend/uploads (außerhalb webroot, im Projekt-Tree)
    UPLOAD_DIR: str = str(Path(__file__).resolve().parent.parent.parent / "uploads")
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB

    # JWT Token
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 Stunden
    ALGORITHM: str = "HS256"

    # Authentication Mode
    AUTH_MODE: str = "wordpress"  # "wordpress" oder "standalone"

    # WordPress Proxy Authentication
    WORDPRESS_PROXY_SECRET: str = "change-this-shared-secret-in-production"

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
    }


# Globale Settings-Instanz
settings = Settings()
