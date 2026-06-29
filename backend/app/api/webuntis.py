"""
WebUntis API Routes
Integration with WebUntis timetable system
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.models.models import User, UserRole
from app.schemas.schemas import FetchLessonsRequest, WebUntisLesson
from app.api.auth import get_wordpress_proxy_user
from app.services.webuntis_service import webuntis_service
from app.utils.absence_utils import (
    validate_date_range,
    is_lesson_in_period,
    clip_lesson_to_period,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Rate Limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/absences/fetch-lessons", response_model=List[WebUntisLesson])
@limiter.limit("30/minute")
async def fetch_lessons_from_webuntis(
    request: Request,
    fetch_request: FetchLessonsRequest,
    current_user: User = Depends(get_wordpress_proxy_user),
    db: Session = Depends(get_db),
):
    """
    Lädt Stunden aus WebUntis für Vorschau (ohne DB-Speicherung)

    Wird vom WordPress-Frontend verwendet, um betroffene Stunden VOR dem Absenden anzuzeigen.
    Authentifizierung über WordPress Proxy Secret (kein JWT Token erforderlich).

    Args:
        request: HTTP Request
        fetch_request: Zeitraum und Perioden
        current_user: Aktueller User (via WordPress Proxy Auth)
        db: Database session

    Returns:
        Liste von WebUntis-Stunden im angegebenen Zeitraum
    """
    # Validierung (delegiert an Utils)
    validate_date_range(
        fetch_request.start_date,
        fetch_request.end_date,
        fetch_request.start_period,
        fetch_request.end_period,
    )

    # Ziel-Lehrkraft bestimmen (Admin kann für andere Lehrkraft abrufen)
    target_teacher: Optional[User] = None
    if fetch_request.teacher_username and current_user.role == UserRole.ADMIN:
        target_teacher = (
            db.query(User)
            .filter(
                User.username == fetch_request.teacher_username,
                User.is_active.is_(True),
            )
            .first()
        )
        if not target_teacher:
            # Teacher not yet in DB — use a transient object (not persisted here;
            # auto-registration happens in absence_service when the absence is created)
            target_teacher = User(
                username=fetch_request.teacher_username,
                webuntis_teacher_code=fetch_request.teacher_webuntis_code,
            )
    else:
        target_teacher = current_user

    # Stunden aus WebUntis abrufen
    lessons = await webuntis_service.get_timetable_for_teacher(
        target_teacher.username,
        fetch_request.start_date,
        fetch_request.end_date,
        db=db,
        webuntis_code=target_teacher.webuntis_teacher_code,
    )

    # Filtern nach Perioden und Blöcke auf den angefragten Bereich kürzen
    filtered_lessons = []
    for lesson in lessons:
        if is_lesson_in_period(
            lesson,
            fetch_request.start_date,
            fetch_request.end_date,
            fetch_request.start_period,
            fetch_request.end_period,
        ):
            filtered_lessons.append(
                clip_lesson_to_period(
                    lesson,
                    fetch_request.start_date,
                    fetch_request.end_date,
                    fetch_request.start_period,
                    fetch_request.end_period,
                )
            )

    return filtered_lessons
