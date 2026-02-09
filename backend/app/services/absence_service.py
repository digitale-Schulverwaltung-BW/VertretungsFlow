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
    User,
    Absence,
    AffectedLesson,
    AbsenceStatus,
    AbsenceAttachment,
)
from app.schemas.schemas import AbsenceCreate
from app.services.webuntis_service import webuntis_service
from app.services.attachment_service import attachment_service
from app.services.absence_notification_service import absence_notification_service
from app.utils.absence_utils import validate_date_range, is_lesson_in_period
from app.core.audit import audit_absence_approved, audit_absence_completed, audit_log

logger = logging.getLogger(__name__)


class AbsenceService:
    """Service for absence business logic"""

    async def create_absence(
        self, absence_data: AbsenceCreate, current_user: User, db: Session
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
        validate_date_range(
            absence_data.start_date,
            absence_data.end_date,
            absence_data.start_period,
            absence_data.end_period,
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
            admin_notes=absence_data.admin_notes,
        )

        db.add(db_absence)
        db.commit()
        db.refresh(db_absence)

        # Eager load relationships nach refresh
        db_absence = (
            db.query(Absence)
            .options(
                selectinload(Absence.affected_lessons),
                selectinload(Absence.attachments),
                joinedload(Absence.teacher),
            )
            .filter(Absence.id == db_absence.id)
            .first()
        )

        # Betroffene Stunden aus WebUntis abrufen
        lessons = await webuntis_service.get_timetable_for_teacher(
            current_user.username,
            absence_data.start_date,
            absence_data.end_date,
            db=db,
            webuntis_code=current_user.webuntis_teacher_code,
        )

        # Erstelle Lookup-Dictionary für Lehrkraft-Inputs (notes, can_be_canceled)
        lesson_inputs = {}
        if absence_data.affected_lessons:
            for input_lesson in absence_data.affected_lessons:
                # Key: (date, period) für eindeutige Identifikation
                key = (input_lesson.date.date(), input_lesson.period)
                lesson_inputs[key] = {
                    "notes": input_lesson.notes,
                    "can_be_canceled": input_lesson.can_be_canceled or False,
                }

        # Betroffene Stunden in DB speichern
        for lesson in lessons:
            if is_lesson_in_period(
                lesson,
                absence_data.start_date,
                absence_data.end_date,
                absence_data.start_period,
                absence_data.end_period,
            ):
                # Suche nach Lehrkraft-Inputs für diese Stunde
                key = (lesson.date.date(), lesson.period)
                inputs = lesson_inputs.get(key, {})

                affected_lesson = AffectedLesson(
                    absence_id=db_absence.id,
                    date=lesson.date,
                    period=lesson.period,
                    end_period=lesson.end_period,  # Für Doppelstunden
                    start_time=lesson.start_time,  # WebUntis startTime (e.g., 730 = 07:30)
                    end_time=lesson.end_time,  # WebUntis endTime (e.g., 815 = 08:15)
                    subject=lesson.subject,
                    class_name=lesson.class_name,
                    room=lesson.room,
                    notes=inputs.get("notes"),
                    can_be_canceled=inputs.get("can_be_canceled", False),
                )
                db.add(affected_lesson)

        db.commit()
        db.refresh(db_absence)

        # Send email notifications
        await absence_notification_service.send_submitted_notification(
            db_absence, current_user, db
        )

        return db_absence

    async def approve_absence(
        self,
        absence_id: int,
        approved: bool,
        current_user: User,
        db: Session,
        request: Request,
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
        absence = (
            db.query(Absence)
            .options(joinedload(Absence.teacher))
            .filter(Absence.id == absence_id)
            .first()
        )

        if not absence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
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
                    "approver_role": current_user.role.value,
                },
                request=request,
            )

            # Send email notifications
            await absence_notification_service.send_approved_notification(
                absence, current_user, db
            )

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
                    "rejector_role": current_user.role.value,
                },
                request=request,
            )

            # Send email notification
            await absence_notification_service.send_rejected_notification(
                absence, current_user, db
            )

            return "Absence rejected"

    async def complete_absence(
        self, absence_id: int, current_user: User, db: Session, request: Request
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
        absence = (
            db.query(Absence)
            .options(joinedload(Absence.teacher), selectinload(Absence.attachments))
            .filter(Absence.id == absence_id)
            .first()
        )

        if not absence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
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
                "attachments_count": (
                    len(absence.attachments) if absence.attachments else 0
                ),
            },
            request=request,
        )

        # Attachments automatisch löschen
        if absence.attachments:
            logger.info(
                f"Deleting {len(absence.attachments)} attachments for completed absence {absence_id}"
            )

            for attachment in absence.attachments:
                # Datei von Disk löschen (delegiert an Service)
                attachment_service.delete_file(attachment.file_path)

            # DB-Einträge werden durch CASCADE automatisch gelöscht

        db.commit()

        # Send email notification to teacher
        await absence_notification_service.send_completed_notification(absence, db)

        return "Absence marked as completed, attachments deleted"

    def delete_absence(self, absence_id: int, db: Session) -> str:
        """
        Deletes an absence and all associated files

        Args:
            absence_id: Absence ID
            db: Database session

        Returns:
            Success message

        Raises:
            HTTPException: If absence not found
        """
        # Eager load attachments for cleanup
        absence = db.query(Absence).options(
            selectinload(Absence.attachments)
        ).filter(Absence.id == absence_id).first()

        if not absence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
            )

        # Delete attachments from disk before deleting DB record
        if absence.attachments:
            logger.info(f"Deleting {len(absence.attachments)} attachments for absence {absence_id}...")
            for attachment in absence.attachments:
                try:
                    attachment_service.delete_file(attachment.file_path)
                except Exception as e:
                    logger.warning(f"Failed to delete file {attachment.file_path}: {e}")

        # Delete database record (CASCADE will delete affected_lessons and attachment records)
        db.delete(absence)
        db.commit()

        logger.info(f"Absence {absence_id} deleted successfully")
        return "Absence deleted"

    def cleanup_old_absences(self, db: Session, retention_days: int) -> dict:
        """
        Deletes absences older than retention_days (based on end_date)

        Args:
            db: Database session
            retention_days: Number of days to retain absences after end_date

        Returns:
            Dict with cleanup statistics: {"deleted_count": int, "errors": int}
        """
        from datetime import timedelta

        if retention_days <= 0:
            logger.info("Absence auto-deletion disabled (retention_days <= 0)")
            return {"deleted_count": 0, "errors": 0}

        cutoff_date = datetime.now().date() - timedelta(days=retention_days)

        logger.info(f"Starting cleanup of absences with end_date before {cutoff_date}")

        # Find all absences older than cutoff_date
        old_absences = db.query(Absence).filter(
            Absence.end_date < cutoff_date
        ).all()

        deleted_count = 0
        error_count = 0

        for absence in old_absences:
            try:
                logger.info(f"Deleting old absence {absence.id} (end_date: {absence.end_date}, teacher: {absence.teacher.username})")
                self.delete_absence(absence.id, db)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Failed to delete absence {absence.id}: {e}")
                error_count += 1

        logger.info(f"Cleanup completed: {deleted_count} absences deleted, {error_count} errors")

        return {
            "deleted_count": deleted_count,
            "errors": error_count,
            "cutoff_date": cutoff_date.isoformat()
        }


# Singleton instance
absence_service = AbsenceService()
