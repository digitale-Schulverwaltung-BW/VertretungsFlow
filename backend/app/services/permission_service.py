"""
Permission Service
Centralized authorization logic for absence management
"""

import logging
from typing import Optional

from app.models.models import User, Absence, UserRole, AbsenceStatus

logger = logging.getLogger(__name__)


class PermissionService:
    """Service for managing permissions"""

    def can_view_absence(self, user: User, absence: Absence) -> bool:
        """
        Check if user can view an absence

        Args:
            user: Current user
            absence: Absence to check

        Returns:
            True if user can view, False otherwise
        """
        # Teachers can only view their own absences
        if user.role == UserRole.TEACHER:
            return absence.teacher_id == user.id

        # Admins, Planners, and Department Heads can view all absences
        return user.role in [UserRole.ADMIN, UserRole.PLANNER, UserRole.DEPARTMENT_HEAD]

    def can_edit_absence(self, user: User, absence: Absence) -> bool:
        """
        Check if user can edit an absence

        Args:
            user: Current user
            absence: Absence to check

        Returns:
            True if user can edit, False otherwise
        """
        # Cannot edit completed absences (except for admins/planners)
        if absence.status == AbsenceStatus.COMPLETED:
            return user.role in [UserRole.ADMIN, UserRole.PLANNER]

        # Teachers can only edit their own absences
        if user.role == UserRole.TEACHER:
            return absence.teacher_id == user.id

        # Admins and Planners can edit all absences
        return user.role in [UserRole.ADMIN, UserRole.PLANNER]

    def can_approve_absence(
        self, user: User, absence: Optional[Absence] = None
    ) -> bool:
        """
        Check if user can approve absences

        Args:
            user: Current user
            absence: Optional absence to check (for status validation)

        Returns:
            True if user can approve, False otherwise
        """
        # Only these roles can approve
        allowed_roles = [UserRole.DEPARTMENT_HEAD, UserRole.ADMIN, UserRole.PLANNER]
        if user.role not in allowed_roles:
            return False

        # If absence provided, check status
        if absence:
            # Admin/Planner can approve regardless of status
            if user.role in [UserRole.ADMIN, UserRole.PLANNER]:
                return True

            # Others can only approve SUBMITTED absences
            return absence.status == AbsenceStatus.SUBMITTED

        return True

    def can_complete_absence(
        self, user: User, dept_heads_can_complete: bool = False
    ) -> bool:
        """
        Check if user can mark absences as completed

        Args:
            user: Current user
            dept_heads_can_complete: Whether department heads can complete absences (from settings)

        Returns:
            True if user can complete, False otherwise
        """
        allowed_roles = [UserRole.PLANNER, UserRole.ADMIN]
        if dept_heads_can_complete:
            allowed_roles.append(UserRole.DEPARTMENT_HEAD)

        return user.role in allowed_roles

    def can_delete_absence(self, user: User, absence: Absence) -> bool:
        """
        Check if user can delete an absence

        Args:
            user: Current user
            absence: Absence to check

        Returns:
            True if user can delete, False otherwise
        """
        # Admins and Planners can always delete
        if user.role in [UserRole.ADMIN, UserRole.PLANNER]:
            return True

        # Teachers can only delete their own absences
        if absence.teacher_id != user.id:
            return False

        # Teachers can only delete DRAFT or SUBMITTED absences
        return absence.status in [AbsenceStatus.DRAFT, AbsenceStatus.SUBMITTED]


# Singleton instance
permission_service = PermissionService()
