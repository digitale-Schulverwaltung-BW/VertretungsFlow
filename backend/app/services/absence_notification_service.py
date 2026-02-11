"""
Absence Notification Service
Business logic for sending absence-related email notifications
"""

import logging
from typing import cast
from sqlalchemy.orm import Session

from app.models.models import Absence, User, UserRole
from app.services.email_service import email_service
from app.utils.email_utils import get_recipients_by_roles, REASON_LABELS

logger = logging.getLogger(__name__)


class AbsenceNotificationService:
    """Service for absence email notifications"""

    async def send_submitted_notification(
        self, absence: Absence, current_user: User, db: Session
    ) -> None:
        """
        Sends email notification when absence is submitted

        Args:
            absence: Absence object
            current_user: User who submitted the absence
            db: Database session
        """
        try:
            dept_head_emails = get_recipients_by_roles(db, [UserRole.DEPARTMENT_HEAD])
            planner_emails = get_recipients_by_roles(db, [UserRole.PLANNER])

            start_date_str = absence.start_date.strftime("%d.%m.%Y")
            end_date_str = absence.end_date.strftime("%d.%m.%Y")
            reason_label = REASON_LABELS.get(
                cast(str, absence.reason), cast(str, absence.reason)
            )

            # Use absence.teacher for recipient — may differ from current_user
            # when an admin creates an absence on behalf of another teacher
            effective_teacher = absence.teacher or current_user

            success = await email_service.send_absence_submitted_notification(
                teacher_name=effective_teacher.full_name or effective_teacher.username,
                teacher_email=effective_teacher.email,
                dept_head_emails=dept_head_emails,
                planner_emails=planner_emails,
                absence_id=absence.id,
                reason=reason_label,
                start_date=start_date_str,
                end_date=end_date_str,
            )

            if not success:
                logger.warning(
                    f"Some email notifications failed for absence {absence.id}"
                )
            else:
                logger.info(f"✓ Submitted notification sent for absence {absence.id}")
        except Exception as e:
            logger.error(f"Email notification error for absence {absence.id}: {e}")
            # Continue - don't fail the request

    async def send_approved_notification(
        self, absence: Absence, current_user: User, db: Session
    ) -> None:
        """
        Sends email notification when absence is approved

        Args:
            absence: Absence object
            current_user: User who approved the absence
            db: Database session
        """
        try:
            planner_emails = get_recipients_by_roles(db, [UserRole.PLANNER])

            if absence.teacher and absence.teacher.email:
                success = await email_service.send_absence_approved_notification(
                    teacher_email=absence.teacher.email,
                    planner_emails=planner_emails,
                    absence_id=absence.id,
                    approver_name=current_user.full_name or current_user.username,
                )

                if not success:
                    logger.warning(
                        f"Email notification failed for approved absence {absence.id}"
                    )
                else:
                    logger.info(
                        f"✓ Approved notification sent for absence {absence.id}"
                    )
            else:
                logger.warning(
                    "Cannot send approval email: teacher has no email address"
                )
        except Exception as e:
            logger.error(
                f"Email notification error for approved absence {absence.id}: {e}"
            )

    async def send_completed_notification(self, absence: Absence, db: Session) -> None:
        """
        Sends email notification when absence is completed

        Args:
            absence: Absence object
            db: Database session
        """
        try:
            if absence.teacher and absence.teacher.email:
                success = await email_service.send_absence_completed_notification(
                    teacher_email=absence.teacher.email, absence_id=absence.id
                )

                if not success:
                    logger.warning(
                        f"Email notification failed for completed absence {absence.id}"
                    )
                else:
                    logger.info(
                        f"✓ Completed notification sent for absence {absence.id}"
                    )
            else:
                logger.warning(
                    "Cannot send completion email: teacher has no email address"
                )
        except Exception as e:
            logger.error(
                f"Email notification error for completed absence {absence.id}: {e}"
            )

    async def send_rejected_notification(
        self, absence: Absence, current_user: User, db: Session
    ) -> None:
        """
        Sends email notification when absence is rejected

        Args:
            absence: Absence object
            current_user: User who rejected the absence
            db: Database session
        """
        try:
            if absence.teacher and absence.teacher.email:
                success = await email_service.send_absence_rejected_notification(
                    teacher_email=absence.teacher.email,
                    absence_id=absence.id,
                    rejector_name=current_user.full_name or current_user.username,
                )

                if not success:
                    logger.warning(
                        f"Email notification failed for rejected absence {absence.id}"
                    )
                else:
                    logger.info(
                        f"✓ Rejected notification sent for absence {absence.id}"
                    )
            else:
                logger.warning(
                    "Cannot send rejection email: teacher has no email address"
                )
        except Exception as e:
            logger.error(
                f"Email notification error for rejected absence {absence.id}: {e}"
            )

    async def send_deleted_notification(
        self, absence: Absence, current_user: User, db: Session
    ) -> None:
        """
        Sends email notification when absence is deleted by the teacher

        Args:
            absence: Absence object (must have teacher relationship loaded)
            current_user: User who deleted the absence
            db: Database session
        """
        try:
            dept_head_emails = get_recipients_by_roles(db, [UserRole.DEPARTMENT_HEAD])
            planner_emails = get_recipients_by_roles(db, [UserRole.PLANNER])

            if not dept_head_emails and not planner_emails:
                logger.info(
                    f"No recipients for deleted notification for absence {absence.id}"
                )
                return

            start_date_str = absence.start_date.strftime("%d.%m.%Y")
            end_date_str = absence.end_date.strftime("%d.%m.%Y")
            reason_label = REASON_LABELS.get(
                cast(str, absence.reason), cast(str, absence.reason)
            )
            teacher_name = current_user.full_name or current_user.username

            success = await email_service.send_absence_deleted_notification(
                teacher_name=teacher_name,
                dept_head_emails=dept_head_emails,
                planner_emails=planner_emails,
                absence_id=absence.id,
                reason=reason_label,
                start_date=start_date_str,
                end_date=end_date_str,
            )

            if not success:
                logger.warning(
                    f"Some email notifications failed for deleted absence {absence.id}"
                )
            else:
                logger.info(f"✓ Deleted notification sent for absence {absence.id}")
        except Exception as e:
            logger.error(
                f"Email notification error for deleted absence {absence.id}: {e}"
            )
            # Continue - don't fail the request


# Singleton instance
absence_notification_service = AbsenceNotificationService()
