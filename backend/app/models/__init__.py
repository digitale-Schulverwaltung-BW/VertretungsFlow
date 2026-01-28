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
)

__all__ = [
    "User",
    "UserRole",
    "Absence",
    "AbsenceStatus",
    "AffectedLesson",
    "Notification",
]
