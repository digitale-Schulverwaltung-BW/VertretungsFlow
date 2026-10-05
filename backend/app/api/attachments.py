"""
Attachments API Routes
File upload/download/delete operations for absences
"""

import logging
import re
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.audit import audit_file_uploaded, audit_file_deleted
from app.models.models import User, Absence, AbsenceAttachment
from app.schemas.schemas import AttachmentResponse
from app.api.auth import get_wordpress_proxy_user
from app.services.attachment_service import attachment_service
from app.services.permission_service import permission_service

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/{absence_id}/attachments", response_model=AttachmentResponse)
@limiter.limit("10/minute")
async def upload_attachment(
    request: Request,
    absence_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Lädt Datei-Anhang zu Abwesenheit hoch

    Security:
    - Authentifizierung erforderlich
    - Nur eigene Abwesenheiten (oder Admin/Planner)
    - Dateivalidierung (Typ, Größe)
    - Storage außerhalb webroot
    """
    # Abwesenheit laden
    absence = db.query(Absence).filter(Absence.id == absence_id).first()
    if not absence:
        raise HTTPException(status_code=404, detail="Absence not found")

    # Berechtigung prüfen (delegiert an Service)
    if not permission_service.can_edit_absence(current_user, absence):
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this absence"
        )

    # Dateivalidierung (delegiert an Service)
    file_size, file_content = await attachment_service.validate_file(file)

    # Datei speichern (delegiert an Service)
    saved_file = await attachment_service.save_file(file, file_content, absence_id)

    # Sanitize original filename: strip path components and dangerous characters
    safe_filename = re.sub(r"[^\w\s\-.]", "_", Path(file.filename or "upload").name)[
        :255
    ]

    # Speichere Metadaten in DB
    attachment = AbsenceAttachment(
        absence_id=absence_id,
        filename=safe_filename,
        stored_filename=saved_file.stored_filename,
        file_path=str(saved_file.file_path),
        mime_type=file.content_type,
        file_size=saved_file.file_size,
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    # Audit log
    audit_file_uploaded(
        attachment_id=attachment.id,
        user_id=current_user.id,
        details={
            "absence_id": absence_id,
            "filename": file.filename,
            "mime_type": file.content_type,
            "file_size": file_size,
        },
        request=request,
    )

    return attachment


@router.get("/{absence_id}/attachments/{attachment_id}")
@limiter.limit("30/minute")
async def download_attachment(
    request: Request,
    absence_id: int,
    attachment_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Lädt Anhang herunter (auth-geschützt)

    Security:
    - Authentifizierung erforderlich
    - Berechtigung wird geprüft
    - Streaming für große Dateien
    """
    # Attachment laden
    attachment = (
        db.query(AbsenceAttachment)
        .filter(
            AbsenceAttachment.id == attachment_id,
            AbsenceAttachment.absence_id == absence_id,
        )
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Abwesenheit laden für Berechtigungsprüfung
    absence = attachment.absence

    # Berechtigung prüfen (delegiert an Service)
    if not permission_service.can_view_absence(current_user, absence):
        raise HTTPException(
            status_code=403, detail="Not authorized to view this absence"
        )

    # Path Resolution & Validation (delegiert an Service)
    file_path = attachment_service.get_file_path(attachment.file_path)

    # Streaming-Response
    return FileResponse(
        path=file_path, media_type=attachment.mime_type, filename=attachment.filename
    )


@router.delete("/{absence_id}/attachments/{attachment_id}")
@limiter.limit("10/minute")
async def delete_attachment(
    request: Request,
    absence_id: int,
    attachment_id: int,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Löscht Anhang

    Erlaubt: Eigentümer (wenn nicht completed), Admin, Planner
    """
    # Attachment laden
    attachment = (
        db.query(AbsenceAttachment)
        .filter(
            AbsenceAttachment.id == attachment_id,
            AbsenceAttachment.absence_id == absence_id,
        )
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    absence = attachment.absence

    # Berechtigung prüfen (delegiert an Service)
    if not permission_service.can_edit_absence(current_user, absence):
        raise HTTPException(
            status_code=403, detail="Not authorized to edit this absence"
        )

    # Datei von Disk löschen (delegiert an Service)
    attachment_service.delete_file(attachment.file_path)

    # Audit log (before deleting from DB)
    audit_file_deleted(
        attachment_id=attachment.id,
        user_id=current_user.id,
        details={
            "absence_id": absence_id,
            "filename": attachment.filename,
            "mime_type": attachment.mime_type,
            "file_size": attachment.file_size,
        },
        request=request,
    )

    # DB-Eintrag löschen
    db.delete(attachment)
    db.commit()

    return {"message": "Attachment deleted"}
