"""
Absences API Routes
CRUD Operations für Abwesenheitsmeldungen
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session, selectinload, joinedload
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.models import User, Absence, AffectedLesson, UserRole, AbsenceStatus
from app.schemas.schemas import (
    AbsenceCreate,
    AbsenceResponse,
    AbsenceUpdate,
    AbsenceApproval,
    AffectedLessonUpdate,
    AffectedLessonResponse,
)
from app.api.auth import get_current_active_user, require_role, get_wordpress_proxy_user
from app.services.webuntis_service import webuntis_service
from app.services.email_service import email_service
from app.services.attachment_service import attachment_service
from app.services.permission_service import permission_service
from app.services.absence_service import absence_service

router = APIRouter()

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/", response_model=AbsenceResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_absence(
    request: Request,
    absence: AbsenceCreate,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Erstellt neue Abwesenheitsmeldung

    Args:
        absence: Abwesenheitsdaten
        current_user: Aktueller User
        db: Database Session

    Returns:
        Erstellte Abwesenheit mit betroffenen Stunden
    """
    # Delegiert an absence_service
    return await absence_service.create_absence(absence, current_user, db)


@router.get("/", response_model=List[AbsenceResponse])
@limiter.limit("60/minute")
async def list_absences(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status: AbsenceStatus = None,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Listet Abwesenheiten auf

    - Lehrkräfte sehen nur eigene Abwesenheiten
    - Abteilungsleiter und Vertretungsplaner sehen alle

    Args:
        skip: Anzahl zu überspringen
        limit: Maximale Anzahl
        status: Filter nach Status
        current_user: Aktueller User
        db: Database Session

    Returns:
        Liste von Abwesenheiten
    """
    query = db.query(Absence).options(
        selectinload(Absence.affected_lessons),
        selectinload(Absence.attachments),
        joinedload(Absence.teacher),
    )

    # Filter nach Rolle
    if current_user.role == UserRole.TEACHER:
        query = query.filter(Absence.teacher_id == current_user.id)

    # Filter nach Status
    if status:
        query = query.filter(Absence.status == status)

    # Sortierung nach Startdatum (früheste/dringendste zuerst)
    query = query.order_by(Absence.start_date.asc())

    absences = query.offset(skip).limit(limit).all()

    return absences


@router.get("/{absence_id}", response_model=AbsenceResponse)
@limiter.limit("60/minute")
async def get_absence(
    request: Request,
    absence_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Holt einzelne Abwesenheit

    Args:
        absence_id: ID der Abwesenheit
        current_user: Aktueller User
        db: Database Session

    Returns:
        Abwesenheit

    Raises:
        HTTPException: Wenn nicht gefunden oder keine Berechtigung
    """
    absence = (
        db.query(Absence)
        .options(
            selectinload(Absence.affected_lessons),
            selectinload(Absence.attachments),
            joinedload(Absence.teacher),
        )
        .filter(Absence.id == absence_id)
        .first()
    )

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
        )

    # Berechtigung prüfen (delegiert an Service)
    if not permission_service.can_view_absence(current_user, absence):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this absence",
        )

    return absence


@router.patch(
    "/{absence_id}/lessons/{lesson_id}", response_model=AffectedLessonResponse
)
@limiter.limit("30/minute")
async def update_lesson_notes(
    request: Request,
    absence_id: int,
    lesson_id: int,
    lesson_update: AffectedLessonUpdate,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Aktualisiert Hinweise für betroffene Stunde

    Args:
        absence_id: ID der Abwesenheit
        lesson_id: ID der betroffenen Stunde
        lesson_update: Update-Daten
        current_user: Aktueller User
        db: Database Session

    Returns:
        Aktualisierte Stunde
    """
    # Abwesenheit und Stunde laden
    absence = db.query(Absence).filter(Absence.id == absence_id).first()

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
        )

    # Berechtigung prüfen (delegiert an Service)
    if not permission_service.can_edit_absence(current_user, absence):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to edit this absence",
        )

    # Stunde laden
    lesson = (
        db.query(AffectedLesson)
        .filter(AffectedLesson.id == lesson_id, AffectedLesson.absence_id == absence_id)
        .first()
    )

    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    # Update durchführen
    if lesson_update.notes is not None:
        lesson.notes = lesson_update.notes

    db.commit()
    db.refresh(lesson)

    return lesson


@router.post("/{absence_id}/approve")
@limiter.limit("30/minute")
async def approve_absence(
    request: Request,
    absence_id: int,
    approval: AbsenceApproval,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Genehmigt oder lehnt Abwesenheit ab

    Erlaubt für: Dept_Head, Admin, Planner

    Args:
        absence_id: ID der Abwesenheit
        approval: Genehmigungs-Daten
        current_user: Aktueller User
        db: Database Session

    Returns:
        Success Message
    """
    # Berechtigungsprüfung zuerst
    absence = db.query(Absence).filter(Absence.id == absence_id).first()

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
        )

    if not permission_service.can_approve_absence(current_user, absence):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to approve this absence",
        )

    # Delegiert an absence_service
    message = await absence_service.approve_absence(
        absence_id, approval.approved, current_user, db, request
    )

    return {"message": message}


@router.post("/{absence_id}/complete")
@limiter.limit("30/minute")
async def complete_absence(
    request: Request,
    absence_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Markiert Abwesenheit als erledigt/eingetragen

    Erlaubt für: Planner, Admin, und optional Dept_Head (wenn Setting aktiv)

    Args:
        absence_id: ID der Abwesenheit
        request: HTTP Request (für Header)
        current_user: Aktueller User
        db: Database Session

    Returns:
        Success Message
    """
    # Berechtigungsprüfung (delegiert an Service)
    dept_heads_can_complete = (
        request.headers.get("X-WordPress-Dept-Heads-Can-Complete", "0") == "1"
    )
    if not permission_service.can_complete_absence(
        current_user, dept_heads_can_complete
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete absences",
        )

    # Delegiert an absence_service
    message = await absence_service.complete_absence(
        absence_id, current_user, db, request
    )

    return {"message": message}


@router.delete("/{absence_id}")
@limiter.limit("10/minute")
async def delete_absence(
    request: Request,
    absence_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Löscht Abwesenheit

    Nur eigene Abwesenheiten solange nicht erledigt; Admins/Planner können immer löschen

    Args:
        absence_id: ID der Abwesenheit
        current_user: Aktueller User
        db: Database Session

    Returns:
        Success Message
    """
    absence = db.query(Absence).filter(Absence.id == absence_id).first()

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Absence not found"
        )

    # Berechtigung prüfen (delegiert an Service)
    if not permission_service.can_delete_absence(current_user, absence):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this absence",
        )

    # Delegiert an absence_service
    message = await absence_service.delete_absence(absence_id, current_user, db)

    return {"message": message}
