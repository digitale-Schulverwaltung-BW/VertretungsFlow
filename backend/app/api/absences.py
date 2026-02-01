"""
Absences API Routes
CRUD Operations für Abwesenheitsmeldungen
"""
import logging
import os
import uuid
from typing import List
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Request, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, selectinload, joinedload
import aiofiles

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.models import User, Absence, AffectedLesson, UserRole, AbsenceStatus, AbsenceAttachment
from app.schemas.schemas import (
    AbsenceCreate,
    AbsenceResponse,
    AbsenceUpdate,
    AbsenceApproval,
    AffectedLessonUpdate,
    AffectedLessonResponse,
    FetchLessonsRequest,
    WebUntisLesson,
    AttachmentResponse
)
from app.api.auth import get_current_active_user, require_role, get_wordpress_proxy_user
from app.services.webuntis_service import webuntis_service
from app.services.email_service import email_service

router = APIRouter()

# File upload configuration
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/var/absenzflow-uploads"))
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain'
]


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
        status=AbsenceStatus.SUBMITTED,
        excursion_classes=absence.excursion_classes,
        personal_reason=absence.personal_reason,
        admin_notes=absence.admin_notes
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
    query = db.query(Absence).options(
        selectinload(Absence.affected_lessons),
        selectinload(Absence.attachments),
        joinedload(Absence.teacher)
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
    absence = db.query(Absence).options(
        selectinload(Absence.affected_lessons),
        selectinload(Absence.attachments),
        joinedload(Absence.teacher)
    ).filter(Absence.id == absence_id).first()

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
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
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
    # Berechtigungsprüfung
    allowed_roles = [UserRole.DEPARTMENT_HEAD, UserRole.ADMIN, UserRole.PLANNER]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to approve absences"
        )

    absence = db.query(Absence).filter(Absence.id == absence_id).first()

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence not found"
        )

    # Status prüfen - Admin/Planner können immer approve, andere nur bei SUBMITTED
    if current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
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
    request: Request,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
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
    # Berechtigungsprüfung
    dept_heads_can_complete = request.headers.get("X-WordPress-Dept-Heads-Can-Complete", "0") == "1"

    allowed_roles = [UserRole.PLANNER, UserRole.ADMIN]
    if dept_heads_can_complete:
        allowed_roles.append(UserRole.DEPARTMENT_HEAD)

    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to complete absences"
        )

    absence = db.query(Absence).filter(Absence.id == absence_id).first()

    if not absence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Absence not found"
        )

    # Kein Status-Check mehr - Admin/Planner können immer complete
    
    # Status aktualisieren
    from datetime import datetime
    absence.status = AbsenceStatus.COMPLETED
    absence.completed_at = datetime.utcnow()

    # Attachments automatisch löschen
    if absence.attachments:
        logger.info(f"Deleting {len(absence.attachments)} attachments for completed absence {absence_id}")

        for attachment in absence.attachments:
            # Datei von Disk löschen
            file_path = Path(attachment.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")

        # DB-Einträge werden durch CASCADE automatisch gelöscht

    db.commit()

    # TODO: E-Mail-Benachrichtigung an Lehrkraft
    # await email_service.send_absence_completed_notification(...)

    return {"message": "Absence marked as completed, attachments deleted"}


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
    if absence.teacher_id != current_user.id and current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this absence"
        )

    # Status prüfen - Admin/Planner können immer löschen, andere nur bei DRAFT/SUBMITTED
    if current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
        if absence.status not in [AbsenceStatus.DRAFT, AbsenceStatus.SUBMITTED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete approved or completed absences"
            )
    
    db.delete(absence)
    db.commit()

    return {"message": "Absence deleted"}


# ============ Attachment Endpoints ============

@router.post("/{absence_id}/attachments", response_model=AttachmentResponse)
async def upload_attachment(
    absence_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
):
    """
    Lädt Datei-Anhang zu Abwesenheit hoch

    Security:
    - Authentifizierung erforderlich
    - Nur eigene Absenzen (oder Admin/Planner)
    - Dateivalidierung (Typ, Größe)
    - Storage außerhalb webroot
    """
    # Abwesenheit laden
    absence = db.query(Absence).filter(Absence.id == absence_id).first()
    if not absence:
        raise HTTPException(status_code=404, detail="Absence not found")

    # Berechtigung prüfen
    if current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
        if absence.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Status-Check: Keine Uploads bei erledigten Absenzen
    if absence.status == AbsenceStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Cannot upload to completed absence")

    # Dateivalidierung: MIME-Type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file.content_type} not allowed"
        )

    # Dateivalidierung: Größe (Read in chunks)
    file_size = 0
    temp_content = []

    while chunk := await file.read(8192):  # 8KB chunks
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large (max {MAX_FILE_SIZE / 1024 / 1024} MB)"
            )
        temp_content.append(chunk)

    # Generiere sicheren Dateinamen
    file_ext = Path(file.filename).suffix
    stored_filename = f"{uuid.uuid4()}{file_ext}"

    # Erstelle Unterverzeichnis pro Abwesenheit
    absence_dir = UPLOAD_DIR / f"absence_{absence_id}"
    absence_dir.mkdir(parents=True, exist_ok=True)

    file_path = absence_dir / stored_filename

    # Speichere Datei
    async with aiofiles.open(file_path, 'wb') as f:
        for chunk in temp_content:
            await f.write(chunk)

    # Speichere Metadaten in DB
    attachment = AbsenceAttachment(
        absence_id=absence_id,
        filename=file.filename,
        stored_filename=stored_filename,
        file_path=str(file_path),
        mime_type=file.content_type,
        file_size=file_size
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    logger.info(f"File uploaded: {file.filename} -> {stored_filename} ({file_size} bytes)")

    return attachment


@router.get("/{absence_id}/attachments/{attachment_id}")
async def download_attachment(
    absence_id: int,
    attachment_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
):
    """
    Lädt Anhang herunter (auth-geschützt)

    Security:
    - Authentifizierung erforderlich
    - Berechtigung wird geprüft
    - Streaming für große Dateien
    """
    # Attachment laden
    attachment = db.query(AbsenceAttachment).filter(
        AbsenceAttachment.id == attachment_id,
        AbsenceAttachment.absence_id == absence_id
    ).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Abwesenheit laden für Berechtigungsprüfung
    absence = attachment.absence

    # Berechtigung prüfen
    if current_user.role == UserRole.TEACHER:
        if absence.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Datei existiert?
    file_path = Path(attachment.file_path)
    if not file_path.exists():
        logger.error(f"File not found on disk: {file_path}")
        raise HTTPException(status_code=404, detail="File not found on server")

    # Streaming-Response
    return FileResponse(
        path=file_path,
        media_type=attachment.mime_type,
        filename=attachment.filename
    )


@router.delete("/{absence_id}/attachments/{attachment_id}")
async def delete_attachment(
    absence_id: int,
    attachment_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db)
):
    """
    Löscht Anhang

    Erlaubt: Eigentümer (wenn nicht completed), Admin, Planner
    """
    # Attachment laden
    attachment = db.query(AbsenceAttachment).filter(
        AbsenceAttachment.id == attachment_id,
        AbsenceAttachment.absence_id == absence_id
    ).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    absence = attachment.absence

    # Berechtigung prüfen
    if current_user.role not in [UserRole.ADMIN, UserRole.PLANNER]:
        if absence.teacher_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
        if absence.status == AbsenceStatus.COMPLETED:
            raise HTTPException(status_code=400, detail="Cannot delete from completed absence")

    # Datei von Disk löschen
    file_path = Path(attachment.file_path)
    if file_path.exists():
        file_path.unlink()
        logger.info(f"Deleted file: {file_path}")

    # DB-Eintrag löschen
    db.delete(attachment)
    db.commit()

    return {"message": "Attachment deleted"}
