"""
Konfiguration für AbsenzFlow
Lädt Umgebungsvariablen aus .env
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application Settings"""
    
    # Application
    APP_NAME: str = "AbsenzFlow"
    API_URL: str = "http://localhost:8000"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080"
    ]
    
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
    
    # JWT Token
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 Stunden
    ALGORITHM: str = "HS256"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            """Parse CORS_ORIGINS as comma-separated list"""
            if field_name == "CORS_ORIGINS":
                return [origin.strip() for origin in raw_val.split(",")]
            return raw_val


# Globale Settings-Instanz
settings = Settings()
