"""
Absence Service
Business logic for absence management
"""
import logging
from datetime import datetime
from typing import List, Dict, Any
from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session, selectinload, joinedload

from app.models.models import (
    User, Absence, AffectedLesson, AbsenceStatus, UserRole,
    AbsenceAttachment
)
from app.schemas.schemas import AbsenceCreate, WebUntisLesson
from app.services.webuntis_service import webuntis_service
from app.services.email_service import email_service
from app.services.attachment_service import attachment_service
from app.core.audit import (
    audit_absence_approved, audit_absence_completed, audit_log
)

logger = logging.getLogger(__name__)


class AbsenceService:
    """Service for absence business logic"""

    def validate_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        start_period: int,
        end_period: int
    ) -> None:
        """
        Validates date range and periods

        Args:
            start_date: Start date
            end_date: End date
            start_period: Start period
            end_period: End period

        Raises:
            HTTPException: If validation fails
        """
        # Validierung: end_date >= start_date
        if end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End date must be after or equal to start date"
            )

        # Validierung: end_period >= start_period bei gleichen Tagen
        if start_date.date() == end_date.date():
            if end_period < start_period:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="End period must be after or equal to start period"
                )

    def is_lesson_in_period(
        self,
        lesson: WebUntisLesson,
        start_date: datetime,
        end_date: datetime,
        start_period: int,
        end_period: int
    ) -> bool:
        """
        Checks if lesson is within the specified period

        Args:
            lesson: Lesson to check
            start_date: Start date
            end_date: End date
            start_period: Start period
            end_period: End period

        Returns:
            True if lesson is in period, False otherwise
        """
        # Check if lesson is within date range
        if not (start_date.date() <= lesson.date.date() <= end_date.date()):
            return False

        # Filter nach Periode
        if start_date.date() == end_date.date():
            # Eintägige Abwesenheit
            return start_period <= lesson.period <= end_period
        elif lesson.date.date() == start_date.date():
            # Erster Tag
            return lesson.period >= start_period
        elif lesson.date.date() == end_date.date():
            # Letzter Tag
            return lesson.period <= end_period
        else:
            # Tage dazwischen
            return True

    async def create_absence(
        self,
        absence_data: AbsenceCreate,
        current_user: User,
        db: Session
    ) -> Absence:
        """
        Creates a new absence with affected lessons

        Args:
            absence_data: Absence data
            current_user: Current user
            db: Database session

        Returns:
            Created absence

        Raises:
            HTTPException: If validation fails
        """
        logger.info(f"📝 Create absence request from user {current_user.username}")

        # Validierung
        self.validate_date_range(
            absence_data.start_date,
            absence_data.end_date,
            absence_data.start_period,
            absence_data.end_period
        )

        # Abwesenheit in DB erstellen
        db_absence = Absence(
            teacher_id=current_user.id,
            reason=absence_data.reason,
            start_date=absence_data.start_date,
            end_date=absence_data.end_date,
            start_period=absence_data.start_period,
            end_period=absence_data.end_period,
            status=AbsenceStatus.SUBMITTED,
            excursion_classes=absence_data.excursion_classes,
            personal_reason=absence_data.personal_reason,
            admin_notes=absence_data.admin_notes
        )

        db.add(db_absence)
        db.commit()
        db.refresh(db_absence)

        # Eager load relationships nach refresh
        db_absence = db.query(Absence).options(
            selectinload(Absence.affected_lessons),
            selectinload(Absence.attachments),
            joinedload(Absence.teacher)
        ).filter(Absence.id == db_absence.id).first()

        # Betroffene Stunden aus WebUntis abrufen
        lessons = await webuntis_service.get_timetable_for_teacher(
            current_user.username,
            absence_data.start_date,
            absence_data.end_date,
            db=db,
            webuntis_code=current_user.webuntis_teacher_code
        )

        # Erstelle Lookup-Dictionary für Lehrkraft-Inputs (notes, can_be_canceled)
        lesson_inputs = {}
        if absence_data.affected_lessons:
            for input_lesson in absence_data.affected_lessons:
                # Key: (date, period) für eindeutige Identifikation
                key = (input_lesson.date.date(), input_lesson.period)
                lesson_inputs[key] = {
                    'notes': input_lesson.notes,
                    'can_be_canceled': input_lesson.can_be_canceled or False
                }

        # Betroffene Stunden in DB speichern
        for lesson in lessons:
            if self.is_lesson_in_period(
                lesson,
                absence_data.start_date,
                absence_data.end_date,
                absence_data.start_period,
                absence_data.end_period
            ):
                # Suche nach Lehrkraft-Inputs für diese Stunde
                key = (lesson.date.date(), lesson.period)
                inputs = lesson_inputs.get(key, {})

                affected_lesson = AffectedLesson(
                    absence_id=db_absence.id,
                    date=lesson.date,
                    period=lesson.period,
                    end_period=lesson.end_period,  # Für Doppelstunden
                    subject=lesson.subject,
                    class_name=lesson.class_name,
                    room=lesson.room,
                    notes=inputs.get('notes'),
                    can_be_canceled=inputs.get('can_be_canceled', False)
                )
                db.add(affected_lesson)

        db.commit()
        db.refresh(db_absence)

        # Send email notifications
        await self._send_absence_submitted_notification(db_absence, current_user, db)

        return db_absence

    async def approve_absence(
        self,
        absence_id: int,
        approved: bool,
        current_user: User,
        db: Session,
        request: Request
    ) -> str:
        """
        Approves or rejects an absence

        Args:
            absence_id: Absence ID
            approved: True to approve, False to reject
            current_user: Current user
            db: Database session
            request: HTTP request (for audit logging)

        Returns:
            Success message

        Raises:
            HTTPException: If absence not found
        """
        absence = db.query(Absence).options(
            joinedload(Absence.teacher)
        ).filter(Absence.id == absence_id).first()

        if not absence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Absence not found"
            )

        if approved:
            old_status = absence.status.value
            absence.status = AbsenceStatus.APPROVED
            absence.approved_by = current_user.id
            absence.approved_at = datetime.utcnow()

            db.commit()

            # Audit log
            audit_absence_approved(
                absence_id=absence.id,
                approver_id=current_user.id,
                details={
                    "old_status": old_status,
                    "new_status": "approved",
                    "teacher_id": absence.teacher_id,
                    "approver_role": current_user.role.value
                },
                request=request
            )

            # Send email notifications
            await self._send_absence_approved_notification(absence, current_user, db)

            return "Absence approved"
        else:
            old_status = absence.status.value
            absence.status = AbsenceStatus.REJECTED
            db.commit()

            # Audit log for rejection
            audit_log(
                action="absence_rejected",
                user_id=current_user.id,
                resource_type="absence",
                resource_id=absence.id,
                details={
                    "old_status": old_status,
                    "new_status": "rejected",
                    "teacher_id": absence.teacher_id,
                    "rejector_role": current_user.role.value
                },
                request=request
            )

            return "Absence rejected"

    async def complete_absence(
        self,
        absence_id: int,
        current_user: User,
        db: Session,
        request: Request
    ) -> str:
        """
        Marks absence as completed/entered

        Args:
            absence_id: Absence ID
            current_user: Current user
            db: Database session
            request: HTTP request (for audit logging)

        Returns:
            Success message

        Raises:
            HTTPException: If absence not found
        """
        absence = db.query(Absence).options(
            joinedload(Absence.teacher),
            selectinload(Absence.attachments)
        ).filter(Absence.id == absence_id).first()

        if not absence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Absence not found"
            )

        # Status aktualisieren
        old_status = absence.status.value
        absence.status = AbsenceStatus.COMPLETED
        absence.completed_at = datetime.utcnow()

        # Audit log
        audit_absence_completed(
            absence_id=absence.id,
            completer_id=current_user.id,
            details={
                "old_status": old_status,
                "new_status": "completed",
                "teacher_id": absence.teacher_id,
                "completer_role": current_user.role.value,
                "attachments_count": len(absence.attachments) if absence.attachments else 0
            },
            request=request
        )

        # Attachments automatisch löschen
        if absence.attachments:
            logger.info(f"Deleting {len(absence.attachments)} attachments for completed absence {absence_id}")

            for attachment in absence.attachments:
                # Datei von Disk löschen (delegiert an Service)
                attachment_service.delete_file(attachment.file_path)

            # DB-Einträge werden durch CASCADE automatisch gelöscht

        db.commit()

        # Send email notification to teacher
        await self._send_absence_completed_notification(absence, db)

        return "Absence marked as completed, attachments deleted"

    def delete_absence(
        self,
        absence_id: int,
        db: Session
    ) -> str:
        """
        Deletes an absence

        Args:
            absence_id: Absence ID
            db: Database session

        Returns:
            Success message

        Raises:
            HTTPException: If absence not found
        """
        absence = db.query(Absence).filter(Absence.id == absence_id).first()

        if not absence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Absence not found"
            )

        db.delete(absence)
        db.commit()

        return "Absence deleted"

    # Private helper methods for email notifications

    async def _send_absence_submitted_notification(
        self,
        absence: Absence,
        current_user: User,
        db: Session
    ) -> None:
        """Sends email notification when absence is submitted"""
        try:
            from app.utils.email_utils import get_recipients_by_roles, REASON_LABELS

            dept_head_emails = get_recipients_by_roles(db, [UserRole.DEPARTMENT_HEAD])
            planner_emails = get_recipients_by_roles(db, [UserRole.PLANNER])

            start_date_str = absence.start_date.strftime("%d.%m.%Y")
            end_date_str = absence.end_date.strftime("%d.%m.%Y")
            reason_label = REASON_LABELS.get(absence.reason, absence.reason)

            success = await email_service.send_absence_submitted_notification(
                teacher_name=current_user.full_name or current_user.username,
                teacher_email=current_user.email,
                dept_head_emails=dept_head_emails,
                planner_emails=planner_emails,
                absence_id=absence.id,
                reason=reason_label,
                start_date=start_date_str,
                end_date=end_date_str
            )

            if not success:
                logger.warning(f"Some email notifications failed for absence {absence.id}")
        except Exception as e:
            logger.error(f"Email notification error for absence {absence.id}: {e}")
            # Continue - don't fail the request

    async def _send_absence_approved_notification(
        self,
        absence: Absence,
        current_user: User,
        db: Session
    ) -> None:
        """Sends email notification when absence is approved"""
        try:
            from app.utils.email_utils import get_recipients_by_roles

            planner_emails = get_recipients_by_roles(db, [UserRole.PLANNER])

            if absence.teacher and absence.teacher.email:
                success = await email_service.send_absence_approved_notification(
                    teacher_email=absence.teacher.email,
                    planner_emails=planner_emails,
                    absence_id=absence.id,
                    approver_name=current_user.full_name or current_user.username
                )

                if not success:
                    logger.warning(f"Email notification failed for approved absence {absence.id}")
            else:
                logger.warning(f"Cannot send approval email: teacher has no email address")
        except Exception as e:
            logger.error(f"Email notification error for approved absence {absence.id}: {e}")

    async def _send_absence_completed_notification(
        self,
        absence: Absence,
        db: Session
    ) -> None:
        """Sends email notification when absence is completed"""
        try:
            if absence.teacher and absence.teacher.email:
                success = await email_service.send_absence_completed_notification(
                    teacher_email=absence.teacher.email,
                    absence_id=absence.id
                )

                if not success:
                    logger.warning(f"Email notification failed for completed absence {absence.id}")
            else:
                logger.warning(f"Cannot send completion email: teacher has no email address")
        except Exception as e:
            logger.error(f"Email notification error for completed absence {absence.id}: {e}")


# Singleton instance
absence_service = AbsenceService()
