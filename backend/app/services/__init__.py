"""
Services package
"""
from app.core.config import settings
from app.services.email_service import EmailService, email_service
from app.services.webuntis_service import WebUntisService, webuntis_service
from app.services.template_service import TemplateService, template_service
from app.services.absence_notification_service import (
    AbsenceNotificationService,
    absence_notification_service
)

# Conditional LDAP import - nur für Standalone-Modus
if settings.AUTH_MODE == "standalone":
    try:
        from app.services.ldap_service import LDAPService, ldap_service
    except ImportError:
        # python-ldap nicht installiert - Fehler für Standalone-Modus
        raise ImportError(
            "python-ldap is required for standalone mode. "
            "Install with: pip install -r requirements-standalone.txt"
        )

    __all__ = [
        "LDAPService",
        "ldap_service",
        "EmailService",
        "email_service",
        "WebUntisService",
        "webuntis_service",
        "TemplateService",
        "template_service",
        "AbsenceNotificationService",
        "absence_notification_service",
    ]
else:
    # WordPress-Modus - LDAP nicht verfügbar
    LDAPService = None
    ldap_service = None

    __all__ = [
        "EmailService",
        "email_service",
        "WebUntisService",
        "webuntis_service",
        "TemplateService",
        "template_service",
        "AbsenceNotificationService",
        "absence_notification_service",
    ]
