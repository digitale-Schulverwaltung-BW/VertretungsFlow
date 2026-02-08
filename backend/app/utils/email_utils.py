"""
Email Utilities
Helper functions for email-related operations
"""

from typing import List, cast
from sqlalchemy.orm import Session

from app.models.models import User, UserRole


# Reason labels for emails (German)
REASON_LABELS = {
    "sick": "Krankheit",
    "training": "Fortbildung",
    "excursion": "Exkursion",
    "personal": "Privat",
    "other": "Sonstiges",
}


def get_recipients_by_roles(db: Session, roles: List[UserRole]) -> List[str]:
    """
    Get email addresses for users with specific roles

    Args:
        db: Database session
        roles: List of UserRole enums

    Returns:
        List of email addresses (non-null, active users only)
    """
    users = (
        db.query(User)
        .filter(User.role.in_(roles), User.is_active.is_(True), User.email.isnot(None))
        .all()
    )

    return [cast(str, user.email) for user in users]
