"""
Absences API Routes
CRUD Operations für Abwesenheitsmeldungen
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
    FetchLessonsRequest,
    WebUntisLesson
)
from app.api.auth import get_current_active_user, require_role, get_wordpress_proxy_user
from app.services.webuntis_service import webuntis_service
from app.services.email_service import email_service

router = APIRouter()


@router.post("/", response_model=AbsenceResponse, status_code=status.HTTP_201_CREATED)
async def create_absence(
    absence: AbsenceCreate,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
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
    logger.info(f"📝 Create absence request from user {current_user.username}")
    logger.info(f"Absence data: {absence}")

    # Validierung: end_date >= start_date
    if absence.end_date < absence.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after or equal to start date"
        )
    
    # Validierung: end_period >= start_period bei gleichen Tagen
    if absence.start_date.date() == absence.end_date.date():
        if absence.end_period < absence.start_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End period must be after or equal to start period"
            )
    
    # Abwesenheit in DB erstellen
    db_absence = Absence(
        teacher_id=current_user.id,
        reason=absence.reason,
        start_date=absence.start_date,
        end_date=absence.end_date,
        start_period=absence.start_period,
        end_period=absence.end_period,
        status=AbsenceStatus.SUBMITTED
    )
    
    db.add(db_absence)
    db.commit()
    db.refresh(db_absence)
    
    # Betroffene Stunden aus WebUntis abrufen
    lessons = await webuntis_service.get_timetable_for_teacher(
        current_user.username,
        absence.start_date,
        absence.end_date,
        webuntis_code=current_user.webuntis_teacher_code
    )

    # Erstelle Lookup-Dictionary für Lehrkraft-Inputs (notes, can_be_canceled)
    lesson_inputs = {}
    if absence.affected_lessons:
        for input_lesson in absence.affected_lessons:
            # Key: (date, period) für eindeutige Identifikation
            key = (input_lesson.date.date(), input_lesson.period)
            lesson_inputs[key] = {
                'notes': input_lesson.notes,
                'can_be_canceled': input_lesson.can_be_canceled or False
            }

    # Betroffene Stunden in DB speichern
    for lesson in lessons:
        # Filter: Nur Stunden im angegebenen Zeitraum
        if absence.start_date.date() <= lesson.date.date() <= absence.end_date.date():
            # Filter nach Periode
            is_in_period = False

            if absence.start_date.date() == absence.end_date.date():
                # Eintägige Abwesenheit
                is_in_period = absence.start_period <= lesson.period <= absence.end_period
            elif lesson.date.date() == absence.start_date.date():
                # Erster Tag
                is_in_period = lesson.period >= absence.start_period
            elif lesson.date.date() == absence.end_date.date():
                # Letzter Tag
                is_in_period = lesson.period <= absence.end_period
            else:
                # Tage dazwischen
                is_in_period = True

            if is_in_period:
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
    
    # TODO: E-Mail-Benachrichtigungen an Abteilungsleiter und Vertretungsplaner
    # await email_service.send_absence_submitted_notification(...)

    return db_absence


@router.post("/fetch-lessons", response_model=List[WebUntisLesson])
async def fetch_lessons_from_webuntis(
    request: FetchLessonsRequest,
    current_user: User = Depends(get_wordpress_proxy_user),
):
    """
    Lädt Stunden aus WebUntis für Vorschau (ohne DB-Speicherung)

    Wird vom WordPress-Frontend verwendet, um betroffene Stunden VOR dem Absenden anzuzeigen.
    Authentifizierung über WordPress Proxy Secret (kein JWT Token erforderlich).

    Args:
        request: Zeitraum und Perioden
        current_user: Aktueller User (via WordPress Proxy Auth)

    Returns:
        Liste von WebUntis-Stunden im angegebenen Zeitraum
    """
    # Validierung
    if request.end_date < request.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after or equal to start date"
        )

    if request.start_date.date() == request.end_date.date():
        if request.end_period < request.start_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="End period must be after or equal to start period"
            )

    # Stunden aus WebUntis abrufen
    lessons = await webuntis_service.get_timetable_for_teacher(
        current_user.username,
        request.start_date,
        request.end_date,
        webuntis_code=current_user.webuntis_teacher_code
    )

    # Filtern nach Perioden
    filtered_lessons = []
    for lesson in lessons:
        if request.start_date.date() <= lesson.date.date() <= request.end_date.date():
            is_in_period = False

            if request.start_date.date() == request.end_date.date():
                # Eintägige Abwesenheit
                is_in_period = request.start_period <= lesson.period <= request.end_period
            elif lesson.date.date() == request.start_date.date():
                # Erster Tag
                is_in_period = lesson.period >= request.start_period
            elif lesson.date.date() == request.end_date.date():
                # Letzter Tag
                is_in_period = lesson.period <= request.end_period
            else:
                # Tage dazwischen
                is_in_period = True

            if is_in_period:
                filtered_lessons.append(lesson)

    return filtered_lessons


@router.get("/", response_model=List[AbsenceResponse])
async def list_absences(
    skip: int = 0,
    limit: int = 100,
    status: AbsenceStatus = None,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
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
    query = db.query(Absence)
    
    # Filter nach Rolle
    if current_user.role == UserRole.TEACHER:
        query = query.filter(Absence.teacher_id == current_user.id)
    
    # Filter nach Status
    if status:
        query = query.filter(Absence.status == status)
    
    # Sortierung nach Erstellungsdatum (neueste zuerst)
    query = query.order_by(Absence.created_at.desc())
    
    absences = query.offset(skip).limit(limit).all()
    
    return absences


@router.get("/{absence_id}", response_model=AbsenceResponse)
async def get_absence(
    absence_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
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
    absence = db.query(Absence).filter(Absence.id == absence_id).first()
    
    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence not found"
        )
    
    # Berechtigung prüfen
    if current_user.role == UserRole.TEACHER and absence.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this absence"
        )
    
    return absence


@router.patch("/{absence_id}/lessons/{lesson_id}", response_model=AffectedLessonResponse)
async def update_lesson_notes(
    absence_id: int,
    lesson_id: int,
    lesson_update: AffectedLessonUpdate,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence not found"
        )
    
    # Berechtigung prüfen
    if current_user.role == UserRole.TEACHER and absence.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this lesson"
        )
    
    # Status prüfen - keine Bearbeitung wenn schon erledigt
    if absence.status == AbsenceStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update completed absence"
        )
    
    # Stunde laden
    lesson = db.query(AffectedLesson).filter(
        AffectedLesson.id == lesson_id,
        AffectedLesson.absence_id == absence_id
    ).first()
    
    if not lesson:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lesson not found"
        )
    
    # Update durchführen
    if lesson_update.notes is not None:
        lesson.notes = lesson_update.notes
    
    db.commit()
    db.refresh(lesson)
    
    return lesson


@router.post("/{absence_id}/approve")
async def approve_absence(
    absence_id: int,
    approval: AbsenceApproval,
    current_user: User = Depends(require_role([UserRole.DEPARTMENT_HEAD, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Genehmigt oder lehnt Abwesenheit ab
    
    Nur für Abteilungsleiter
    
    Args:
        absence_id: ID der Abwesenheit
        approval: Genehmigungs-Daten
        current_user: Aktueller User (muss Abteilungsleiter sein)
        db: Database Session
        
    Returns:
        Success Message
    """
    absence = db.query(Absence).filter(Absence.id == absence_id).first()
    
    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence not found"
        )
    
    # Status prüfen
    if absence.status != AbsenceStatus.SUBMITTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve submitted absences"
        )
    
    # Status aktualisieren
    from datetime import datetime
    
    if approval.approved:
        absence.status = AbsenceStatus.APPROVED
        absence.approved_by = current_user.id
        absence.approved_at = datetime.utcnow()
        
        # TODO: E-Mail-Benachrichtigungen
        # await email_service.send_absence_approved_notification(...)
        
        message = "Absence approved"
    else:
        absence.status = AbsenceStatus.REJECTED
        message = "Absence rejected"
    
    db.commit()
    
    return {"message": message}


@router.post("/{absence_id}/complete")
async def complete_absence(
    absence_id: int,
    current_user: User = Depends(require_role([UserRole.PLANNER, UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    """
    Markiert Abwesenheit als erledigt/eingetragen
    
    Nur für Vertretungsplaner
    
    Args:
        absence_id: ID der Abwesenheit
        current_user: Aktueller User (muss Vertretungsplaner sein)
        db: Database Session
        
    Returns:
        Success Message
    """
    absence = db.query(Absence).filter(Absence.id == absence_id).first()
    
    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence not found"
        )
    
    # Status prüfen
    if absence.status != AbsenceStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only complete approved absences"
        )
    
    # Status aktualisieren
    from datetime import datetime
    absence.status = AbsenceStatus.COMPLETED
    absence.completed_at = datetime.utcnow()
    
    db.commit()
    
    # TODO: E-Mail-Benachrichtigung an Lehrkraft
    # await email_service.send_absence_completed_notification(...)
    
    return {"message": "Absence marked as completed"}


@router.delete("/{absence_id}")
async def delete_absence(
    absence_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
):
    """
    Löscht Abwesenheit
    
    Nur eigene Abwesenheiten und nur wenn noch nicht genehmigt
    
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence not found"
        )
    
    # Berechtigung prüfen
    if absence.teacher_id != current_user.id and current_user.role not in [UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this absence"
        )
    
    # Status prüfen
    if absence.status not in [AbsenceStatus.DRAFT, AbsenceStatus.SUBMITTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete approved or completed absences"
        )
    
    db.delete(absence)
    db.commit()
    
    return {"message": "Absence deleted"}
