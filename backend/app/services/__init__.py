"""
Services package
"""
from app.services.ldap_service import LDAPService, ldap_service
from app.services.email_service import EmailService, email_service
from app.services.webuntis_service import WebUntisService, webuntis_service

__all__ = [
    "LDAPService",
    "ldap_service",
    "EmailService",
    "email_service",
    "WebUntisService",
    "webuntis_service",
]
