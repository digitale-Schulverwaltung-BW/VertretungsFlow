"""
Models package
"""
from app.models.models import (
    User,
    UserRole,
    Absence,
    AbsenceStatus,
    AffectedLesson,
    Notification,
    AbsenceAttachment,
    WebUntisCache,
)

__all__ = [
    "User",
    "UserRole",
    "Absence",
    "AbsenceStatus",
    "AffectedLesson",
    "Notification",
    "AbsenceAttachment",
    "WebUntisCache",
]
